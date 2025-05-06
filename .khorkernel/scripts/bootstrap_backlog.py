#!/usr/bin/env python3
# Khora Kernel - Bootstrap Script v1.0.2
# Sets up a new project based on the Khora Kernel.

# --- Python Version Check ---
import sys
if sys.version_info < (3, 8):
    print("Error: This script requires Python 3.8 or higher.", file=sys.stderr)
    sys.exit(1)

import subprocess
import pathlib
import yaml
import json
import shutil
import argparse
import os
import importlib.util
from typing import Dict, Any, List, Optional

# --- Configuration ---
KERNEL_DIR_NAME = ".khorkernel"
MANIFEST_FILE = "KERNEL_MANIFEST.yaml"
SPRINT0_FILE = "bootstrap_sprint0.json"
GH_WORKFLOW_DIR = ".github/workflows"
OUTPUT_COMPOSE_FILE = "docker-compose.yml"
LITE_COMPOSE_FILE = "docker-compose.lite.yml"
OUTPUT_CONTEXT_DELTA_FILE = "context-delta.yml"
GITIGNORE_FILE = ".gitignore"
KERNEL_IGNORES = ['.khora/', '.khora', 'kg/', '*.pyc', '__pycache__/']
REQUIREMENTS_FILE = "requirements-kernel.txt"
VERSION_FILE = "VERSION"


# --- Helper Functions ---
def get_kernel_version(kernel_dir: pathlib.Path) -> str:
    """Get the kernel version from the VERSION file."""
    try:
        version_path = kernel_dir / VERSION_FILE
        if version_path.exists():
            return version_path.read_text(encoding='utf-8').strip()
        return "unknown"
    except Exception as e:
        print(f"Warning: Could not read kernel version: {e}", file=sys.stderr)
        return "unknown"


def check_command_exists(command: str) -> bool:
    """Check if a command exists on the system path."""
    try:
        # Use shell=True cautiously, needed sometimes for Windows pathing/aliases
        is_windows = os.name == 'nt'
        result = subprocess.run([command, "--version"], capture_output=True, check=True, text=True, shell=is_windows, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_pip_package(package: str, version: Optional[str] = None) -> bool:
    """Attempt to install a package using pip. Returns success status."""
    print(f"Attempting to install '{package}{f'=={version}' if version else ''}' using pip...")
    try:
        # Ensure pip itself is available
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
        
        # Install the package
        cmd = [sys.executable, "-m", "pip", "install"]
        if version:
            cmd.append(f"{package}=={version}")
        else:
            cmd.append(package)
            
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Successfully installed '{package}'.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing '{package}': {e.stderr or e.stdout}", file=sys.stderr)
        print(f"Please install '{package}' manually.", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"Error: '{sys.executable} -m pip' command failed. Please ensure Python and pip are correctly installed and in your PATH.", file=sys.stderr)
        return False


def install_kernel_requirements(kernel_dir: pathlib.Path) -> bool:
    """Install dependencies from requirements-kernel.txt. Returns success status."""
    req_file = kernel_dir / REQUIREMENTS_FILE
    if not req_file.exists():
        print(f"Warning: Kernel requirements file not found at '{req_file}'. Skipping dependency installation.", file=sys.stderr)
        return False
    
    try:
        print(f"Installing kernel dependencies from {req_file.relative_to(kernel_dir.parent)}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            check=True, capture_output=True, text=True
        )
        print("Successfully installed kernel dependencies.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing kernel dependencies: {e.stderr or e.stdout}", file=sys.stderr)
        print("Continuing with bootstrap process, but some features may not work correctly.", file=sys.stderr)
        return False


def check_jinja2() -> bool:
    """Ensure Jinja2 is available, attempt to install if missing."""
    try:
        import jinja2
        return True
    except ImportError:
        print("Jinja2 not found. Attempting to install...", file=sys.stderr)
        return install_pip_package("jinja2", "3.1.2") and install_pip_package("pyyaml", "6.0.1")


def render_template(env, template_rel_path: str, context: Dict[str, Any], output_path: pathlib.Path):
    """Renders a Jinja template to the specified output path."""
    try:
        # Add a filter for path normalization
        def normalize_path(p):
            return p.replace('\\', '/') if p else p
        env.filters['normalize_path'] = normalize_path

        template = env.get_template(template_rel_path)
        rendered_content = template.render(**context)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered_content, encoding='utf-8')
        print(f"Rendered '{template_rel_path}' -> '{output_path.relative_to(output_path.parent.parent)}'") # Show relative path
    except Exception as e:
        print(f"Error rendering template '{template_rel_path}': {e}", file=sys.stderr)


