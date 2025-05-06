#!/usr/bin/env python3
"""
Khora Kernel – repo_inspect v1.0.3
----------------------------------
One‑shot audit that emits a Markdown report covering:

  1. Directory structure & file counts
  2. Manifest sanity checks
  3. Knowledge‑graph validity
  4. Jinja template syntax
  5. Python syntax
  6. Heuristic quality score

Extra goodies
-------------
* `--verbose` / `--debug` flags for more detail
* `--include-hidden` to ignore the default exclusion list
* graceful degradation if optional libs (jsonschema, tabulate) are missing
* never crashes on absolute --out paths or empty reports
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import pathlib
import re
import sys
import textwrap
import time
from typing import Any, Dict, List

# ────────────────────────────────────────────────────────────────────
#  TRY OPTIONAL DEPENDENCIES
# ────────────────────────────────────────────────────────────────────
missing_opt_deps: list[str] = []

try:
    import yaml  # required
except ModuleNotFoundError:  # pragma: no cover
    print("❌  Missing required dependency: pyyaml – `pip install pyyaml`", file=sys.stderr)
    sys.exit(1)

try:
    from jsonschema import validate as js_validate, ValidationError  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    js_validate = None  # type: ignore
    ValidationError = Exception  # type: ignore
    missing_opt_deps.append("jsonschema")

try:
    from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    Environment = None  # type: ignore
    TemplateSyntaxError = Exception  # type: ignore
    missing_opt_deps.append("jinja2")

try:
    from tabulate import tabulate  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    tabulate = None  # type: ignore
    missing_opt_deps.append("tabulate")

# ────────────────────────────────────────────────────────────────────
#  PATHS & CONSTANTS
# ────────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(".").resolve()
KERNEL = ROOT / ".khorkernel"

MANIFEST = KERNEL / "KERNEL_MANIFEST.yaml"
VERSION_FILE = KERNEL / "VERSION"
KG_CONCEPTS = ROOT / "kg/concepts.json"
KG_RULES = ROOT / "kg/rules.json"
KG_SCHEMA = KERNEL / "schema/kg_schema.json"

OUT_DEFAULT = ROOT / "reports/repo_inspect_report.md"
EXCLUDE_DIRS_DEFAULT = {
    ".git",
    ".hg",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".khorkernel/__pycache__",
}

MANIFEST_REQUIRED = {"project", "features", "paths", "ports"}

# ────────────────────────────────────────────────────────────────────
#  HELPER UTILITIES
# ────────────────────────────────────────────────────────────────────
def sha1(path: pathlib.Path) -> str:
    h = hashlib.sha1()
    h.update(path.read_bytes())
    return h.hexdigest()[:7]


def list_files(exclude_dirs: set[str]) -> dict[str, list[pathlib.Path]]:
    """
    Group files by extension; honour the exclusion list.
    """
    bins: dict[str, list[pathlib.Path]] = {"py": [], "md": [], "j2": [], "other": []}
    for p in ROOT.rglob("*"):
        if any(part in exclude_dirs for part in p.parts):
            continue
        if p.is_file():
            if p.suffix == ".py":
                bins["py"].append(p)
            elif p.suffix == ".md":
                bins["md"].append(p)
            elif p.suffix == ".j2":
                bins["j2"].append(p)
            else:
                bins["other"].append(p)
    return bins


def bulletize(lines: list[str]) -> str:
    return "\n".join(f"* {l}" for l in lines)


def heading(txt: str, level: int = 2) -> str:
    return f"\n{'#' * level} {txt}"


# ────────────────────────────────────────────────────────────────────
#  1. STRUCTURE
# ────────────────────────────────────────────────────────────────────
def gather_structure(exclude_dirs: set[str]) -> str:
    bins = list_files(exclude_dirs)
    if tabulate:
        rows = [[k.upper(), len(v)] for k, v in bins.items()]
        return tabulate(rows, headers=["Type", "Count"], tablefmt="github")  # type: ignore
    # fallback simple:
    return bulletize([f"{k.upper()}: {len(v)}" for k, v in bins.items()])


# ────────────────────────────────────────────────────────────────────
#  2. MANIFEST
# ────────────────────────────────────────────────────────────────────
def validate_manifest() -> list[str]:
    if not MANIFEST.exists():
        return ["❌ Manifest missing."]
    try:
        data: dict[str, Any] = yaml.safe_load(MANIFEST.read_text()) or {}
        issues = [f"❌ manifest missing key `{k}`" for k in MANIFEST_REQUIRED if k not in data]
        return issues or ["✅ manifest looks sane"]
    except Exception as exc:  # pragma: no cover
        return [f"❌ manifest YAML error: {exc}"]


# ────────────────────────────────────────────────────────────────────
#  3. KNOWLEDGE GRAPH
# ────────────────────────────────────────────────────────────────────
def validate_kg() -> list[str]:
    if js_validate is None:
        return ["⚠️  jsonschema not installed – KG not validated"]

    if not KG_CONCEPTS.exists() or not KG_RULES.exists():
        return ["❌ KG files not generated.  Run `populate_kg.py` first."]

    try:
        schema_root = json.loads(KG_SCHEMA.read_text())
        item_schema = schema_root["definitions"]["knowledgeItem"]
    except Exception as exc:
        return [f"❌ KG schema unreadable: {exc}"]

    msgs: list[str] = []
    for f in (KG_CONCEPTS, KG_RULES):
        try:
            data: Dict[str, Any] = json.loads(f.read_text() or "{}")
            invalid = [k for k, v in data.items() if _invalid_ki(v, item_schema)]
            if invalid:
                msgs.append(
                    f"❌ {f.name}: {len(invalid)} invalid entries "
                    f"(e.g., {invalid[:3]})"
                )
            else:
                msgs.append(f"✅ {f.name}: {len(data)} items, schema‑valid")
        except Exception as exc:
            msgs.append(f"❌ {f.name} unreadable: {exc}")
    return msgs


def _invalid_ki(item: dict[str, Any], schema: dict[str, Any]) -> bool:
    try:
        js_validate(item, schema)  # type: ignore[arg-type]
        return False
    except ValidationError:
        return True


# ────────────────────────────────────────────────────────────────────
#  4. JINJA TEMPLATES
# ────────────────────────────────────────────────────────────────────
def compile_templates() -> list[str]:
    if Environment is None:
        return ["⚠️  jinja2 not installed – templates not checked"]

    env = Environment(loader=FileSystemLoader(str(KERNEL)))
    msgs: list[str] = []
    for tpl in KERNEL.rglob("*.j2"):
        rel = tpl.relative_to(ROOT)
        try:
            env.parse(tpl.read_text())
            msgs.append(f"✅ {rel}")
        except TemplateSyntaxError as exc:
            msgs.append(f"❌ {rel}:{exc.lineno} {exc.message}")
    return msgs or ["✅ no templates found"]


# ────────────────────────────────────────────────────────────────────
#  5. PYTHON SYNTAX
# ────────────────────────────────────────────────────────────────────
def compile_py(exclude_dirs: set[str]) -> list[str]:
    msgs: list[str] = []
    for py in list_files(exclude_dirs)["py"]:
        rel = py.relative_to(ROOT)
        try:
            ast.parse(py.read_text(), filename=str(rel))
        except SyntaxError as exc:  # pragma: no cover
            msgs.append(f"❌ {rel}:{exc.lineno}:{exc.offset} {exc.msg}")
    return msgs or ["✅ all *.py files parse"]


# ────────────────────────────────────────────────────────────────────
#  6. HEURISTIC SCORE
# ────────────────────────────────────────────────────────────────────
def heuristic_score(
    manifest_msgs: list[str],
    kg_msgs: list[str],
    tpl_msgs: list[str],
    py_msgs: list[str],
) -> str:
    score = 100
    if any(m.startswith("❌") for m in manifest_msgs):
        score -= 25
    if any(m.startswith("❌") for m in kg_msgs):
        score -= 20
    if any(m.startswith("❌") for m in tpl_msgs):
        score -= 20
    if any(m.startswith("❌") for m in py_msgs):
        score -= 20
    bar = "█" * (score // 5) + "░" * ((100 - score) // 5)
    return f"{score}/100  {bar}"


# ────────────────────────────────────────────────────────────────────
#  MAIN
# ────────────────────────────────────────────────────────────────────
def build_report(
    exclude_dirs: set[str],
    verbose: bool = False,
    debug: bool = False,
) -> str:
    """
    Compose the entire markdown report and return as a string.
    """
    lines: list[str] = []
    ts = time.strftime("%Y‑%m‑%d %H:%M:%S UTC")
    kernel_ver = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "unknown"
    repo_sha = sha1(MANIFEST) if MANIFEST.exists() else "n/a"

    lines.append(f"# 📊 Khora Repo Report\n*(generated {ts})*")
    lines.append(f"\n**Kernel Version:** `{kernel_ver}` &nbsp;&nbsp; **Repo SHA:** `{repo_sha}`")

    # 1 – structure
    lines.append(heading("1. Structure"))
    lines.append(gather_structure(exclude_dirs))

    # 2 – manifest
    manifest_msgs = validate_manifest()
    lines.append(heading("2. Manifest Checks"))
    lines.extend(bulletize(manifest_msgs).splitlines())

    # 3 – KG
    kg_msgs = validate_kg()
    lines.append(heading("3. Knowledge Graph"))
    lines.extend(bulletize(kg_msgs).splitlines())

    # 4 – templates
    tpl_msgs = compile_templates()
    lines.append(heading("4. Jinja Templates"))
    lines.extend(bulletize(tpl_msgs).splitlines() if not verbose else tpl_msgs)

    # 5 – python
    py_msgs = compile_py(exclude_dirs)
    lines.append(heading("5. Python Syntax"))
    lines.extend(bulletize(py_msgs).splitlines() if not verbose else py_msgs)

    # 6 – score
    lines.append(heading("6. Quality Score"))
    lines.append(f"```\n{heuristic_score(manifest_msgs, kg_msgs, tpl_msgs, py_msgs)}\n```")

    if debug and missing_opt_deps:
        lines.append(heading("Debug"))
        lines.append(
            bulletize([f"⚠️  optional dependency not installed: {d}" for d in missing_opt_deps])
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Khora Kernel repo inspector")
    ap.add_argument(
        "--out",
        default=str(OUT_DEFAULT),
        help=f"output markdown file (default: {OUT_DEFAULT.name})",
    )
    ap.add_argument(
        "--include-hidden",
        action="store_true",
        help="include normally excluded directories (e.g. .venv, node_modules)",
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="show full template/python error lists instead of bullet summary",
    )
    ap.add_argument("--debug", action="store_true", help="extra debug section at end")
    args = ap.parse_args()

    exclude_dirs = set() if args.include_hidden else EXCLUDE_DIRS_DEFAULT
    report_md = build_report(exclude_dirs, verbose=args.verbose, debug=args.debug)

    out_path = pathlib.Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md, encoding="utf‑8")

    try:
        shown = out_path.relative_to(ROOT)
    except ValueError:
        shown = out_path
    size_kb = out_path.stat().st_size // 1024
    print(f"✔ Report written to {shown} ({size_kb} KB)")


if __name__ == "__main__":
    main()
