#!/usr/bin/env python3
# Khora Kernel - Generate Context Script v1.0.2
# Creates the .khora/context.yaml file based on the manifest and KG files.

# --- Python Version Check ---
import sys
if sys.version_info < (3, 8):
    print("Error: This script requires Python 3.8 or higher.", file=sys.stderr)
    sys.exit(1)

import yaml
import pathlib
import hashlib
import datetime
import json
import os
from typing import Dict, Any, List, Optional, Union

# Check for jsonschema and handle gracefully
try:
    import jsonschema
    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError:
    SCHEMA_VALIDATION_AVAILABLE = False
    print("Warning: jsonschema package not found. Context schema validation will be skipped.", file=sys.stderr)
    print("Consider installing it with: pip install jsonschema", file=sys.stderr)

# --- Configuration ---
OUTPUT_DIR = ".khora"
OUTPUT_FILE = "context.yaml"
KERNEL_DIR_NAME = ".khorkernel"
MANIFEST_FILE = f"{KERNEL_DIR_NAME}/KERNEL_MANIFEST.yaml"
KG_DIR = "kg"
CONCEPTS_FILE = f"{KG_DIR}/concepts.json"
RULES_FILE = f"{KG_DIR}/rules.json"
VERSION_FILE = f"{KERNEL_DIR_NAME}/VERSION"
SCHEMA_FILE = f"{KERNEL_DIR_NAME}/schema/context_schema.json"

# --- Helper Functions ---
def find_project_root(current_path: pathlib.Path) -> pathlib.Path:
    """Find the project root by looking for the .khorkernel directory."""
    current = current_path.resolve()
    while current != current.parent:
        if (current / KERNEL_DIR_NAME).is_dir():
            return current
        current = current.parent
    # If .khorkernel not found, maybe running from kernel source itself?
    if (current_path.resolve() / MANIFEST_FILE).exists():
        return current_path.resolve() # Assume current dir is root

    print("Warning: '.khorkernel' directory not found. Assuming current directory is project root.", file=sys.stderr)
    return current_path.resolve()


def calculate_file_hash(file_path: pathlib.Path) -> Optional[str]:
    """Calculate SHA1 hash of a file if it exists."""
    if not file_path.is_file():
        return None
    try:
        hasher = hashlib.sha1()
        with open(file_path, 'rb') as f:
            while chunk := f.read(4096):
                hasher.update(chunk)
        return hasher.hexdigest()
    except IOError as e:
        print(f"Warning: Could not read file '{file_path}' for hashing: {e}", file=sys.stderr)
        return None


def load_json_file(file_path: pathlib.Path) -> Optional[Union[Dict, List]]:
    """Load a JSON file if it exists."""
    if not file_path.is_file():
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load or parse JSON file '{file_path}': {e}", file=sys.stderr)
        return None


def read_version(root_dir: pathlib.Path) -> str:
    """Read kernel version from the VERSION file."""
    version_path = root_dir / VERSION_FILE
    try:
        return version_path.read_text(encoding='utf-8').strip()
    except Exception as e:
        print(f"Warning: Could not read kernel version file '{version_path}': {e}", file=sys.stderr)
        return "unknown"


def validate_context(context_data: Dict[str, Any], schema_path: pathlib.Path) -> bool:
    """Validate the context data against the schema."""
    if not SCHEMA_VALIDATION_AVAILABLE:
        return True  # Skip validation if jsonschema isn't available
        
    if not schema_path.exists():
        print(f"Warning: Schema file not found at '{schema_path}'. Skipping validation.", file=sys.stderr)
        return True
        
    try:
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
        jsonschema.validate(instance=context_data, schema=schema)
        print("Context data validation successful.")
        return True
    except json.JSONDecodeError as e:
        print(f"Error parsing context schema file: {e}", file=sys.stderr)
        return False
    except jsonschema.exceptions.ValidationError as e:
        print(f"Context data validation failed: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error during context validation: {e}", file=sys.stderr)
        return False


