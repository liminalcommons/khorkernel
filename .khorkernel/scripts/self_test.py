#!/usr/bin/env python3
# Khora Kernel - Self Test Script v1.0.2
# Validates the integrity and functionality of the kernel

import sys
import os
import pathlib
import subprocess
import yaml
import json
import tempfile
import shutil
import time
from typing import Dict, List, Any, Tuple, Optional

# --- Python Version Check ---
if sys.version_info < (3, 8):
    print("Error: This script requires Python 3.8 or higher.", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
KERNEL_DIR_NAME = ".khorkernel"
MANIFEST_FILE = "KERNEL_MANIFEST.yaml"
VERSION_FILE = "VERSION"
REQUIRED_SCRIPTS = [
    "bootstrap_backlog.py",
    "gen_context.py",
    "populate_kg.py",
    "render_kg.py",
    "gen_secure_creds.py",
    "self_test.py",
    "gen_release_notes.py"
]
REQUIRED_TEMPLATES = [
    "compose/docker-compose.j2",
    "compose/docker-compose.lite.j2",
    "ci/ci.j2",
    "ci/docker-build.j2",
    "ci/context-delta.yml"
]
REQUIRED_SCHEMAS = [
    "schema/kg_schema.json",
    "schema/context_schema.json"
]


# --- Helper Functions ---
def find_kernel_dir(current_path: pathlib.Path) -> Optional[pathlib.Path]:
    """Find the kernel directory, either directly or in parent."""
    # Check if we're inside the kernel dir
    if current_path.name == KERNEL_DIR_NAME:
        return current_path
    
    # Check if kernel is in current directory
    kernel_dir = current_path / KERNEL_DIR_NAME
    if kernel_dir.is_dir():
        return kernel_dir
    
    # Look for kernel in parent directories
    current = current_path.resolve()
    while current != current.parent:
        kernel_dir = current / KERNEL_DIR_NAME
        if kernel_dir.is_dir():
            return kernel_dir
        current = current.parent
    
    return None


def check_file_exists(base_dir: pathlib.Path, relative_path: str) -> Tuple[bool, str]:
    """Check if a file exists and return status with message."""
    file_path = base_dir / relative_path
    exists = file_path.exists()
    if exists:
        return True, f"✅ {relative_path}"
    else:
        return False, f"❌ {relative_path} (MISSING)"


def check_kernel_files(kernel_dir: pathlib.Path) -> Tuple[bool, List[str]]:
    """Check if all required kernel files exist."""
    all_files_exist = True
    messages = []

    # Check core files
    for file in [MANIFEST_FILE, VERSION_FILE]:
        exists, msg = check_file_exists(kernel_dir, file)
        all_files_exist = all_files_exist and exists
        messages.append(msg)
    
    # Check script files
    for script in REQUIRED_SCRIPTS:
        exists, msg = check_file_exists(kernel_dir, f"scripts/{script}")
        all_files_exist = all_files_exist and exists
        messages.append(msg)
    
    # Check template files
    for template in REQUIRED_TEMPLATES:
        exists, msg = check_file_exists(kernel_dir, template)
        all_files_exist = all_files_exist and exists
        messages.append(msg)
    
    # Check schema files
    for schema in REQUIRED_SCHEMAS:
        exists, msg = check_file_exists(kernel_dir, schema)
        all_files_exist = all_files_exist and exists
        messages.append(msg)
    
    return all_files_exist, messages


def check_manifest_validity(kernel_dir: pathlib.Path) -> Tuple[bool, str, Optional[Dict]]:
    """Check if the manifest file is valid YAML and has required keys."""
    manifest_path = kernel_dir / MANIFEST_FILE
    
    if not manifest_path.exists():
        return False, "❌ Manifest file is missing", None
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.safe_load(f)
        
        if not isinstance(manifest, dict):
            return False, "❌ Manifest is not a valid YAML dictionary", None
        
        # Check for required keys
        missing_keys = []
        for key in ['project', 'features', 'paths', 'ports']:
            if key not in manifest:
                missing_keys.append(key)
        
        if missing_keys:
            return False, f"❌ Manifest is missing required keys: {', '.join(missing_keys)}", manifest
        
        return True, "✅ Manifest is valid", manifest
    
    except Exception as e:
        return False, f"❌ Error loading manifest: {e}", None


def check_script_syntax(kernel_dir: pathlib.Path) -> Tuple[bool, List[str]]:
    """Check Python script syntax using compileall."""
    scripts_dir = kernel_dir / "scripts"
    if not scripts_dir.is_dir():
        return False, ["❌ Scripts directory not found"]
    
    messages = []
    all_valid = True
    
    for script in REQUIRED_SCRIPTS:
        script_path = scripts_dir / script
        if not script_path.exists():
            messages.append(f"❌ {script} (MISSING)")
            all_valid = False
            continue
        
        try:
            process = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script_path)],
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                messages.append(f"✅ {script} (Syntax valid)")
            else:
                messages.append(f"❌ {script} (Syntax error: {process.stderr.strip()})")
                all_valid = False
        
        except Exception as e:
            messages.append(f"❌ {script} (Error checking syntax: {e})")
            all_valid = False
    
    return all_valid, messages


