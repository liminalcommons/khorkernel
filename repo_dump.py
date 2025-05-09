#!/usr/bin/env python3
"""
Khora Kernel – repo_dump
Dump (almost) everything in the repo into a single Markdown bundle so it can be
shared with an LLM for audit / feedback.

Features
--------
* Skips common junk / virtual‑env / node_modules / VCS dirs.
* Detects & omits binary files (adds a stub line instead).
* Truncates very large text files (default 50 KB) but records size + SHA‑1.
* Writes either to stdout or --out <file> (default reports/repo_dump.md).

Usage
-----
  python .khorkernel/scripts/repo_dump.py             # writes reports/repo_dump.md
  python .khorkernel/scripts/repo_dump.py --out /tmp/full.md
  python .khorkernel/scripts/repo_dump.py --max-bytes 20000
"""
from __future__ import annotations
import argparse, base64, hashlib, mimetypes, os, pathlib, sys, textwrap

# Import version helper
# SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
# sys.path.append(str(SCRIPT_DIR / "khora-kernel-vnext" / "src"))
# from khora_kernel_vnext._internal.version import get_kernel_version

ROOT = pathlib.Path(__file__).resolve().parent # Explicitly set ROOT to the script's directory

def get_kernel_version() -> str:
    """Reads the kernel version from the VERSION file."""
    version_file = ROOT / "khora-kernel-vnext" / "src" / "khora_kernel_vnext" / "_internal" / "VERSION"
    try:
        return version_file.read_text().strip()
    except FileNotFoundError:
        return "0.0.0-unknown" # Fallback version

# Print banner with dynamic version
print(f"Khora Kernel – repo_dump v{get_kernel_version()}")

EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", ".venv", "env", "node_modules", "__pycache__", "dist", "build",
    # Additional cache directories
    ".pytest_cache", ".ruff_cache", ".mypy_cache", ".cache", ".tox", ".coverage",
    "caches", ".caches", "tmp", ".tmp", "temp", ".temp", "__cache__",
}
# Files to exclude
EXCLUDE_FILES = {
    "repo_dump.md",  # Exclude previous repo dump outputs
    ".DS_Store",     # macOS metadata file
    "Thumbs.db",     # Windows thumbnail cache
}
MAX_DEFAULT = 50_000  # bytes

# ──────────────────────────────────────────────────────────
def is_binary(path: pathlib.Path) -> bool:
    """Very lightweight binary sniff."""
    try:
        with path.open("rb") as f:
            CHUNK = f.read(1024)
            return b"\0" in CHUNK
    except Exception:
        return True

def sha1(path: pathlib.Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:7]

def lang_tag(p: pathlib.Path) -> str:
    """Return a reasonable markdown language tag from extension."""
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".json": "json",
        ".md": "markdown",
        ".html": "html",
        ".css": "css",
        ".j2": "jinja",
        ".sh": "bash",
        ".toml": "toml",
    }
    return mapping.get(p.suffix.lower(), "")

# ──────────────────────────────────────────────────────────
def gather_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for p in ROOT.rglob("*"):
        if p.is_dir():
            # skip excluded dirs anywhere in path
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
        elif p.is_file():
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            # Skip excluded files
            if p.name in EXCLUDE_FILES:
                continue
            # Skip any file with 'repo_dump' in the name to catch variations
            if "repo_dump" in p.name.lower():
                continue
            # Skip cache files by pattern
            if p.name.endswith('.pyc') or p.name.endswith('.pyo') or p.name.endswith('.pyd'):
                continue
            files.append(p)
    return sorted(files)

# ──────────────────────────────────────────────────────────
def dump_repo(out_file: pathlib.Path, max_bytes: int) -> None:
    lines: list[str] = []
    lines.append(f"# 📦 Repository Dump  \n*(root `{ROOT.name}`, max_bytes={max_bytes})*")
    for p in gather_files():
        rel = p.relative_to(ROOT)
        size = p.stat().st_size
        sha = sha1(p)
        if is_binary(p):
            lines.append(f"\n## {rel}  \n`{size} bytes`  ·  `{sha}` (binary omitted)")
            continue

        try:
            text = p.read_text(errors="replace")
        except Exception as e:
            lines.append(f"\n## {rel}  \nCould not read file: {e}")
            continue

        if size > max_bytes:
            head = text[:max_bytes]
            note = f"*…truncated – original {size} bytes, showing first {max_bytes} bytes*"
        else:
            head, note = text, ""

        tag = lang_tag(p)
        lines.append(f"\n## {rel}  \n`{size} bytes`  ·  `{sha}`  {note}")
        lines.append(f"```{tag}\n{head}\n```")

    out_file.write_text("\n".join(lines), encoding="utf‑8")
    print(f"✔ Repo dumped to {out_file}  ({out_file.stat().st_size//1024} KB)")

# ──────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Dump repo into a single markdown file.")
    default_out_file = ROOT / "reports" / "repo_dump.md"
    ap.add_argument("--out", default=str(default_out_file), help="output markdown path")
    ap.add_argument("--max-bytes", type=int, default=MAX_DEFAULT,
                    help="max bytes of each text file to include (default 50000)")
    args = ap.parse_args()
    out_path = pathlib.Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dump_repo(out_path, args.max_bytes)

if __name__ == "__main__":
    main()
