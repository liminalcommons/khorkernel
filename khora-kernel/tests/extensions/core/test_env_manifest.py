"""
Tests for environment-specific manifest configuration.
"""
import os
import pytest
from pathlib import Path
import tempfile
import shutil

from khora_kernel_vnext.extensions.core.manifest import (
    KhoraManifestConfig,
    KhoraManifestNotFoundError,
    KhoraManifestInvalidError,
    deep_merge_dicts
)

# Test data for environment layering
LAYERED_CONFIG_TOML = """
[project]
name = "env-test-project"
version = "0.1.0"

[tool.khora]
project_name = "EnvTestProject"
project_description = "Project with environment-specific configurations"
python_version = "3.11"

[tool.khora.features]
fastapi = true
docker = true
ci_github_actions = true

[tool.khora.paths]
api_dir = "src/api"

[tool.khora.env.dev]
project_description = "Development version of the project"
python_version = "3.12"

[tool.khora.env.dev.features]
ci_github_actions = false
kg = true

[tool.khora.env.prod]
project_description = "Production version of the project"

[tool.khora.env.prod.paths]
api_dir = "src/api/production"

[tool.khora.env.prod.ports]
http = 80
"""


class TestEnvironmentManifest:
    """Tests for environment-specific manifest configuration."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for the project."""
        temp_dir = tempfile.mkdtemp()
        try:
            yield Path(temp_dir)
        finally:
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_pyproject(self, temp_project_dir):
        """Create a sample pyproject.toml with environment-specific configurations."""
        pyproject_path = temp_project_dir / "pyproject.toml"
        with open(pyproject_path, "w") as f:
            f.write(LAYERED_CONFIG_TOML)
        return temp_project_dir

    def test_deep_merge_dicts(self):
        """Test deep_merge_dicts function."""
        base = {
            "name": "base",
            "nested": {
                "a": 1,
                "b": 2,
                "deep": {
                    "x": True
                }
            },
            "list": [1, 2, 3]
        }
        
        override = {
            "name": "override",
            "nested": {
                "b": 200,
                "c": 3,
                "deep": {
                    "y": False
                }
            },
            "new_key": "new value"
        }
        
        result = deep_merge_dicts(base, override)
        
        # Check base values are preserved when not overridden
        assert result["nested"]["a"] == 1
        # Check overridden values
        assert result["name"] == "override"
        assert result["nested"]["b"] == 200
        # Check new values in override
        assert result["nested"]["c"] == 3
        assert result["new_key"] == "new value"
        # Check deep merging
        assert result["nested"]["deep"]["x"] == True
        assert result["nested"]["deep"]["y"] == False
        # Check lists are not merged but replaced
        assert result["list"] == [1, 2, 3]

    def test_base_config_loading(self, sample_pyproject):
        """Test loading base config without environment overrides."""
        config = KhoraManifestConfig.from_project_toml(sample_pyproject)
        
        # Check basic properties
        assert config.project_name == "EnvTestProject"
        assert config.project_description == "Project with environment-specific configurations"
        assert config.python_version == "3.11"
        
        # Check feature flags
        assert config.features.fastapi == True
        assert config.features.docker == True
        assert config.features.ci_github_actions == True
        assert config.features.kg == False
        
        # Check active environment
        assert config.active_environment is None
        
        # Check paths
        assert config.paths.api_dir == Path("src/api")
        
        # Check ports
        assert config.ports.http == 8000

    def test_dev_environment_loading(self, sample_pyproject):
        """Test loading dev environment config with overrides."""
        config = KhoraManifestConfig.from_project_toml_with_env(sample_pyproject, env="dev")
        
        # Check overridden properties
        assert config.project_name == "EnvTestProject"  # Not overridden
        assert config.project_description == "Development version of the project"  # Overridden
        assert config.python_version == "3.12"  # Overridden
        
        # Check feature flags (overridden and not)
        assert config.features.fastapi == True  # Not overridden
        assert config.features.docker == True  # Not overridden
        assert config.features.ci_github_actions == False  # Overridden
        assert config.features.kg == True  # Overridden
        
        # Check active environment
        assert config.active_environment == "dev"
        
        # Check paths (not overridden)
        assert config.paths.api_dir == Path("src/api")
        
        # Check ports (not overridden)
        assert config.ports.http == 8000

    def test_prod_environment_loading(self, sample_pyproject):
        """Test loading prod environment config with overrides."""
        config = KhoraManifestConfig.from_project_toml_with_env(sample_pyproject, env="prod")
        
        # Check overridden properties
        assert config.project_name == "EnvTestProject"  # Not overridden
        assert config.project_description == "Production version of the project"  # Overridden
        assert config.python_version == "3.11"  # Not overridden
        
        # Check feature flags (not overridden)
        assert config.features.fastapi == True
        assert config.features.docker == True
        assert config.features.ci_github_actions == True
        assert config.features.kg == False
        
        # Check active environment
        assert config.active_environment == "prod"
        
        # Check paths (overridden)
        assert config.paths.api_dir == Path("src/api/production")
        
        # Check ports (overridden)
        assert config.ports.http == 80

    def test_nonexistent_environment(self, sample_pyproject):
        """Test loading a non-existent environment falls back to base config."""
        config = KhoraManifestConfig.from_project_toml_with_env(sample_pyproject, env="staging")
        
        # Should be identical to the base config
        assert config.project_name == "EnvTestProject"
        assert config.project_description == "Project with environment-specific configurations"
        assert config.python_version == "3.11"
        assert config.features.fastapi == True
        assert config.features.docker == True
        assert config.features.ci_github_actions == True
        assert config.features.kg == False
        assert config.paths.api_dir == Path("src/api")
        assert config.ports.http == 8000
        
        # But active_environment should be None
        assert config.active_environment is None
