import pytest
from pathlib import Path
import shutil
import tomlkit # Changed to tomlkit
import yaml # For parsing YAML if needed, though direct string comparison might be enough
import logging
from pyscaffold.actions import ScaffoldOpts, Structure
from khora_kernel_vnext.extensions.ci_github_actions.extension import add_ci_workflow_file

# Import the actual Pydantic models
from khora_kernel_vnext.extensions.core.manifest import (
    KhoraManifestConfig, KhoraFeaturesConfig, KhoraPathsConfig, 
    KhoraPortsConfig, KhoraPluginsConfig, KhoraDockerPluginConfig
)

# Helper function (can be shared or moved to a conftest.py later)
def create_test_pyproject_toml(project_path: Path, khora_config: dict):
    pyproject_content = {
        "project": {
            "name": project_path.name,
            "version": "0.1.0",
            "description": "Test project for CI",
            "authors": [{"name": "Test CI Author", "email": "test_ci@example.com"}],
            "requires-python": ">=3.8",
        },
        "build-system": {
            "requires": ["setuptools>=61.0.0", "wheel"],
            "build-backend": "setuptools.build_meta",
            "backend-path": ["."],
        },
        "tool": {"khora": khora_config}
    }
    # Ensure parent directory exists if project_path is just a name
    # (project_path / "pyproject.toml").parent.mkdir(parents=True, exist_ok=True)
    with open(project_path / "pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(pyproject_content)) # Using tomlkit.dumps

@pytest.fixture
def tmp_project_ci(tmp_path: Path) -> Path:
    """Create a temporary directory for a test CI project."""
    project_name = "my_ci_test_project"
    project_path = tmp_path / project_name
    project_path.mkdir(parents=True, exist_ok=True)
    return project_path

def test_ci_extension_creates_workflow_when_feature_enabled(tmp_project_ci: Path):
    """
    Test that .github/workflows/ci.yml is created when khora.features.ci_github_actions is true.
    """
    project_name = tmp_project_ci.name
    python_version_manifest = "3.10"
    khora_config = {
        "project_description": "A test project with CI.",
        "python_version": python_version_manifest,
        "paths": {"api_dir": "api", "docs_dir": "docs"},
        "features": {"fastapi": False, "docker": False, "ci_github_actions": True},
        "ports": {"http": 8000},
        "plugins_config": {}
    }
    # create_test_pyproject_toml(tmp_project_ci, khora_config) # Not strictly needed for direct action call

    # Create an actual Pydantic model instance
    khora_manifest = KhoraManifestConfig(
        project_name=project_name,
        project_description=khora_config["project_description"],
        python_version=python_version_manifest,
        paths=KhoraPathsConfig(**khora_config["paths"]),
        features=KhoraFeaturesConfig(**khora_config["features"]),
        ports=KhoraPortsConfig(**khora_config["ports"]),
        plugins_config=KhoraPluginsConfig(
            docker=KhoraDockerPluginConfig(**khora_config.get("plugins_config", {}).get("docker", {}))
        )
    )
    
    mock_opts: ScaffoldOpts = {
        "project_name": project_name,
        "khora_config": khora_manifest,
        "package": project_name,
        "author": "Test Author", "email": "test@example.com", "license": "MIT", "url": "http://example.com",
        "description": khora_config["project_description"], "version": "0.1.0",
        "extensions": [], "force": False, "pretend": False, "verbose": 0, "update": False, "ensure_empty": False,
        "namespace": None, "command": None, "parser": None, "log_level": logging.INFO,
        "config_files": [], "config_is_ready": False,
    }
    
    initial_struct: Structure = {project_name: {}} # Start with a basic structure

    final_struct, _ = add_ci_workflow_file(initial_struct.copy(), mock_opts)

    # Assertions for the structure
    assert ".github" in final_struct
    assert "workflows" in final_struct[".github"]
    assert "ci.yml" in final_struct[".github"]["workflows"]
    
    ci_yml_content_tuple = final_struct[".github"]["workflows"]["ci.yml"]
    assert isinstance(ci_yml_content_tuple, tuple)
    ci_yml_content_str = ci_yml_content_tuple[0]

    # Write to a file for easier inspection if needed, and for path-based assertions
    ci_workflow_dir = tmp_project_ci / ".github" / "workflows"
    ci_workflow_dir.mkdir(parents=True, exist_ok=True)
    ci_workflow_path = ci_workflow_dir / "ci.yml"
    
    with open(ci_workflow_path, "w") as f:
        f.write(ci_yml_content_str)

    assert ci_workflow_path.exists()

    # Verify key content (can be more detailed)
    assert f"CI Workflow for {project_name}" in ci_yml_content_str
    assert f'python-version: ["{python_version_manifest}"]' in ci_yml_content_str
    assert "actions/checkout@v3" in ci_yml_content_str
    assert "actions/setup-python@v3" in ci_yml_content_str
    assert "uv pip install --system .[dev]" in ci_yml_content_str
    assert "uv ruff check ." in ci_yml_content_str
    assert "uv ruff format --check ." in ci_yml_content_str
    assert "uv pytest" in ci_yml_content_str


def test_ci_extension_skips_when_feature_disabled(tmp_project_ci: Path):
    """
    Test that .github/workflows/ci.yml is NOT created when khora.features.ci_github_actions is false.
    """
    project_name = tmp_project_ci.name
    khora_config = {
        "project_description": "A test project without CI.",
        "python_version": "3.9",
        "paths": {"api_dir": "api", "docs_dir": "docs"},
        "features": {"ci_github_actions": False}, # CI feature is false
        "ports": {"http": 8000},
        "plugins_config": {}
    }

    # Create an actual Pydantic model instance
    khora_manifest = KhoraManifestConfig(
        project_name=project_name,
        project_description=khora_config["project_description"],
        python_version=khora_config["python_version"],
        paths=KhoraPathsConfig(**khora_config["paths"]),
        features=KhoraFeaturesConfig(**khora_config["features"]),
        ports=KhoraPortsConfig(**khora_config["ports"]),
        plugins_config=KhoraPluginsConfig(
            docker=KhoraDockerPluginConfig(**khora_config.get("plugins_config", {}).get("docker", {}))
        )
    )
    
    mock_opts: ScaffoldOpts = {
        "project_name": project_name,
        "khora_config": khora_manifest,
        "package": project_name, 
        "author": "Test Author", "email": "test@example.com", "license": "MIT", "url": "http://example.com",
        "description": khora_config["project_description"], "version": "0.1.0",
        "extensions": [], "force": False, "pretend": False, "verbose": 0, "update": False, "ensure_empty": False,
        "namespace": None, "command": None, "parser": None, "log_level": logging.INFO,
        "config_files": [], "config_is_ready": False,
    }
    initial_struct: Structure = {project_name: {}}

    final_struct, _ = add_ci_workflow_file(initial_struct.copy(), mock_opts)

    ci_workflow_path = tmp_project_ci / ".github" / "workflows" / "ci.yml"
    
    assert ".github" not in final_struct or "workflows" not in final_struct.get(".github", {}) or \
           "ci.yml" not in final_struct.get(".github", {}).get("workflows", {})
    assert not ci_workflow_path.exists()