def update_gitignore(root_dir: pathlib.Path, ignores: List[str]):
    """Add kernel-specific ignores to the project's .gitignore file."""
    gitignore_path = root_dir / GITIGNORE_FILE
    new_lines = []
    existing_lines = set()
    header = "# Khora Kernel Ignores"

    if gitignore_path.exists():
        try:
            existing_content = gitignore_path.read_text(encoding='utf-8')
            existing_lines = set(line.strip() for line in existing_content.splitlines())
        except IOError as e:
            print(f"Warning: Could not read existing .gitignore file: {e}", file=sys.stderr)
            # Continue without existing lines

    needs_header = header not in existing_lines
    needs_update = False
    for ignore_pattern in ignores:
        if ignore_pattern not in existing_lines:
            new_lines.append(ignore_pattern)
            needs_update = True

    if needs_update:
        print(f"Updating '{gitignore_path}'...")
        try:
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                if needs_header:
                    f.write(f"\n{header}\n")
                for line in new_lines:
                    f.write(f"{line}\n")
            print(f"Added/updated {len(new_lines)} entries in .gitignore.")
        except IOError as e:
            print(f"Error writing to .gitignore file: {e}", file=sys.stderr)
    else:
        print(f".gitignore already contains necessary kernel ignores.")


def load_manifest(manifest_path: pathlib.Path) -> Dict[str, Any]:
    """Load the KERNEL_MANIFEST.yaml file with error handling."""
    try:
        if not manifest_path.exists():
            print(f"Error: Manifest file not found at '{manifest_path}'.", file=sys.stderr)
            sys.exit(1)
            
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.safe_load(f)
            
        if not isinstance(manifest, dict):
            print(f"Error: Manifest content is not a dictionary.", file=sys.stderr)
            sys.exit(1)
            
        return manifest
    except yaml.YAMLError as e:
        print(f"Error parsing manifest file '{manifest_path}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading manifest file '{manifest_path}': {e}", file=sys.stderr)
        sys.exit(1)


