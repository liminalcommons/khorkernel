import pytest
from pathlib import Path
import shutil
import tomlkit # Changed to tomlkit
import yaml  # PyYAML for parsing docker-compose.yml
# from pyscaffold.cli import run_cli_with_args # Removed unused import
import logging # Import logging

# Import the actual Pydantic models
from khora_kernel_vnext.extensions.core.manifest import (
    KhoraManifestConfig, KhoraFeaturesConfig, KhoraPathsConfig, 
    KhoraPortsConfig, KhoraPluginsConfig, KhoraDockerPluginConfig
)

# Helper function to create a pyproject.toml for a test project
def create_test_pyproject_toml(project_path: Path, khora_config: dict):
    pyproject_content = {
        "project": {
            "name": project_path.name,
            "version": "0.1.0",
            "description": "Test project",
            "authors": [{"name": "Test Author", "email": "test@example.com"}],
            "requires-python": ">=3.8",
        },
        "build-system": {
            "requires": ["setuptools>=61.0.0", "wheel"],
            "build-backend": "setuptools.build_meta",
            "backend-path": ["."],
        },
        "tool": {"khora": khora_config}
    }
    with open(project_path / "pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(pyproject_content)) # Using tomlkit.dumps

@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary directory for a test project."""
    project_name = "my_test_project"
    project_path = tmp_path / project_name
    project_path.mkdir(parents=True, exist_ok=True)
    return project_path

def test_docker_extension_creates_docker_compose_when_feature_enabled(tmp_project: Path):
    """
    Test that docker-compose.yml is created when the khora.features.docker is true.
    """
    project_name = tmp_project.name
    khora_config = {
        "project_description": "A test project with Docker.",
        "python_version": "3.9",
        "paths": {"api_dir": "service_api", "docs_dir": "docs"},
        "features": {"fastapi": True, "docker": True, "ci_github_actions": False},
        "ports": {"http": 8080},
        "plugins_config": {"docker": {"api_service_name": "my_api_service"}}
    }
    create_test_pyproject_toml(tmp_project, khora_config)

    # Run PyScaffold with the khora-docker extension
    # Note: We need to ensure the khora-core extension runs to parse the manifest
    # and pass the opts to other extensions.
    # For an isolated test of khora-docker, we might need to mock `opts`
    # or ensure the test setup correctly invokes the core extension first.
    # Here, we assume the extension can access the khora_opts if khora-core has run.
    # A more robust integration test would run `putup` on a fixture project.
    
    # Simulate running putup in the project directory
    # We pass the extension directly for this test.
    # In a full `putup` run, extensions are discovered.
    opts = [
        project_name,
        "--khora-docker", # Activate the docker extension
        # We need to simulate that khora-core has parsed the manifest
        # This is a simplification. A full integration test would be better.
        # For now, we rely on the DockerExtension's internal logic to fetch from opts
        # which would be populated by the CoreExtension in a real run.
        # To make this test work standalone for the DockerExtension,
        # we'd need to inject `khora_opts` into `opts` somehow,
        # or the DockerExtension needs to be able to read pyproject.toml itself
        # if the core extension hasn't populated opts.
        # The current DockerExtension code tries to get 'khora' from opts.
        # Let's try to pass it via custom args if PyScaffold allows, or mock.
        # For now, this test will likely fail or skip if khora_opts isn't in opts.
        # We will refine this after seeing the initial run.
        # The DockerExtension's add_docker_compose_file directly uses opts["khora"]
        # which is populated by the CoreExtension.
        # A true integration test would involve running `putup` with all relevant extensions.
    ]
    
    # To properly test, we need to ensure `opts` within `add_docker_compose_file`
    # contains the `khora_config`. PyScaffold's `run_cli_with_args` might not
    # directly allow injecting this complex structure easily for a specific extension's action.
    # We'll assume for now that if `--khora-docker` is passed, and if the Core extension
    # were also active, `opts['khora']` would be populated.
    # The DockerExtension itself doesn't parse pyproject.toml.

    # Let's try running with the actual `putup` command structure
    # This requires the khora-kernel-vnext to be installed or in PYTHONPATH
    
    # For a more direct unit/integration test of the extension action:
    from khora_kernel_vnext.extensions.docker.extension import add_docker_compose_file
    from pyscaffold.actions import ScaffoldOpts, Structure
    
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
        "khora_config": khora_manifest, # Use the actual Pydantic model
        "package": project_name, 
        "author": "Test Author",
        "email": "test@example.com",
        "license": "MIT",
        "url": "http://example.com",
        "description": khora_config["project_description"],
        "version": "0.1.0", # Add version to opts
        "extensions": [], # Mock extensions list
        "force": False,
        "pretend": False,
        "verbose": 0,
        "update": False,
        "ensure_empty": False,
        "namespace": None,
        "command": None, # Mock command
        "parser": None, # Mock parser
        "log_level": logging.INFO, # Mock log_level
        "config_files": [], # Mock config_files
        "config_is_ready": False, # Mock config_is_ready
    }
    
    # Add default PyScaffold structure elements that might be expected
    initial_struct: Structure = {
        project_name: {
            "__init__.py": "content",
            "module.py": "content"
        },
        "pyproject.toml": "content",
        "README.md": "content",
        ".gitignore": "content"
    }

    # Call the action directly
    final_struct, _ = add_docker_compose_file(initial_struct.copy(), mock_opts)

    docker_compose_path = tmp_project / "docker-compose.yml"
    
    # The action modifies `struct` to include "docker-compose.yml"
    assert "docker-compose.yml" in final_struct
    docker_compose_content_tuple = final_struct["docker-compose.yml"]
    assert isinstance(docker_compose_content_tuple, tuple)
    docker_compose_content_str = docker_compose_content_tuple[0]

    # Write the generated content to the actual file path for assertion
    with open(docker_compose_path, "w") as f:
        f.write(docker_compose_content_str)

    assert docker_compose_path.exists()

    with open(docker_compose_path, "r") as f:
        content = yaml.safe_load(f)

    assert content["version"] == "3.8"
    assert "services" in content
    assert khora_config["plugins_config"]["docker"]["api_service_name"] in content["services"]
    service_config = content["services"][khora_config["plugins_config"]["docker"]["api_service_name"]]
    assert service_config["build"]["context"] == f"./{khora_config['paths']['api_dir']}"
    assert service_config["ports"] == [f"{khora_config['ports']['http']}:{khora_config['ports']['http']}"]
    assert service_config["volumes"] == [f"./{khora_config['paths']['api_dir']}:/app/{khora_config['paths']['api_dir']}"]

    # Clean up the temporary project directory
    # shutil.rmtree(tmp_project) # Pytest's tmp_path fixture handles cleanup

def test_docker_extension_skips_when_feature_disabled(tmp_project: Path):
    """
    Test that docker-compose.yml is NOT created when khora.features.docker is false.
    """
    project_name = tmp_project.name
    khora_config = {
        "project_description": "A test project without Docker.",
        "python_version": "3.9",
        "paths": {"api_dir": "api", "docs_dir": "docs"},
        "features": {"fastapi": True, "docker": False}, # Docker is false
        "ports": {"http": 8000},
        "plugins_config": {"docker": {"api_service_name": "api"}}
    }
    # No need to create pyproject.toml on disk for this direct action call

    from khora_kernel_vnext.extensions.docker.extension import add_docker_compose_file
    from pyscaffold.actions import ScaffoldOpts, Structure
    import logging # Required for mock_opts

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
        "author": "Test Author",
        "email": "test@example.com",
        "license": "MIT",
        "url": "http://example.com",
        "description": khora_config["project_description"],
        "version": "0.1.0",
        "extensions": [],
        "force": False,
        "pretend": False,
        "verbose": 0,
        "update": False,
        "ensure_empty": False,
        "namespace": None,
        "command": None, 
        "parser": None, 
        "log_level": logging.INFO, 
        "config_files": [], 
        "config_is_ready": False, 
    }
    initial_struct: Structure = {project_name: {}}

    final_struct, _ = add_docker_compose_file(initial_struct.copy(), mock_opts)

    docker_compose_path = tmp_project / "docker-compose.yml"
    assert "docker-compose.yml" not in final_struct
    assert not docker_compose_path.exists()

    # shutil.rmtree(tmp_project) # Pytest's tmp_path fixture handles cleanup