def check_jinja_templates(kernel_dir: pathlib.Path) -> Tuple[bool, List[str]]:
    """Check Jinja templates for basic syntax issues."""
    try:
        import jinja2
    except ImportError:
        return False, ["❌ Jinja2 not installed. Cannot check templates."]
    
    messages = []
    all_valid = True
    
    # Create a test environment
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(kernel_dir)))
    
    for template_path in REQUIRED_TEMPLATES:
        if template_path.endswith('.yml'):
            continue  # Skip non-Jinja templates
            
        # Get the template name (without directory path)
        template_name = template_path
        
        try:
            # Try to load the template
            template = env.get_template(template_name)
            messages.append(f"✅ {template_name} (Template valid)")
        except jinja2.exceptions.TemplateNotFound:
            messages.append(f"❌ {template_name} (Template not found)")
            all_valid = False
        except jinja2.exceptions.TemplateSyntaxError as e:
            messages.append(f"❌ {template_name} (Syntax error: {e})")
            all_valid = False
        except Exception as e:
            messages.append(f"❌ {template_name} (Error: {e})")
            all_valid = False
    
    return all_valid, messages


def check_schema_validity(kernel_dir: pathlib.Path) -> Tuple[bool, List[str]]:
    """Check if schema files contain valid JSON Schema."""
    try:
        import jsonschema
        jsonschema_available = True
    except ImportError:
        jsonschema_available = False
    
    messages = []
    all_valid = True
    
    for schema_path in REQUIRED_SCHEMAS:
        full_path = kernel_dir / schema_path
        if not full_path.exists():
            messages.append(f"❌ {schema_path} (MISSING)")
            all_valid = False
            continue
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            if not isinstance(schema, dict):
                messages.append(f"❌ {schema_path} (Not a valid JSON object)")
                all_valid = False
                continue
            
            # Basic schema validation
            if "$schema" not in schema:
                messages.append(f"⚠️ {schema_path} (Missing $schema property, but otherwise valid)")
            
            # Validate with jsonschema if available
            if jsonschema_available:
                # Validate schema itself against metaschema
                try:
                    jsonschema.validators.validator_for(schema).check_schema(schema)
                    messages.append(f"✅ {schema_path} (Schema valid)")
                except jsonschema.exceptions.SchemaError as e:
                    messages.append(f"❌ {schema_path} (Invalid schema: {e})")
                    all_valid = False
            else:
                messages.append(f"✅ {schema_path} (Found, but jsonschema not installed for deep validation)")
        
        except json.JSONDecodeError as e:
            messages.append(f"❌ {schema_path} (Invalid JSON: {e})")
            all_valid = False
        except Exception as e:
            messages.append(f"❌ {schema_path} (Error: {e})")
            all_valid = False
    
    return all_valid, messages


