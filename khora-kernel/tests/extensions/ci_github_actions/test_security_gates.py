"""
Tests for the CI GitHub Actions extension's security gates integration.
"""
import pytest
import yaml
from pathlib import Path

from khora_kernel_vnext.extensions.core.manifest import (
    KhoraManifestConfig,
    KhoraFeaturesConfig,
)
from khora_kernel_vnext.extensions.ci_github_actions.extension import add_ci_workflow_file
from pyscaffold.actions import ScaffoldOpts, Structure


@pytest.fixture
def base_khora_config():
    """Create a base Khora config with CI GitHub Actions enabled."""
    return KhoraManifestConfig(
        project_name="test_project",
        project_description="Test project for CI GitHub Actions extension",
        python_version="3.11",
        features=KhoraFeaturesConfig(ci_github_actions=True)
    )


@pytest.fixture
def mock_opts(base_khora_config):
    """Create a mock opts dictionary for testing."""
    return {
        "project_name": "test_project",
        "khora_config": base_khora_config,
    }


def test_ci_workflow_with_security_gates(mock_opts, base_khora_config):
    """Test that CI workflow includes security gates steps when security_gates=True."""
    # Enable security gates
    base_khora_config.features.security_gates = True
    mock_opts["khora_config"] = base_khora_config
    
    # Initial structure with empty .github directory
    struct = {".github": {}}
    
    result_struct, _ = add_ci_workflow_file(struct, mock_opts)
    
    # Verify the structure contains the workflow file
    assert ".github" in result_struct
    assert "workflows" in result_struct[".github"]
    assert "ci.yml" in result_struct[".github"]["workflows"]
    
    # Get the workflow content
    workflow_content = result_struct[".github"]["workflows"]["ci.yml"][0]
    
    # Check that security gates are included
    assert "Security scanning with pip-audit" in workflow_content
    assert "Security scanning with Bandit" in workflow_content
    assert "Secret scanning with TruffleHog" in workflow_content
    assert "uv pip install pip-audit" in workflow_content
    assert "uv pip install bandit" in workflow_content
    assert "pip install trufflehog" in workflow_content


def test_ci_workflow_without_security_gates(mock_opts, base_khora_config):
    """Test that CI workflow doesn't include security gates when security_gates=False."""
    # Ensure security gates are disabled (default)
    base_khora_config.features.security_gates = False
    mock_opts["khora_config"] = base_khora_config
    
    # Initial structure with empty .github directory
    struct = {".github": {}}
    
    result_struct, _ = add_ci_workflow_file(struct, mock_opts)
    
    # Get the workflow content
    workflow_content = result_struct[".github"]["workflows"]["ci.yml"][0]
    
    # Check that security gates are NOT included
    assert "Security scanning with pip-audit" not in workflow_content
    assert "Security scanning with Bandit" not in workflow_content
    assert "Secret scanning with TruffleHog" not in workflow_content
    assert "uv pip install pip-audit" not in workflow_content
    assert "uv pip install bandit" not in workflow_content
    assert "pip install trufflehog" not in workflow_content


def test_ci_workflow_creates_directories(mock_opts, base_khora_config):
    """Test that the CI workflow file creates the necessary directory structure."""
    # Start with an empty structure
    struct = {}
    
    result_struct, _ = add_ci_workflow_file(struct, mock_opts)
    
    # Verify the directory structure was created
    assert ".github" in result_struct
    assert isinstance(result_struct[".github"], dict)
    assert "workflows" in result_struct[".github"]
    assert isinstance(result_struct[".github"]["workflows"], dict)
    assert "ci.yml" in result_struct[".github"]["workflows"]


def test_ci_workflow_handles_existing_nondict_github_dir(mock_opts, base_khora_config):
    """Test handling when .github exists but is not a directory."""
    # Create a structure where .github exists but is a file
    struct = {".github": "some content"}
    
    result_struct, _ = add_ci_workflow_file(struct, mock_opts)
    
    # Verify .github was converted to a dictionary
    assert isinstance(result_struct[".github"], dict)
    assert "workflows" in result_struct[".github"]
    assert "ci.yml" in result_struct[".github"]["workflows"]


def test_ci_workflow_uses_python_version(mock_opts, base_khora_config):
    """Test that the CI workflow uses the configured Python version."""
    # Set a specific Python version
    base_khora_config.python_version = "3.12"
    mock_opts["khora_config"] = base_khora_config
    
    struct = {}
    result_struct, _ = add_ci_workflow_file(struct, mock_opts)
    
    # Get the workflow content
    workflow_content = result_struct[".github"]["workflows"]["ci.yml"][0]
    
    # Check that the Python version is included
    assert "3.12" in workflow_content


def test_ci_workflow_skips_when_feature_disabled(mock_opts, base_khora_config):
    """Test that no CI workflow is generated when ci_github_actions is disabled."""
    # Disable CI GitHub Actions
    base_khora_config.features.ci_github_actions = False
    mock_opts["khora_config"] = base_khora_config
    
    struct = {}
    result_struct, _ = add_ci_workflow_file(struct, mock_opts)
    
    # Structure should be unchanged
    assert result_struct == struct


def test_ci_workflow_skips_when_no_khora_config(mock_opts):
    """Test that no CI workflow is generated when khora_config is missing."""
    # Remove khora_config from opts
    mock_opts.pop("khora_config")
    
    struct = {}
    result_struct, _ = add_ci_workflow_file(struct, mock_opts)
    
    # Structure should be unchanged
    assert result_struct == struct