def load_sprint0_issues(sprint0_path: pathlib.Path) -> List[Dict[str, Any]]:
    """Load the bootstrap_sprint0.json file with error handling."""
    if not sprint0_path.exists():
        print(f"Error: Sprint-0 issue file not found at '{sprint0_path}'.", file=sys.stderr)
        return []
        
    try:
        with open(sprint0_path, 'r', encoding='utf-8') as f:
            issues = json.load(f)
            
        if not isinstance(issues, list):
            print(f"Error: Sprint-0 file does not contain a list of issues.", file=sys.stderr)
            return []
            
        # Quick validation of issue structure
        for i, issue in enumerate(issues):
            if not isinstance(issue, dict) or "title" not in issue or "body" not in issue:
                print(f"Warning: Invalid issue format at index {i} in '{sprint0_path.name}'.", file=sys.stderr)
                
        return issues
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in Sprint-0 issue file '{sprint0_path}': {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error loading Sprint-0 issue file '{sprint0_path}': {e}", file=sys.stderr)
        return []


def check_gh_auth() -> bool:
    """Check GitHub CLI authentication status."""
    try:
        is_windows = os.name == 'nt'
        result = subprocess.run(["gh", "auth", "status"], check=True, capture_output=True, text=True, shell=is_windows, timeout=10)
        print("GitHub CLI authenticated.")
        return True
    except subprocess.CalledProcessError as e:
        auth_error_msg = e.stderr or "Unknown error during 'gh auth status'."
        print(f"Error: GitHub CLI authentication failed: {auth_error_msg.strip()}", file=sys.stderr)
        print("Please run 'gh auth login' and try again, or run with --skip-issues.", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Error: 'gh' command not found. Install GitHub CLI or run with --skip-issues.", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("Error: 'gh auth status' timed out. Check network or GitHub CLI status.", file=sys.stderr)
        return False


def create_github_issue(title: str, body: str, labels: List[str]) -> bool:
    """Create a GitHub issue using the gh CLI. Returns success status."""
    try:
        is_windows = os.name == 'nt'
        cmd = ["gh", "issue", "create", "--title", title, "--body", body]
        if labels:
            cmd.extend(["--label", ",".join(labels)])
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, shell=is_windows, timeout=30)
        return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or "Unknown error"
        
        # Check for rate limit errors specifically
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            print(f"GitHub API rate limit exceeded. Wait a few minutes before trying again.", file=sys.stderr)
        else:
            print(f"Error creating issue '{title}':\n{error_msg}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error creating issue '{title}': {e}", file=sys.stderr)
        return False


def load_plugin(plugin_name: str, kernel_dir: pathlib.Path) -> Optional[Any]:
    """Load a plugin module by name if it exists."""
    plugin_dir = kernel_dir / "plugins" / plugin_name
    plugin_file = plugin_dir / "plugin.py"
    
    if not plugin_dir.exists() or not plugin_file.exists():
        print(f"Warning: Plugin '{plugin_name}' directory or plugin.py file not found.", file=sys.stderr)
        return None
    
    try:
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
        if spec is None or spec.loader is None:
            print(f"Warning: Could not load plugin '{plugin_name}'. Invalid module specification.", file=sys.stderr)
            return None
            
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)
        return plugin_module
    except Exception as e:
        print(f"Error loading plugin '{plugin_name}': {e}", file=sys.stderr)
        return None