def run_sandbox_test(kernel_dir: pathlib.Path) -> Tuple[bool, List[str]]:
    """Set up a sandbox environment and run bootstrap script."""
    messages = []
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        messages.append(f"Created sandbox environment at {tmp_path}")
        
        try:
            # Copy kernel directory to sandbox
            sandbox_kernel = tmp_path / KERNEL_DIR_NAME
            shutil.copytree(kernel_dir, sandbox_kernel)
            messages.append("✅ Copied kernel to sandbox")
            
            # Initialize git repo
            os.chdir(tmp_path)
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Kernel Test"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "kernel-test@example.com"], check=True, capture_output=True)
            messages.append("✅ Initialized git repository")
            
            # Test bootstrap script in regenerate-only mode
            bootstrap_script = sandbox_kernel / "scripts" / "bootstrap_backlog.py"
            result = subprocess.run(
                [sys.executable, str(bootstrap_script), "--regenerate-only", "--skip-deps"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                messages.append("✅ Bootstrap script executed successfully")
                
                # Check for generated files
                if (tmp_path / "docker-compose.yml").exists():
                    messages.append("✅ docker-compose.yml generated")
                else:
                    messages.append("❌ docker-compose.yml not generated")
                
                if (tmp_path / ".github" / "workflows").is_dir():
                    messages.append("✅ GitHub workflow directory created")
                else:
                    messages.append("❌ GitHub workflow directory not created")
                
                return True, messages
            else:
                messages.append(f"❌ Bootstrap script failed with error code {result.returncode}")
                messages.append(f"Error output: {result.stderr}")
                return False, messages
        
        except Exception as e:
            messages.append(f"❌ Sandbox test failed: {e}")
            import traceback
            messages.append(traceback.format_exc())
            return False, messages


def check_plugins(kernel_dir: pathlib.Path) -> Tuple[bool, List[str]]:
    """Check if plugins directory exists and contains expected plugins."""
    plugins_dir = kernel_dir / "plugins"
    
    if not plugins_dir.is_dir():
        return False, ["❌ Plugins directory not found"]
    
    messages = []
    
    # Check for README
    if (plugins_dir / "README.md").exists():
        messages.append("✅ plugins/README.md found")
    else:
        messages.append("❌ plugins/README.md missing")
    
    # Check for example plugins
    for plugin in ["terraform", "playwright"]:
        plugin_dir = plugins_dir / plugin
        if plugin_dir.is_dir():
            if (plugin_dir / "plugin.py").exists():
                messages.append(f"✅ Plugin '{plugin}' found with plugin.py")
            else:
                messages.append(f"⚠️ Plugin '{plugin}' directory exists but missing plugin.py")
        else:
            messages.append(f"⚠️ Plugin '{plugin}' not found (optional)")
    
    return True, messages


def print_section(title: str, messages: List[str]) -> None:
    """Print a section of test results with nice formatting."""
    print(f"\n=== {title} ===\n")
    for msg in messages:
        print(msg)


def main():
    print("=== Khora Kernel Self-Test v1.0.2 ===\n")
    
    # Find kernel directory
    script_dir = pathlib.Path(__file__).parent
    kernel_dir = find_kernel_dir(script_dir)
    
    if not kernel_dir:
        print("❌ Kernel directory not found. Run this script from within or adjacent to .khorkernel/", file=sys.stderr)
        sys.exit(1)
    
    print(f"Kernel directory found at: {kernel_dir}")
    
    # Version check
    version_file = kernel_dir / VERSION_FILE
    if version_file.exists():
        version = version_file.read_text().strip()
        print(f"Kernel version: {version}")
    else:
        print("⚠️ VERSION file not found")
    
    # File presence check
    files_valid, file_messages = check_kernel_files(kernel_dir)
    print_section("File Presence Check", file_messages)
    
    # Manifest check
    manifest_valid, manifest_message, manifest = check_manifest_validity(kernel_dir)
    print_section("Manifest Validation", [manifest_message])
    
    # Python syntax check
    syntax_valid, syntax_messages = check_script_syntax(kernel_dir)
    print_section("Python Script Syntax Check", syntax_messages)
    
    # Jinja template check
    jinja_valid, jinja_messages = check_jinja_templates(kernel_dir)
    print_section("Jinja Template Check", jinja_messages)
    
    # JSON Schema check
    schema_valid, schema_messages = check_schema_validity(kernel_dir)
    print_section("JSON Schema Check", schema_messages)
    
    # Plugin check
    plugins_valid, plugin_messages = check_plugins(kernel_dir)
    print_section("Plugins Check", plugin_messages)
    
    # Sandbox test
    print("\n=== Running Sandbox Test (This may take a moment) ===\n")
    sandbox_valid, sandbox_messages = run_sandbox_test(kernel_dir)
    print_section("Sandbox Test", sandbox_messages)
    
    # Overall result
    overall_valid = files_valid and manifest_valid and syntax_valid and jinja_valid and schema_valid and sandbox_valid
    
    print("\n=== Test Summary ===\n")
    print(f"File Presence Check: {'✅ PASS' if files_valid else '❌ FAIL'}")
    print(f"Manifest Validation: {'✅ PASS' if manifest_valid else '❌ FAIL'}")
    print(f"Python Script Syntax: {'✅ PASS' if syntax_valid else '❌ FAIL'}")
    print(f"Jinja Templates: {'✅ PASS' if jinja_valid else '❌ FAIL'}")
    print(f"JSON Schema: {'✅ PASS' if schema_valid else '❌ FAIL'}")
    print(f"Plugins: {'✅ PASS' if plugins_valid else '❌ FAIL'}")
    print(f"Sandbox Test: {'✅ PASS' if sandbox_valid else '❌ FAIL'}")
    print(f"\nOverall Result: {'✅ PASS' if overall_valid else '❌ FAIL'}")
    
    if overall_valid:
        print("\n✨ Khora Kernel is ready for distribution! ✨")
    else:
        print("\n⚠️ Some tests failed. Review issues before distribution.")
        sys.exit(1)


if __name__ == "__main__":
    main()