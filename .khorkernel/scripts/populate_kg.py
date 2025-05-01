#!/usr/bin/env python3
# Khora Kernel - Populate Knowledge Graph Script v1.0.2
# Scans markdown files for [concept:...] and [rule:...] tags
# and generates kg/concepts.json and kg/rules.json.

# --- Python Version Check ---
import sys
if sys.version_info < (3, 8):
    print("Error: This script requires Python 3.8 or higher.", file=sys.stderr)
    sys.exit(1)

import json
import pathlib
import re
import yaml
from typing import Dict, List, Tuple, Any, Set, Optional

# Pre-compile regex for efficiency
TAG_PATTERN = re.compile(
    r"\[(concept|rule):([\w\-]+)\]\s*[-–—]\s*(.+)",
    re.IGNORECASE
)

# --- Configuration ---
KG_OUTPUT_DIR = "kg"
CONCEPTS_FILE = "concepts.json"
RULES_FILE = "rules.json"
KERNEL_DIR_NAME = ".khorkernel"
MANIFEST_FILE = f"{KERNEL_DIR_NAME}/KERNEL_MANIFEST.yaml"
DEFAULT_DOCS_DIR = "docs" # Default if not specified in manifest

# --- Helper Functions ---
def find_project_root(current_path: pathlib.Path) -> pathlib.Path:
    """Find the project root by looking for the .khorkernel directory."""
    current = current_path.resolve()
    while current != current.parent:
        if (current / KERNEL_DIR_NAME).is_dir():
            return current
        current = current.parent
    # Fallback check
    if (current_path.resolve() / MANIFEST_FILE).exists():
        return current_path.resolve()
    print("Warning: '.khorkernel' directory not found. Assuming current directory is project root.", file=sys.stderr)
    return current_path.resolve()


def load_manifest(root_dir: pathlib.Path) -> Dict[str, Any]:
    """Load the kernel manifest file."""
    manifest_path = root_dir / MANIFEST_FILE
    if not manifest_path.exists():
        print(f"Warning: Manifest file not found at '{manifest_path}'. Using default settings.", file=sys.stderr)
        return {}
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading manifest file '{manifest_path}': {e}", file=sys.stderr)
        return {}


def get_scan_directories(root_dir: pathlib.Path, manifest: Dict[str, Any]) -> List[pathlib.Path]:
    """Determine which directories to scan for markdown files."""
    scan_dirs_config = []
    # 1. Docs directory from manifest or default
    docs_dir_name = manifest.get("paths", {}).get("docs_dir", DEFAULT_DOCS_DIR)
    docs_dir_path = root_dir / docs_dir_name
    if docs_dir_path.is_dir():
        scan_dirs_config.append(docs_dir_path)
        print(f"Scanning docs directory: '{docs_dir_path.relative_to(root_dir)}'")

    # 2. Always scan the root directory shallowly for top-level README.md etc.
    scan_dirs_config.append(root_dir)
    print(f"Scanning root directory: '{root_dir}'")

    # Deduplicate and resolve paths
    unique_scan_dirs = []
    seen_paths: Set[pathlib.Path] = set()
    for p in scan_dirs_config:
        resolved_p = p.resolve()
        if resolved_p not in seen_paths:
            if p.is_dir(): # Only add if it actually exists
                unique_scan_dirs.append(p)
                seen_paths.add(resolved_p)

    return unique_scan_dirs


def extract_kg_from_markdown(file_path: pathlib.Path, root_dir: pathlib.Path) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]]:
    """Extract concept and rule tags from a markdown file."""
    concepts = {}
    rules = {}
    try:
        content = file_path.read_text(encoding="utf-8")
        for line_num, line in enumerate(content.splitlines()):
            match = TAG_PATTERN.match(line.strip())
            if match:
                item_type, item_name, item_desc = match.groups()
                item_type = item_type.lower()
                # Store relative path from root for portability
                source_ref = f"{file_path.relative_to(root_dir)}#L{line_num + 1}"
                
                if item_type == "concept":
                    if item_name in concepts:
                        # Provide more context in warning
                        prev_source = concepts[item_name]['source']
                        print(f"\nWarning: Duplicate definition for concept '{item_name}'.", file=sys.stderr)
                        print(f"  New:      '{source_ref}'", file=sys.stderr)
                        print(f"  Previous: '{prev_source}'", file=sys.stderr)
                        print(f"  Overwriting with definition from '{source_ref}'.\n", file=sys.stderr)
                    
                    concepts[item_name] = {
                        "desc": item_desc.strip(),
                        "source": str(source_ref)
                    }
                elif item_type == "rule":
                    if item_name in rules:
                        # Provide more context in warning
                        prev_source = rules[item_name]['source']
                        print(f"\nWarning: Duplicate definition for rule '{item_name}'.", file=sys.stderr)
                        print(f"  New:      '{source_ref}'", file=sys.stderr)
                        print(f"  Previous: '{prev_source}'", file=sys.stderr)
                        print(f"  Overwriting with definition from '{source_ref}'.\n", file=sys.stderr)
                    
                    rules[item_name] = {
                        "desc": item_desc.strip(),
                        "source": str(source_ref)
                    }
    except Exception as e:
        print(f"Error reading or parsing file '{file_path}': {e}", file=sys.stderr)
    
    return concepts, rules