# --- Main Logic ---
def main():
    script_dir = pathlib.Path(__file__).parent
    root_dir = find_project_root(script_dir)
    # print(f"Project root identified as: {root_dir}")

    # --- Read Kernel Version ---
    kernel_version = read_version(root_dir)

    # --- Load Manifest ---
    manifest_path = root_dir / MANIFEST_FILE
    if not manifest_path.exists():
        print(f"Error: Manifest file not found at '{manifest_path}'. Cannot generate context.", file=sys.stderr)
        sys.exit(1)
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.safe_load(f)
            if not isinstance(manifest, dict):
                 raise yaml.YAMLError("Manifest content is not a dictionary.")
    except Exception as e:
        print(f"Error loading or parsing manifest file '{manifest_path}': {e}", file=sys.stderr)
        sys.exit(1)

    # --- Prepare Context Data ---
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds') + "Z"

    # Basic project info from manifest
    project_info = {
        "name": manifest.get("project", "unknown-project"),
        "description": manifest.get("project_description", ""),
    }

    # Features and Infrastructure
    features = manifest.get("features", {})
    infra = {
        "broker_type": features.get("broker", "none"),
        "database_type": features.get("database", "none"),
        "observability_enabled": features.get("observability", False),
        "security_gates_enabled": features.get("security_gates", False),
        "http_port": manifest.get("ports", {}).get("http", None),
        "lite_mode_available": features.get("lite_mode_available", False)
    }

    # Paths
    paths = manifest.get("paths", {})

    # Bounded Contexts (provide a default if missing)
    default_contexts = []
    if paths.get("api_dir"):
        default_contexts.append({"id": "api", "name": "API Service", "path": paths["api_dir"], "container_service": "api"})
    if paths.get("worker_dir") and paths["worker_dir"] != paths.get("api_dir"):
         default_contexts.append({"id": "worker", "name": "Worker Service", "path": paths["worker_dir"], "container_service": "worker"})

    bounded_contexts = manifest.get("bounded_contexts", default_contexts)

    # --- Knowledge Graph Integration ---
    concepts_path = root_dir / CONCEPTS_FILE
    rules_path = root_dir / RULES_FILE

    kg_summary = {
        "concepts_hash": calculate_file_hash(concepts_path),
        "rules_hash": calculate_file_hash(rules_path),
        "concept_count": len(load_json_file(concepts_path) or {}),
        "rule_count": len(load_json_file(rules_path) or {}),
        "source_dir": KG_DIR,
        "last_updated": now_iso
    }

    # --- Check Plugins ---
    plugins_enabled = manifest.get("plugins", [])
    plugin_details = []
    
    for plugin in plugins_enabled:
        plugin_dir = root_dir / KERNEL_DIR_NAME / "plugins" / plugin
        plugin_py = plugin_dir / "plugin.py"
        if plugin_dir.exists() and plugin_py.exists():
            plugin_details.append({
                "name": plugin,
                "path": str(plugin_dir.relative_to(root_dir)),
                "active": True
            })
        else:
            print(f"Warning: Plugin '{plugin}' listed in manifest but not found in plugins directory.", file=sys.stderr)
            plugin_details.append({
                "name": plugin,
                "active": False,
                "reason": "Plugin directory or plugin.py not found"
            })

    # --- Assemble Final Context ---
    context_data = {
        "schema_version": "1.0.2",
        "kernel_version": kernel_version,
        "generated_at": now_iso,
        "project": project_info,
        "infrastructure": infra,
        "paths": paths,
        "bounded_contexts": bounded_contexts,
        "knowledge_graph_summary": kg_summary,
        "plugins_enabled": plugins_enabled,
        "plugin_details": plugin_details if plugin_details else None,
    }

    # --- Validate Context Against Schema ---
    schema_path = root_dir / SCHEMA_FILE
    if SCHEMA_VALIDATION_AVAILABLE and schema_path.exists():
        valid = validate_context(context_data, schema_path)
        if not valid:
            print("Warning: Generated context data failed schema validation.", file=sys.stderr)
            print("Context file will still be written, but may cause issues.", file=sys.stderr)

    # --- Output ---
    output_dir = root_dir / OUTPUT_DIR
    output_path = output_dir / OUTPUT_FILE
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            # Use sort_keys=False to maintain a more logical order
            yaml.safe_dump(context_data, f, sort_keys=False, indent=2, allow_unicode=True)
        print(f"Context file generated successfully at: '{output_path.relative_to(root_dir)}'")
    except Exception as e:
        print(f"Error writing context file '{output_path}': {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()