"""
Integration tests for environment-specific manifest layering.
"""
import os
import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from click.testing import CliRunner

from khora_kernel.cli.commands import health, inspect, validate_manifest
from khora_kernel.extensions.core.manifest import KhoraManifestConfig


# Test data with environment-specific configurations
ENV_TEST_PROJECT_TOML = """
[project]
name = "env-integration-test"
version = "0.1.0"
description = "Integration test for environment-specific configurations"

[tool.khora]
project_name = "EnvIntegrationTest"
project_description = "Base project configuration"
python_version = "3.11"

[tool.khora.features]
fastapi = true
docker = true
ci_github_actions = false
kg = false

[tool.khora.paths]
api_dir = "src/api"

[tool.khora.env.dev]
project_description = "Development environment configuration"
python_version = "3.12"

[tool.khora.env.dev.features]
docker = false
kg = true

[tool.khora.env.prod]
project_description = "Production environment configuration"

[tool.khora.env.prod.features]
ci_github_actions = true

[tool.khora.env.prod.paths]
api_dir = "src/api/production"

[tool.khora.env.prod.ports]
http = 80
"""


class TestEnvironmentManifestIntegration:
    """Integration tests for environment-specific manifest layering."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory with necessary project files."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Set up as a Khora project
            project_dir = Path(temp_dir)
            
            # Create pyproject.toml
            with open(project_dir / "pyproject.toml", "w") as f:
                f.write(ENV_TEST_PROJECT_TOML)
            
            # Create minimal directory structure
            (project_dir / "src").mkdir()
            (project_dir / "src" / "api").mkdir(parents=True)
            (project_dir / ".khora").mkdir()
            
            # Create a minimal context.yaml
            context_yaml = {
                "kernel_version": "0.1.0",
                "schema_version": "0.1.0",
                "generated_at": "2025-05-08T00:00:00Z",
                "project": {
                    "name": "EnvIntegrationTest",
                    "description": "Base project configuration",
                    "paths": {"api_dir": "src/api"}
                }
            }
            with open(project_dir / ".khora" / "context.yaml", "w") as f:
                yaml.dump(context_yaml, f)
            
            yield project_dir
        finally:
            shutil.rmtree(temp_dir)

    def test_manifest_config_with_environments(self, temp_project_dir):
        """Test loading manifest config with different environments."""
        # Test base config (no environment)
        base_config = KhoraManifestConfig.from_project_toml(temp_project_dir)
        assert base_config.project_name == "EnvIntegrationTest"
        assert base_config.project_description == "Base project configuration"
        assert base_config.python_version == "3.11"
        assert base_config.features.fastapi is True
        assert base_config.features.docker is True
        assert base_config.features.ci_github_actions is False
        assert base_config.features.kg is False
        assert base_config.ports.http == 8000
        assert base_config.active_environment is None
        
        # Test dev environment
        dev_config = KhoraManifestConfig.from_project_toml_with_env(temp_project_dir, env="dev")
        assert dev_config.project_name == "EnvIntegrationTest"  # Not overridden
        assert dev_config.project_description == "Development environment configuration"  # Overridden
        assert dev_config.python_version == "3.12"  # Overridden
        assert dev_config.features.fastapi is True  # Not overridden
        assert dev_config.features.docker is False  # Overridden
        assert dev_config.features.ci_github_actions is False  # Not overridden
        assert dev_config.features.kg is True  # Overridden
        assert dev_config.ports.http == 8000  # Not overridden
        assert dev_config.active_environment == "dev"
        
        # Test prod environment
        prod_config = KhoraManifestConfig.from_project_toml_with_env(temp_project_dir, env="prod")
        assert prod_config.project_name == "EnvIntegrationTest"  # Not overridden
        assert prod_config.project_description == "Production environment configuration"  # Overridden
        assert prod_config.python_version == "3.11"  # Not overridden
        assert prod_config.features.fastapi is True  # Not overridden
        assert prod_config.features.docker is True  # Not overridden
        assert prod_config.features.ci_github_actions is True  # Overridden
        assert prod_config.features.kg is False  # Not overridden
        assert prod_config.ports.http == 80  # Overridden
        assert prod_config.paths.api_dir == Path("src/api/production")  # Overridden
        assert prod_config.active_environment == "prod"

    def test_cli_commands_with_environment(self, temp_project_dir):
        """Test CLI commands with environment-specific configurations."""
        runner = CliRunner()
        
        # Change to the temp directory so commands work correctly
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_project_dir)
            
            # Test validate-manifest with different environments
            base_result = runner.invoke(validate_manifest, ["--json-output"])
            assert base_result.exit_code == 0
            base_json = yaml.safe_load(base_result.output)
            assert base_json["valid"] is True
            assert base_json["manifest"]["python_version"] == "3.11"
            assert "active_environment" not in base_json
            
            dev_result = runner.invoke(validate_manifest, ["--json-output", "--khora-env", "dev"])
            assert dev_result.exit_code == 0
            dev_json = yaml.safe_load(dev_result.output)
            assert dev_json["valid"] is True
            assert dev_json["manifest"]["python_version"] == "3.12"
            assert dev_json["active_environment"] == "dev"
            assert dev_json["manifest"]["features"]["docker"] is False
            
            prod_result = runner.invoke(validate_manifest, ["--json-output", "--khora-env", "prod"])
            assert prod_result.exit_code == 0
            prod_json = yaml.safe_load(prod_result.output)
            assert prod_json["valid"] is True
            assert prod_json["manifest"]["ports"]["http"] == 80
            assert prod_json["active_environment"] == "prod"
            
            # Test health with environment
            health_result = runner.invoke(health, ["--json-output", "--khora-env", "dev"])
            assert health_result.exit_code == 0
            import json
            health_json = json.loads(health_result.output)
            assert health_json["environment"]["name"] == "dev"
            
            # Test inspect with environment
            inspect_result = runner.invoke(inspect, ["--json-output", "--khora-env", "prod"])
            assert inspect_result.exit_code == 0
            inspect_json = json.loads(inspect_result.output)
            assert inspect_json["environment"] == "prod"
            if "manifest" in inspect_json:
                assert inspect_json["manifest"]["ports"]["http"] == 80
        finally:
            os.chdir(old_cwd)

    def test_nonexistent_environment_fallback(self, temp_project_dir):
        """Test that nonexistent environment falls back to base config."""
        # Load with a nonexistent environment
        config = KhoraManifestConfig.from_project_toml_with_env(temp_project_dir, env="staging")
        
        # Should be identical to base config
        assert config.project_description == "Base project configuration"
        assert config.python_version == "3.11"
        assert config.features.docker is True
        assert config.features.kg is False
        assert config.ports.http == 8000
        assert config.active_environment is None
