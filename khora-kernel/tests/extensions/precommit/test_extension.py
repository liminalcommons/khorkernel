"""
Tests for the Pre-commit extension.
"""
import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

from pyscaffold.actions import ScaffoldOpts, Structure
from pyscaffold.operations import no_overwrite

from khora_kernel_vnext.extensions.precommit.extension import (
    PrecommitExtension, 
    add_precommit_config
)
from khora_kernel_vnext.extensions.core.manifest import (
    KhoraManifestConfig,
    KhoraFeaturesConfig,
)


@pytest.fixture
def precommit_extension_instance():
    """Returns a PrecommitExtension instance for testing."""
    return PrecommitExtension(name="khora_precommit")


@pytest.fixture
def base_khora_config():
    """Create a basic KhoraManifestConfig with precommit enabled."""
    return KhoraManifestConfig(
        project_name="TestProject",
        project_description="Test project for precommit extension",
        python_version="3.11",
        features=KhoraFeaturesConfig(precommit=True)
    )


def test_augment_cli(precommit_extension_instance):
    """Test that the extension properly adds CLI options."""
    parser = MagicMock()
    result = precommit_extension_instance.augment_cli(parser)
    
    # Check that add_argument was called
    parser.add_argument.assert_called_once()
    
    # Should return self
    assert result is precommit_extension_instance


def test_activate_not_enabled(precommit_extension_instance):
    """Test that the extension doesn't modify actions when not enabled."""
    precommit_extension_instance.opts = {"khora_precommit": False}
    actions = ["action1", "action2"]
    
    result = precommit_extension_instance.activate(actions)
    
    # Should return original actions unchanged
    assert result == actions


def test_activate_enabled(precommit_extension_instance):
    """Test that the extension adds an action when enabled."""
    precommit_extension_instance.opts = {"khora_precommit": True}
    actions = [MagicMock(__name__="action1"), MagicMock(__name__="define_structure")]
    
    with patch("khora_kernel_vnext.extensions.precommit.extension.add_precommit_config") as mock_action:
        result = precommit_extension_instance.activate(actions)
        
        # Should have one more action
        assert len(result) == 3
        
        # New action should be our mock
        assert result[2] is mock_action


def test_add_precommit_config_no_khora_config():
    """Test handling when Khora config is missing."""
    struct = {}
    opts = {}  # No khora_config
    
    with patch("khora_kernel_vnext.extensions.precommit.extension.logger") as mock_logger:
        result_struct, result_opts = add_precommit_config(struct, opts)
        
        # Should log warning
        mock_logger.warning.assert_called_once()
        
        # Should return unchanged struct and opts
        assert result_struct == struct
        assert result_opts == opts


def test_add_precommit_config_precommit_disabled(base_khora_config):
    """Test handling when precommit is disabled."""
    struct = {}
    base_khora_config.features.precommit = False
    opts = {"khora_config": base_khora_config}
    
    with patch("khora_kernel_vnext.extensions.precommit.extension.logger") as mock_logger:
        result_struct, result_opts = add_precommit_config(struct, opts)
        
        # Should log info
        mock_logger.info.assert_called_once()
        
        # Should return unchanged struct and opts
        assert result_struct == struct
        assert result_opts == opts


def test_add_precommit_config_basic(base_khora_config):
    """Test generating basic pre-commit config without optional features."""
    struct = {}
    opts = {"khora_config": base_khora_config, "project_name": "test_project"}
    
    result_struct, result_opts = add_precommit_config(struct, opts)
    
    # Should have added .pre-commit-config.yaml to struct
    assert ".pre-commit-config.yaml" in result_struct
    
    # Get the YAML content and operation
    yaml_content, operation = result_struct[".pre-commit-config.yaml"]
    
    # Check that operation is no_overwrite
    assert operation.__name__ == "_no_overwrite"
    
    # Parse YAML content
    config = yaml.safe_load(yaml_content)
    
    # Check structure
    assert "repos" in config
    assert len(config["repos"]) == 2  # Only standard hooks, no KG or security
    
    # Check for standard hooks
    assert any(repo["repo"].endswith("ruff-pre-commit") for repo in config["repos"])
    assert any(repo["repo"].endswith("pre-commit-hooks") for repo in config["repos"])
    
    # Should NOT have KG or security hooks
    assert not any(hook.get("id") == "khora-knowledge-graph" for repo in config["repos"] for hook in repo.get("hooks", []))
    assert not any(repo["repo"].endswith("bandit") for repo in config["repos"])


