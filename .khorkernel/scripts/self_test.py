#!/usr/bin/env python3
"""
Khora Kernel – self_test (v1.0.2)
Quick diagnostic to ensure local environment is ready.
"""
import importlib.util, json, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
failures = 0

def check(cond, msg):
    global failures
    if cond:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")
        failures += 1

print("== Khora self-test ==")
check(sys.version_info >= (3,8), f"Python ≥3.8 (found {sys.version.split()[0]})")
check((ROOT/".khorkernel").is_dir(), ".khorkernel directory present")
check((ROOT/".khorkernel/KERNEL_MANIFEST.yaml").is_file(), "KERNEL_MANIFEST.yaml present")

kg_concepts = ROOT/"kg/concepts.json"
kg_rules    = ROOT/"kg/rules.json"
if kg_concepts.exists() and kg_concepts.stat().st_size:
    check(True, "KG concepts.json present")
else:
    print("⚠️  Knowledge‑graph not generated yet – run populate_kg.py", file=sys.stderr)

if kg_rules.exists() and kg_rules.stat().st_size:
    check(True, "KG rules.json present")
else:
    print("⚠️  Knowledge‑graph not generated yet – run populate_kg.py", file=sys.stderr)

try:
    import yaml, rich
    check(True, "Required libs (pyyaml, rich) importable")
except ImportError as e:
    check(False, f"Missing library: {e.name}")

print("\nSelf-test completed:", "✅ PASS" if failures==0 else f"❌ {failures} issue(s) found")
sys.exit(1 if failures else 0)
