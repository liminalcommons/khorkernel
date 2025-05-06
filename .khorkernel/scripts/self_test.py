#!/usr/bin/env python3
"""
Khora Kernel – self_test (v1.0.3)
Quick diagnostic to ensure local environment is ready.
"""
import importlib.util, json, os, pathlib, sys, argparse

ROOT = pathlib.Path(__file__).resolve().parents[2]
failures = 0
output_lines = []

def check(cond, msg):
    global failures
    line = f"✅ {msg}" if cond else f"❌ {msg}"
    output_lines.append(line)
    print(line)
    if not cond:
        failures += 1

def run_self_test():
    """Run all self tests and return the success status."""
    output_lines.append("== Khora self-test ==")
    print("== Khora self-test ==")
    
    check(sys.version_info >= (3,8), f"Python ≥3.8 (found {sys.version.split()[0]})")
    check((ROOT/".khorkernel").is_dir(), ".khorkernel directory present")
    check((ROOT/".khorkernel/KERNEL_MANIFEST.yaml").is_file(), "KERNEL_MANIFEST.yaml present")

    kg_concepts = ROOT/"kg/concepts.json"
    kg_rules    = ROOT/"kg/rules.json"
    if kg_concepts.exists() and kg_concepts.stat().st_size:
        check(True, "KG concepts.json present")
    else:
        warning = "⚠️  Knowledge‑graph not generated yet – run populate_kg.py"
        output_lines.append(warning)
        print(warning, file=sys.stderr)

    if kg_rules.exists() and kg_rules.stat().st_size:
        check(True, "KG rules.json present")
    else:
        warning = "⚠️  Knowledge‑graph not generated yet – run populate_kg.py"
        output_lines.append(warning)
        print(warning, file=sys.stderr)

    try:
        import yaml, rich
        check(True, "Required libs (pyyaml, rich) importable")
    except ImportError as e:
        check(False, f"Missing library: {e.name}")

    summary = "✅ PASS" if failures==0 else f"❌ {failures} issue(s) found"
    output_lines.append(f"\nSelf-test completed: {summary}")
    print(f"\nSelf-test completed: {summary}")
    
    return failures == 0

def main():
    """Parse arguments and run the self test."""
    parser = argparse.ArgumentParser(description="Khora Kernel self-test")
    parser.add_argument("--out", help="Write output to specified file")
    args = parser.parse_args()
    
    success = run_self_test()
    
    # Write to output file if specified
    if args.out:
        out_path = pathlib.Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            print(f"✓ Test results written to {out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path}")
        except Exception as e:
            print(f"Error writing to output file: {e}", file=sys.stderr)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