def test_add_precommit_config_with_kg(base_khora_config):
    """Test generating pre-commit config with KG feature enabled."""
    struct = {}
    base_khora_config.features.kg = True
    opts = {"khora_config": base_khora_config, "project_name": "test_project"}
    
    result_struct, _ = add_precommit_config(struct, opts)
    
    # Get the YAML content
    yaml_content, _ = result_struct[".pre-commit-config.yaml"]
    config = yaml.safe_load(yaml_content)
    
    # Should have more than 2 repos (standard + local for KG)
    assert len(config["repos"]) > 2
    
    # Check for KG hook
    found_kg_hook = False
    for repo in config["repos"]:
        if repo.get("repo") == "local":
            for hook in repo.get("hooks", []):
                if hook.get("id") == "khora-knowledge-graph":
                    found_kg_hook = True
                    # Check hook configuration
                    assert "python" in hook["entry"]
                    assert "kg_precommit" in hook["entry"]
                    assert hook["files"].endswith("md$")
                    assert hook["pass_filenames"] is True
    
    assert found_kg_hook, "KG hook not found in pre-commit config"


def test_add_precommit_config_with_security(base_khora_config):
    """Test generating pre-commit config with security gates enabled."""
    struct = {}
    base_khora_config.features.security_gates = True
    opts = {"khora_config": base_khora_config, "project_name": "test_project"}
    
    result_struct, _ = add_precommit_config(struct, opts)
    
    # Get the YAML content
    yaml_content, _ = result_struct[".pre-commit-config.yaml"]
    config = yaml.safe_load(yaml_content)
    
    # Should have more than 2 repos (standard + security)
    assert len(config["repos"]) > 2
    
    # Check for security hooks
    found_bandit = False
    found_trufflehog = False
    
    for repo in config["repos"]:
        if repo.get("repo", "").endswith("bandit"):
            found_bandit = True
        if repo.get("repo", "").endswith("trufflehog"):
            found_trufflehog = True
    
    assert found_bandit, "Bandit hook not found in pre-commit config"
    assert found_trufflehog, "TruffleHog hook not found in pre-commit config"


def test_add_precommit_config_all_features(base_khora_config):
    """Test generating pre-commit config with all features enabled."""
    struct = {}
    base_khora_config.features.kg = True
    base_khora_config.features.security_gates = True
    opts = {"khora_config": base_khora_config, "project_name": "test_project"}
    
    result_struct, _ = add_precommit_config(struct, opts)
    
    # Get the YAML content
    yaml_content, _ = result_struct[".pre-commit-config.yaml"]
    config = yaml.safe_load(yaml_content)
    
    # Should have more than 3 repos (standard + security + local for KG)
    assert len(config["repos"]) > 3
    
    # Check for KG hook
    found_kg_hook = False
    for repo in config["repos"]:
        if repo.get("repo") == "local":
            for hook in repo.get("hooks", []):
                if hook.get("id") == "khora-knowledge-graph":
                    found_kg_hook = True
    
    assert found_kg_hook, "KG hook not found in pre-commit config"
    
    # Check for security hooks
    found_bandit = False
    found_trufflehog = False
    
    for repo in config["repos"]:
        if repo.get("repo", "").endswith("bandit"):
            found_bandit = True
        if repo.get("repo", "").endswith("trufflehog"):
            found_trufflehog = True
    
    assert found_bandit, "Bandit hook not found in pre-commit config"
    assert found_trufflehog, "TruffleHog hook not found in pre-commit config"


def test_yaml_dump_error():
    """Test error handling when YAML serialization fails."""
    struct = {}
    opts = {"khora_config": MagicMock(features=MagicMock(precommit=True))}
    
    with patch("khora_kernel_vnext.extensions.precommit.extension.yaml.dump", side_effect=Exception("YAML error")):
        with patch("khora_kernel_vnext.extensions.precommit.extension.logger") as mock_logger:
            result_struct, _ = add_precommit_config(struct, opts)
            
            # Should log error
            mock_logger.error.assert_called_once()
            
            # Should still add file with error comment
            assert ".pre-commit-config.yaml" in result_struct
            yaml_content, _ = result_struct[".pre-commit-config.yaml"]
            assert yaml_content.startswith("# Error generating pre-commit config")
