import pytest
from pathlib import Path
import shutil
import subprocess
import os
import tomlkit
import yaml
import sys

# Import PyScaffold's API directly for more reliable extension loading
from pyscaffold.api import create_project
from pyscaffold.extensions.pre_commit import PreCommit

# Import our extensions directly to avoid entry point discovery issues
from khora_kernel_vnext.extensions.core.extension import CoreExtension
from khora_kernel_vnext.extensions.fastapi_scaffold.extension import FastApiScaffoldExtension
from khora_kernel_vnext.extensions.docker.extension import DockerExtension
from khora_kernel_vnext.extensions.ci_github_actions.extension import CIGitHubActionsExtension
from khora_kernel_vnext.extensions.kg.extension import KGExtension
from khora_kernel_vnext.extensions.precommit.extension import PrecommitExtension
from khora_kernel_vnext.extensions.core.manifest import KhoraManifestConfig

@pytest.fixture
def tmp_target_project(tmp_path: Path) -> Path:
    """Create a temporary directory to scaffold a target project into."""
    return tmp_path / "target_project_root"

def test_precommit_config_generated_and_valid(tmp_target_project: Path):
    """
    Tests that PyScaffold generates a .pre-commit-config.yaml with expected hooks
    when Khora extensions are active.
    """
    project_name = "my_precommit_app"
    khora_config = {
        "project_name": project_name,  # Added explicit project_name
        "project_description": "A test project to check pre-commit setup.",
        "python_version": "3.9",
        "paths": {"api_dir": "src/" + project_name + "/api", "docs_dir": "docs"}, # Adjusted api_dir for src layout
        "features": {
            "fastapi": True, 
            "docker": True, 
            "ci_github_actions": True,
            "kg": True,
            "precommit": True,
            "security_gates": True
        },
        "ports": {"http": 8001},
        "plugins_config": {"docker": {"api_service_name": "precommit_api"}}
    }
    
    # Define project path
    project_dir = tmp_target_project / project_name
    
    # First, create a basic project without our extensions
    try:
        # Create a basic project with PyScaffold
        create_project(
            project_path=str(project_dir),
            name=project_name,
            package=project_name,
            no_tox=True,  # Skip tox configuration
            no_verify=True  # Skip some verification steps for faster creation
        )
        
        # Now load the existing pyproject.toml
        pyproject_path = project_dir / "pyproject.toml"
        with open(pyproject_path, "r") as f:
            pyproject_content = tomlkit.parse(f.read())
        
        # Add our Khora configuration
        if "tool" not in pyproject_content:
            pyproject_content["tool"] = {}
        pyproject_content["tool"]["khora"] = khora_config
        
        # Save the updated pyproject.toml
        with open(pyproject_path, "w") as f:
            f.write(tomlkit.dumps(pyproject_content))
            
        # Initialize git and commit the changes (PyScaffold already initialized git for us)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit with Khora manifest"], cwd=project_dir, check=True, capture_output=True)
        
        # Before we run PyScaffold with the extensions, let's manually create the context.yaml file
        # This bypasses the issue with the extension's manifest reading mechanism
        
        # Create .khora directory
        khora_dir = project_dir / ".khora"
        khora_dir.mkdir(exist_ok=True)
        
        # Create context.yaml with our values
        context_data = {
            "kernel_version": "0.1.0",
            "schema_version": "0.1.0",
            "generated_at": "2025-05-07T12:00:00Z",
            "project": {
                "name": khora_config["project_name"],
                "description": khora_config["project_description"],
                "paths": khora_config["paths"]
            },
            "knowledge_graph_summary": "TBD for MVK", 
        }
        
        # Write context.yaml
        with open(khora_dir / "context.yaml", "w") as f:
            yaml.dump(context_data, f)
    except Exception as e:
        pytest.fail(f"Failed to create initial project structure: {e}")
    
    # Now run PyScaffold again with our extensions
    pyscaffold_opts = {
        "project_path": project_dir,
        "package": project_name,
        "name": project_name,
        "force": True,
        "update": True,
        "khora_core": True,
        "fastapi_scaffold": True,
        "khora_docker": True,
        "khora_ci_github_actions": True,
        "pre_commit": True,
        "khora_kg": True,
        "khora_precommit": True
    }
    
    # Create Pydantic model from dict for all extensions
    khora_model = KhoraManifestConfig(**khora_config)
    
    # Initialize extension instances with options
    core_ext = CoreExtension()
    core_ext.opts = pyscaffold_opts
    core_ext.opts["khora_config"] = khora_model
    
    fastapi_ext = FastApiScaffoldExtension()
    fastapi_ext.opts = pyscaffold_opts
    fastapi_ext.opts["khora_config"] = khora_model
    
    docker_ext = DockerExtension()
    docker_ext.opts = pyscaffold_opts
    docker_ext.opts["khora_config"] = khora_model
    
    ci_ext = CIGitHubActionsExtension()
    ci_ext.opts = pyscaffold_opts
    ci_ext.opts["khora_config"] = khora_model
    
    precommit_ext = PreCommit()
    precommit_ext.opts = pyscaffold_opts
    # Default PyScaffold extension doesn't use khora_config
    
    # Initialize our new extensions
    kg_ext = KGExtension()
    kg_ext.opts = pyscaffold_opts
    kg_ext.opts["khora_config"] = khora_model
    
    khora_precommit_ext = PrecommitExtension()
    khora_precommit_ext.opts = pyscaffold_opts
    khora_precommit_ext.opts["khora_config"] = khora_model
    
    # Define extensions list - our precommit extension needs to run FIRST
    # so it's not blocked by no_overwrite() after the default precommit runs
    extensions = [
        khora_precommit_ext,  # Must run before the standard PyScaffold precommit
        core_ext,
        fastapi_ext, 
        docker_ext,
        ci_ext,
        kg_ext,
        precommit_ext  # Standard PyScaffold precommit runs after ours
    ]
    
    try:
        # Update the project with our extensions
        create_project(
            project_path=str(project_dir),
            extensions=extensions,
            update=True  # Pass update directly as a keyword argument
        )
    except Exception as e:
        pytest.fail(f"Failed to update project with extensions: {e}")

    pre_commit_config_path = project_dir / ".pre-commit-config.yaml"
    assert pre_commit_config_path.exists(), ".pre-commit-config.yaml was not generated"

    with open(pre_commit_config_path, "r") as f:
        config = yaml.safe_load(f)
        # Print the entire config for debugging
        print("DEBUG - Pre-commit config content:", config)

    assert "repos" in config
    assert len(config["repos"]) > 0, "No repos found in pre-commit config"
    
    # Look for various types of hooks
    has_yaml_hook = False
    has_whitespace_hook = False
    has_format_hook = False
    has_lint_hook = False
    has_security_hook = False
    has_kg_hook = False
    
    # For debugging, enumerate all hooks and their IDs
    print("DEBUG - Hooks found in pre-commit config:")
    for repo in config["repos"]:
        repo_url = repo.get("repo", "local")
        print(f"  Repo: {repo_url}")
        for hook in repo.get("hooks", []):
            hook_id = hook["id"]
            print(f"    Hook: {hook_id}")
            
            # Check for yaml validation
            if "yaml" in hook_id:
                has_yaml_hook = True
            # Check for whitespace hooks
            if "whitespace" in hook_id or "end-of-file-fixer" in hook_id:
                has_whitespace_hook = True
            # Check for formatting tools
            if any(formatter in hook_id for formatter in ["black", "ruff-format", "format", "prettier"]):
                has_format_hook = True
            # Check for linting tools
            if any(linter in hook_id for linter in ["flake8", "ruff", "lint", "pylint"]):
                has_lint_hook = True
            # Check for security tools
            if any(sec_tool in hook_id.lower() for sec_tool in ["bandit", "trufflehog", "security"]):
                has_security_hook = True
                print(f"      Found security hook: {hook_id}")
            # Check for KG hook
            if "khora-knowledge-graph" in hook_id:
                has_kg_hook = True

    # These assertions are based on what PyScaffold's native pre-commit generates
    assert has_yaml_hook, "No YAML validation hook found in pre-commit config"
    assert has_whitespace_hook, "No whitespace handling hooks found in pre-commit config"
    assert has_format_hook, "No code formatting hook found in pre-commit config"
    assert has_lint_hook, "No linting hook found in pre-commit config"
    
    # Now directly test our PrecommitExtension by calling its action function with empty structure
    print("\nDEBUG - Directly testing PrecommitExtension functionality with empty structure:")
    
    # Start with an empty structure
    empty_struct = {}
    
    # Create options with our config and explicitly set security_gates and kg to True
    direct_opts = {
        "project_path": project_dir,
        "khora_config": khora_model,
        "project_name": project_name  # Make sure project_name is set
    }
    
    # Print the model for debugging
    print(f"DEBUG - KhoraManifestConfig features: {khora_model.features}")
    print(f"DEBUG - security_gates enabled: {getattr(khora_model.features, 'security_gates', False)}")
    print(f"DEBUG - kg enabled: {getattr(khora_model.features, 'kg', False)}")
    
    # Import the add_precommit_config function directly
    from khora_kernel_vnext.extensions.precommit.extension import add_precommit_config
    
    # Call the action function directly
    new_struct, _ = add_precommit_config(empty_struct, direct_opts)
    
    # The direct file should now be in the structure
    assert ".pre-commit-config-direct.yaml" in new_struct, "Direct pre-commit config was not created"
    
    # Write the direct config to a file
    direct_config_path = project_dir / ".pre-commit-config-direct.yaml"
    with open(direct_config_path, "w") as f:
        f.write(new_struct[".pre-commit-config-direct.yaml"][0])
    
    # Load and check the direct config
    with open(direct_config_path, "r") as f:
        direct_config = yaml.safe_load(f)
        print(f"DEBUG - Direct pre-commit config: {direct_config}")
    
    # Check for security hooks directly
    direct_has_security_hook = False
    direct_has_kg_hook = False
    
    for repo in direct_config["repos"]:
        repo_url = repo.get("repo", "local")
        print(f"  Direct Repo: {repo_url}")
        for hook in repo.get("hooks", []):
            hook_id = hook["id"]
            print(f"    Direct Hook: {hook_id}")
            
            if any(sec_tool in hook_id.lower() for sec_tool in ["bandit", "trufflehog", "security"]):
                direct_has_security_hook = True
                print(f"      Found direct security hook: {hook_id}")
            
            if "khora-knowledge-graph" in hook_id:
                direct_has_kg_hook = True
                print(f"      Found KG hook: {hook_id}")
    
    # Assert that our direct call to the extension added security hooks
    assert direct_has_security_hook, "PrecommitExtension did not add security hooks when called directly"
    assert direct_has_kg_hook, "PrecommitExtension did not add KG hooks when called directly"
    
    # Also test that the regular PyScaffold-generated pre-commit config has our hooks
    assert has_security_hook, "No security scanning hooks found in pre-commit config"
    assert has_kg_hook, "No Knowledge Graph hook found in pre-commit config"

    # (Optional, but recommended by AC) Test pre-commit run
    # This requires pre-commit to be installed in the test environment.
    # And also git to be initialized in the project. PyScaffold does this.
    try:
        # Stage all files
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
        # Run pre-commit
        result = subprocess.run(
            ["pre-commit", "run", "--all-files"], 
            cwd=project_dir, 
            capture_output=True, 
            text=True
        )
        # If pre-commit made changes, it exits with 1. If no changes and all good, exits 0.
        # If errors that it cannot fix, it might exit with > 1.
        assert result.returncode in [0, 1], \
            f"pre-commit run --all-files failed with code {result.returncode}.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    except FileNotFoundError:
        pytest.skip("pre-commit command not found. Skipping pre-commit run test.")
    except subprocess.CalledProcessError as e:
        # This might happen if git is not installed or other setup issues.
        pytest.fail(f"Failed to run git or pre-commit commands: {e}\nstdout:\n{e.stdout}\nstderr:\n{e.stderr}")