def validate_kg_item(item_name: str, item_data: Dict[str, str], item_type: str) -> Optional[str]:
    """Validate a knowledge graph item for common issues."""
    if not item_name:
        return f"Empty {item_type} name"
    
    if not item_name[0].isupper():
        return f"{item_type} '{item_name}' doesn't follow CamelCase convention (should start with uppercase)"
    
    if "desc" not in item_data or not item_data["desc"]:
        return f"{item_type} '{item_name}' has empty description"
    
    if len(item_data["desc"]) < 10:
        return f"{item_type} '{item_name}' has very short description (only {len(item_data['desc'])} chars)"
    
    return None


# --- Main Logic ---
def main():
    script_dir = pathlib.Path(__file__).parent
    root_dir = find_project_root(script_dir)
    # print(f"Project root identified as: {root_dir}")

    manifest = load_manifest(root_dir)
    scan_directories = get_scan_directories(root_dir, manifest)

    knowledge_graph = {"concept": {}, "rule": {}}
    processed_files = 0

    excluded_dirs = {".git", ".hg", ".venv", "node_modules", "build", "dist", "__pycache__", KERNEL_DIR_NAME}

    for scan_dir in scan_directories:
        if scan_dir == root_dir:
            # Scan only top-level *.md files in the root, avoiding excluded dirs implicitly
            file_iterator = (p for p in scan_dir.glob("*.md") if p.is_file())
        else:
            # Scan recursively within specified subdirectories, excluding common build/venv dirs
            file_iterator = (p for p in scan_dir.rglob("*.md") 
                             if p.is_file() and not any(part in excluded_dirs 
                                                       for part in p.relative_to(root_dir).parts))

        for md_path in file_iterator:
            processed_files += 1
            # print(f"  Processing: {md_path.relative_to(root_dir)}") # Verbose
            
            concepts, rules = extract_kg_from_markdown(md_path, root_dir)
            
            # Add extracted items to the knowledge graph
            for name, data in concepts.items():
                knowledge_graph["concept"][name] = data
            
            for name, data in rules.items():
                knowledge_graph["rule"][name] = data

    # --- Validate KG Items ---
    warnings = []
    for concept_name, concept_data in knowledge_graph["concept"].items():
        warning = validate_kg_item(concept_name, concept_data, "Concept")
        if warning:
            warnings.append(warning)
    
    for rule_name, rule_data in knowledge_graph["rule"].items():
        warning = validate_kg_item(rule_name, rule_data, "Rule")
        if warning:
            warnings.append(warning)
    
    if warnings:
        print("\nKnowledge Graph Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        print()

    # --- Output ---
    output_dir = root_dir / KG_OUTPUT_DIR
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error: Could not create output directory '{output_dir}': {e}", file=sys.stderr)
        sys.exit(1)

    concepts_path = output_dir / CONCEPTS_FILE
    rules_path = output_dir / RULES_FILE

    try:
        # Write even if empty to ensure files exist for hashing in gen_context
        with open(concepts_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge_graph["concept"], f, indent=2, ensure_ascii=False, sort_keys=True)
        with open(rules_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge_graph["rule"], f, indent=2, ensure_ascii=False, sort_keys=True)
    except IOError as e:
        print(f"Error writing KG files to '{output_dir}': {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Knowledge Graph processed {processed_files} files, found {len(knowledge_graph['concept'])} concepts, {len(knowledge_graph['rule'])} rules.")
    print(f"Output written to '{concepts_path.relative_to(root_dir)}' and '{rules_path.relative_to(root_dir)}'.")
    
    # Suggest visualization if content exists
    if knowledge_graph["concept"] or knowledge_graph["rule"]:
        print("\nTip: Visualize your knowledge graph with:")
        print("  python .khorkernel/scripts/render_kg.py --format table # or --format graph")


if __name__ == "__main__":
    main()