# --- Main Logic ---
def main():
    parser = argparse.ArgumentParser(description="Khora Kernel Bootstrap Script v1.0.2")
    parser.add_argument(
        "--regenerate-only",
        action="store_true",
        help="Only regenerate templates (Docker Compose, CI); skip Git, Issues, pre-commit.",
    )
    parser.add_argument(
        "--skip-issues",
        action="store_true",
        help="Skip creating GitHub issues.",
    )
    parser.add_argument(
        "--skip-git",
        action="store_true",
        help="Skip git add and commit steps.",
    )
    parser.add_argument(
        "--skip-precommit-install",
        action="store_true",
        help="Skip attempting to install pre-commit hooks.",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip installing kernel dependencies.",
    )
    args = parser.parse_args()

    project_root = pathlib.Path('.').resolve()
    kernel_dir = project_root / KERNEL_DIR_NAME

    kernel_version = get_kernel_version(kernel_dir)
    print(f"--- Khora Kernel Bootstrap v{kernel_version} (Project Root: {project_root}) ---")

    if not kernel_dir.is_dir():
        print(f"Error: Kernel directory '{KERNEL_DIR_NAME}' not found in the current directory.", file=sys.stderr)
        print("Please copy the kernel directory here before running bootstrap.", file=sys.stderr)
        sys.exit(1)

    # --- Dependency Checks ---
    print("Checking dependencies...")
    if not check_command_exists("git"):
        print("Error: 'git' command not found. Please install Git.", file=sys.stderr)
        sys.exit(1)

    # Install kernel dependencies from requirements-kernel.txt
    if not args.skip_deps:
        install_kernel_requirements(kernel_dir)
    
    # Ensure Jinja2 is available
    if not check_jinja2():
        print("Error: Failed to install required Jinja2 package. Cannot continue.", file=sys.stderr)
        sys.exit(1)
    
    # Import Jinja2 (should be available now)
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        print("Error: Jinja2 import failed even after installation attempt.", file=sys.stderr)
        sys.exit(1)

    # Check GitHub CLI if we're going to create issues
    if not args.skip_issues and not args.regenerate_only:
        if not check_command_exists("gh"):
            print("Error: 'gh' (GitHub CLI) command not found, required for creating issues.", file=sys.stderr)
            print("Install it from https://cli.github.com/ or run with --skip-issues.", file=sys.stderr)
            sys.exit(1)
        
        if not check_gh_auth():
            print("GitHub authentication failed. Run with --skip-issues to bypass issue creation.", file=sys.stderr)
            sys.exit(1)

    # --- Load Manifest ---
    manifest_path = kernel_dir / MANIFEST_FILE
    print(f"Loading manifest: {manifest_path.relative_to(project_root)}")
    manifest = load_manifest(manifest_path)
    print(f"Project configured: {manifest.get('project', 'N/A')}")

    # --- Setup Jinja Environment ---
    jinja_env = Environment(
        loader=FileSystemLoader(str(kernel_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True
    )

    # --- Render Templates ---
    print("Rendering templates...")
    
    # 1. Docker Compose (main)
    render_template(jinja_env, "compose/docker-compose.j2", manifest, project_root / OUTPUT_COMPOSE_FILE)
    
    # 2. Docker Compose Lite (if enabled)
    if manifest.get("features", {}).get("lite_mode_available", False):
        render_template(jinja_env, "compose/docker-compose.lite.j2", manifest, project_root / LITE_COMPOSE_FILE)

    # 3. CI Workflows
    workflow_out_dir = project_root / GH_WORKFLOW_DIR
    workflow_out_dir.mkdir(parents=True, exist_ok=True)

    render_template(jinja_env, "ci/ci.j2", manifest, workflow_out_dir / "ci.yml")
    render_template(jinja_env, "ci/docker-build.j2", manifest, workflow_out_dir / "docker-build.yml")
    render_template(jinja_env, "ci/context-delta.yml", manifest, workflow_out_dir / "context-delta.yml")
    
    # 4. Pre-commit config
    render_template(jinja_env, "ci_templates/precommit.j2", manifest, project_root / ".pre-commit-config.yaml")

    # --- Process Plugins ---
    active_plugins = manifest.get("plugins", [])
    if active_plugins:
        print(f"Processing {len(active_plugins)} activated plugins...")
        for plugin_name in active_plugins:
            plugin_module = load_plugin(plugin_name, kernel_dir)
            if plugin_module and hasattr(plugin_module, "render"):
                try:
                    print(f"Running plugin '{plugin_name}'...")
                    plugin_module.render(project_root, manifest, jinja_env)
                except Exception as e:
                    print(f"Error during plugin '{plugin_name}' execution: {e}", file=sys.stderr)
            else:
                print(f"Warning: Plugin '{plugin_name}' has no 'render' function or failed to load.", file=sys.stderr)

    if args.regenerate_only:
        print("--- Regeneration complete. Skipping Git, Issues, and pre-commit steps. ---")
        sys.exit(0)

    # --- Update .gitignore ---
    update_gitignore(project_root, KERNEL_IGNORES)

    # --- Git Commit ---
    if not args.skip_git:
        print("Adding files and creating initial commit...")
        try:
            # Check if there's anything to commit first
            status_result = subprocess.run(["git", "status", "--porcelain"], check=True, capture_output=True, text=True)
            if status_result.stdout:
                subprocess.run(["git", "add", "."], check=True, capture_output=True)
                commit_msg = f"chore(kernel): initialise project from Khora Kernel v{kernel_version}"
                subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
                print(f"Created initial commit: '{commit_msg}'")
            else:
                print("No changes detected; skipping initial commit.")

        except subprocess.CalledProcessError as e:
            print(f"Warning: Git command failed.", file=sys.stderr)
            print(e.stderr or e.stdout, file=sys.stderr)
        except FileNotFoundError:
             print("Warning: 'git' command failed. Is git installed and initialized?", file=sys.stderr)

    # --- Create GitHub Issues ---
    if not args.skip_issues:
        print("Creating Sprint-0 GitHub Issues...")
        sprint0_path = kernel_dir / SPRINT0_FILE
        issues = load_sprint0_issues(sprint0_path)
        
        if not issues:
            print("No valid issues found. Skipping issue creation.", file=sys.stderr)
        else:
            created_count = 0
            total_issues = len(issues)
            print(f"Found {total_issues} issues to create.")
            
            for i, issue in enumerate(issues):
                # Simple templating in issue body/title if needed (replace manifest vars)
                title = issue["title"].replace('{{ project }}', manifest.get('project','app'))
                
                # Process body with more advanced templating
                body = issue.get("body", "")
                for key, value in manifest.items():
                    if isinstance(value, str):
                        body = body.replace(f"{{{{ {key} }}}}", value)
                
                # Handle nested structures like features
                for feature, enabled in manifest.get("features", {}).items():
                    body = body.replace(f"{{{{ features.{feature} }}}}", str(enabled))
                
                # Handle paths
                for path_key, path_value in manifest.get("paths", {}).items():
                    body = body.replace(f"{{{{ paths.{path_key} }}}}", path_value)
                
                labels = issue.get("labels", [])
                
                print(f"  Creating issue {i+1}/{total_issues}: '{title}'...")
                if create_github_issue(title, body, labels):
                    created_count += 1
                else:
                    print(f"  Failed to create issue: '{title}'")
                    
                    # If we fail early, it might be a rate-limit issue, so don't hammer the API
                    if created_count == 0 and i < 2:
                        print("Issues creation failing. Might be a rate limit or authentication issue. Aborting issue creation.", file=sys.stderr)
                        break

            print(f"Created {created_count}/{total_issues} Sprint-0 issues.")

    # --- Pre-commit Installation ---
    if not args.skip_precommit_install:
        print("Checking and potentially installing pre-commit hooks...")
        precommit_cmd = "pre-commit" # Adjust if needed for specific envs
        if check_command_exists(precommit_cmd):
            try:
                is_windows = os.name == 'nt'
                subprocess.run([precommit_cmd, "install"], check=True, capture_output=True, text=True, shell=is_windows)
                print("Pre-commit hooks installed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Warning: '{precommit_cmd} install' failed. Maybe already installed or repo not configured?", file=sys.stderr)
                # print(e.stderr)
            except FileNotFoundError:
                 print(f"Warning: '{precommit_cmd}' command failed despite check. Check PATH.", file=sys.stderr)
        else:
            print(f"'{precommit_cmd}' command not found.")
            if install_pip_package("pre-commit"):
                # Try installing hooks again after package install
                if check_command_exists(precommit_cmd):
                     try:
                         is_windows = os.name == 'nt'
                         subprocess.run([precommit_cmd, "install"], check=True, capture_output=True, text=True, shell=is_windows)
                         print("Pre-commit hooks installed successfully after package installation.")
                     except Exception as e:
                         print(f"Warning: '{precommit_cmd} install' failed even after package installation: {e}", file=sys.stderr)
                else:
                     print(f"Failed to find 'pre-commit' command after installation. Please install it manually.", file=sys.stderr)
            else:
                print(f"Failed to install 'pre-commit' automatically. Please install it manually (`pip install pre-commit`) and run `pre-commit install`.", file=sys.stderr)

    # --- Generate Secure Credentials (Optional) ---
    try:
        # Run the credential generator if it exists
        creds_script = kernel_dir / "scripts" / "gen_secure_creds.py"
        if creds_script.exists():
            print("Generating secure development credentials...")
            # Just run the script, don't capture output (it will print its own messages)
            subprocess.run([sys.executable, str(creds_script)], check=False)
    except Exception as e:
        print(f"Note: Failed to generate secure credentials: {e}", file=sys.stderr)

    print("--- Bootstrap complete! ---")
    print("Next steps:")
    print("  1. Review the generated files (docker-compose.yml, .github/workflows/).")
    print("  2. Implement your application code (e.g., in 'src/app/api').")
    if args.skip_git:
        print("  3. Commit any changes (you skipped the automatic git step).")
    print(f"  4. Push your branch: git push origin {os.environ.get('GITHUB_HEAD_REF', 'main')}.")
    if args.skip_issues:
        print("  5. Create your initial Sprint-0 issues (you skipped automatic issue creation).")
    else:
        print("  5. Check GitHub for your Sprint-0 issues and start developing!")
    print(f"  6. For lightweight development, use: docker compose --profile lite up")


if __name__ == "__main__":
    main()
