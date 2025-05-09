"""
Tests for the khora validate-manifest CLI command.
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner

from khora_kernel.cli.commands import validate_manifest

# Test data with multiple environments
TEST_PYPROJECT_CONTENT = """
[project]
name = "validate-test-project"
version = "0.1.0"
description = "Test project for validate-manifest command"

[tool.khora]
project_name = "ValidateTestProject"
project_description = "Base configuration for validation testing"
python_version = "3.11"

[tool.khora.features]
fastapi = true
docker = true

[tool.khora.paths]
api_dir = "src/api"

[tool.khora.env.dev]
project_description = "Development configuration for validation testing"
python_version = "3.12"

[tool.khora.env.dev.features]
docker = false
kg = true

[tool.khora.env.prod]
project_description = "Production configuration for validation testing"

[tool.khora.env.prod.features]
security_gates = true

[tool.khora.env.prod.ports]
http = 80
"""

# Invalid TOML (missing required field)
INVALID_PYPROJECT_CONTENT = """
[project]
name = "invalid-test-project"
version = "0.1.0"

[tool.khora]
# Missing required project_name field
project_description = "This is an invalid configuration"
# Missing required python_version field

[tool.khora.features]
fastapi = true
"""


class TestValidateManifest:
    """Test suite for the validate-manifest command."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for the test project."""
        temp_dir = tempfile.mkdtemp()
        try:
            yield Path(temp_dir)
        finally:
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def valid_pyproject(self, temp_project_dir):
        """Create a valid pyproject.toml file."""
        pyproject_path = temp_project_dir / "pyproject.toml"
        with open(pyproject_path, "w") as f:
            f.write(TEST_PYPROJECT_CONTENT)
        return temp_project_dir

    @pytest.fixture
    def invalid_pyproject(self, temp_project_dir):
        """Create an invalid pyproject.toml file."""
        pyproject_path = temp_project_dir / "pyproject.toml"
        with open(pyproject_path, "w") as f:
            f.write(INVALID_PYPROJECT_CONTENT)
        return temp_project_dir

    def test_validate_manifest_basic(self, valid_pyproject):
        """Test validating a manifest with default options."""
        runner = CliRunner()
        pyproject_path = valid_pyproject / "pyproject.toml"
        
        result = runner.invoke(validate_manifest, ["--pyproject-path", str(pyproject_path)])
        
        assert result.exit_code == 0
        assert "Manifest is valid." in result.output
        assert "Project: ValidateTestProject" in result.output
        assert "Python Version: 3.11" in result.output
        assert "✅ fastapi" in result.output
        assert "✅ docker" in result.output

    def test_validate_manifest_json_output(self, valid_pyproject):
        """Test validating a manifest with JSON output."""
        runner = CliRunner()
        pyproject_path = valid_pyproject / "pyproject.toml"
        
        result = runner.invoke(validate_manifest, [
            "--pyproject-path", str(pyproject_path),
            "--json-output"
        ])
        
        assert result.exit_code == 0
        
        # Parse the JSON output to verify it's valid
        json_result = json.loads(result.output)
        assert json_result["valid"] == True
        assert json_result["manifest"]["project_name"] == "ValidateTestProject"
        assert json_result["manifest"]["python_version"] == "3.11"
        assert json_result["manifest"]["features"]["fastapi"] == True
        assert json_result["manifest"]["features"]["docker"] == True

    def test_validate_manifest_dev_env(self, valid_pyproject):
        """Test validating a manifest with the dev environment."""
        runner = CliRunner()
        pyproject_path = valid_pyproject / "pyproject.toml"
        
        result = runner.invoke(validate_manifest, [
            "--pyproject-path", str(pyproject_path),
            "--khora-env", "dev"
        ])
        
        assert result.exit_code == 0
        assert "Manifest is valid with 'dev' environment" in result.output
        assert "Project: ValidateTestProject" in result.output
        assert "Python Version: 3.12" in result.output  # Overridden in dev
        assert "Active Environment: dev" in result.output
        assert "✅ fastapi" in result.output
        assert "❌ docker" in result.output  # Overridden in dev
        assert "✅ kg" in result.output      # Added in dev

    def test_validate_manifest_prod_env(self, valid_pyproject):
        """Test validating a manifest with the prod environment."""
        runner = CliRunner()
        pyproject_path = valid_pyproject / "pyproject.toml"
        
        result = runner.invoke(validate_manifest, [
            "--pyproject-path", str(pyproject_path),
            "--khora-env", "prod"
        ])
        
        assert result.exit_code == 0
        assert "Manifest is valid with 'prod' environment" in result.output
        assert "Production configuration for validation testing" in result.output
        assert "✅ security_gates" in result.output  # Added in prod

    def test_validate_manifest_json_with_env(self, valid_pyproject):
        """Test validating a manifest with JSON output and environment."""
        runner = CliRunner()
        pyproject_path = valid_pyproject / "pyproject.toml"
        
        result = runner.invoke(validate_manifest, [
            "--pyproject-path", str(pyproject_path),
            "--json-output",
            "--khora-env", "dev"
        ])
        
        assert result.exit_code == 0
        
        # Parse the JSON output
        json_result = json.loads(result.output)
        assert json_result["valid"] == True
        assert json_result["environment"] == "dev"
        assert json_result["active_environment"] == "dev"
        assert json_result["manifest"]["project_name"] == "ValidateTestProject"
        assert json_result["manifest"]["python_version"] == "3.12"  # Overridden in dev
        assert json_result["manifest"]["features"]["fastapi"] == True
        assert json_result["manifest"]["features"]["docker"] == False  # Overridden in dev
        assert json_result["manifest"]["features"]["kg"] == True  # Added in dev

    def test_validate_invalid_manifest(self, invalid_pyproject):
        """Test validating an invalid manifest."""
        runner = CliRunner()
        pyproject_path = invalid_pyproject / "pyproject.toml"
        
        result = runner.invoke(validate_manifest, ["--pyproject-path", str(pyproject_path)])
        
        assert result.exit_code == 1
        assert "Invalid manifest" in result.output

    def test_validate_invalid_manifest_json(self, invalid_pyproject):
        """Test validating an invalid manifest with JSON output."""
        runner = CliRunner()
        pyproject_path = invalid_pyproject / "pyproject.toml"
        
        result = runner.invoke(validate_manifest, [
            "--pyproject-path", str(pyproject_path),
            "--json-output"
        ])
        
        assert result.exit_code == 1
        
        # Parse the JSON output
        json_result = json.loads(result.output)
        assert json_result["valid"] == False
        assert json_result["error_type"] == "manifest_invalid"
        
        # Check that errors list contains at least one error
        assert len(json_result["errors"]) > 0

    def test_validate_nonexistent_env(self, valid_pyproject):
        """Test validating with a non-existent environment."""
        runner = CliRunner()
        pyproject_path = valid_pyproject / "pyproject.toml"
        
        result = runner.invoke(validate_manifest, [
            "--pyproject-path", str(pyproject_path),
            "--khora-env", "nonexistent"
        ])
        
        assert result.exit_code == 0
        # Should fall back to base config
        assert "Python Version: 3.11" in result.output
        assert "✅ docker" in result.output  # In base config
        assert "❌ kg" in result.output      # Not in base config
