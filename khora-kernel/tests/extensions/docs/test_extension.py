"""Test the docs extension."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from khora_kernel_vnext.extensions.docs.extension import DocsExtension


def test_docs_extension_init():
    """Test docs extension initialization."""
    extension = DocsExtension()
    assert extension is not None


def test_augment_cli():
    """Test that the CLI is properly augmented."""
    extension = DocsExtension()
    parser = MagicMock()
    
    # Call the method
    result = extension.augment_cli(parser)
    
    # Check that add_argument was called with the right parameters
    parser.add_argument.assert_called_once()
    args, kwargs = parser.add_argument.call_args
    assert args[0] == "--docs-type"
    assert kwargs["dest"] == "docs_type"
    assert kwargs["choices"] == ["sphinx", "mkdocs"]
    assert kwargs["default"] == "sphinx"
    
    # Check that the parser is returned
    assert result == parser


def test_docs_extension_not_enabled():
    """Test that the extension does nothing if docs feature is not enabled."""
    extension = DocsExtension()
    extension.options = {"khora_features": {}}  # No 'documentation' feature
    
    actions = [("action1", {}), ("action2", {})]
    result = extension.activate(actions)
    
    # Should return the same actions without modification
    assert result == actions


def test_docs_extension_enabled_sphinx():
    """Test that the extension adds Sphinx docs actions when enabled."""
    extension = DocsExtension()
    extension.options = {
        "khora_features": {"documentation": True},
        "docs_type": "sphinx",
        "project": "test-project",
        "description": "A test project"
    }
    
    actions = [
        ("action1", {}),
        ("write_manifest", {}),
        ("action2", {})
    ]
    
    result = extension.activate(actions)
    
    # Should add doc actions before 'write_manifest'
    assert len(result) > len(actions)
    
    # Find the write_manifest index in the result
    write_manifest_index = next(i for i, (action, _) in enumerate(result) if action == "write_manifest")
    
    # Check for doc-related actions before write_manifest
    doc_actions = result[:write_manifest_index]
    
    # Verify we have at least one doc action and they're Sphinx-related
    assert len(doc_actions) > 0
    
    # Check for Sphinx-specific actions (e.g., conf.py, index.rst)
    sphinx_paths = [opt.get("path") for _, opt in doc_actions if isinstance(opt, dict) and "path" in opt]
    assert any("conf.py" in path for path in sphinx_paths if path)
    assert any("index.rst" in path for path in sphinx_paths if path)


def test_docs_extension_enabled_mkdocs():
    """Test that the extension adds MkDocs docs actions when enabled."""
    extension = DocsExtension()
    extension.options = {
        "khora_features": {"documentation": True},
        "docs_type": "mkdocs",
        "project": "test-project",
        "description": "A test project"
    }
    
    actions = [
        ("action1", {}),
        ("write_manifest", {}),
        ("action2", {})
    ]
    
    result = extension.activate(actions)
    
    # Should add doc actions before 'write_manifest'
    assert len(result) > len(actions)
    
    # Find the write_manifest index in the result
    write_manifest_index = next(i for i, (action, _) in enumerate(result) if action == "write_manifest")
    
    # Check for doc-related actions before write_manifest
    doc_actions = result[:write_manifest_index]
    
    # Verify we have at least one doc action and they're MkDocs-related
    assert len(doc_actions) > 0
    
    # Check for MkDocs-specific actions (e.g., mkdocs.yml, index.md)
    mkdocs_paths = [opt.get("path") for _, opt in doc_actions if isinstance(opt, dict) and "path" in opt]
    assert any("mkdocs.yml" in path for path in mkdocs_paths if path)
    assert any("index.md" in path for path in mkdocs_paths if path)


def test_docs_type_from_options():
    """Test getting docs type from options."""
    extension = DocsExtension()
    
    # Test default
    opts = {}
    assert extension._get_docs_type(opts) == "sphinx"
    
    # Test explicit setting
    opts = {"docs_type": "mkdocs"}
    assert extension._get_docs_type(opts) == "mkdocs"


def test_update_dependencies_action():
    """Test the update dependencies action."""
    extension = DocsExtension()
    
    # Test Sphinx dependencies
    action, options = extension._update_dependencies_action("sphinx")
    assert action == "custom_action"
    assert options["action_type"] == "modify"
    assert options["target"] == "pyproject.toml"
    
    # Test the updater function with a mock content
    mock_content = "[project.optional-dependencies.dev]\ndeps = []\n[other.section]"
    updated = options["modification"](mock_content, {})
    assert "sphinx" in updated
    assert "sphinx-rtd-theme" in updated
    assert "myst-parser" in updated
    
    # Test MkDocs dependencies
    action, options = extension._update_dependencies_action("mkdocs")
    mock_content = "[project.optional-dependencies.dev]\ndeps = []\n[other.section]"
    updated = options["modification"](mock_content, {})
    assert "mkdocs" in updated
    assert "mkdocs-material" in updated
    assert "mkdocstrings[python]" in updated


def test_sphinx_structure_generation():
    """Test Sphinx structure generation."""
    extension = DocsExtension()
    opts = {}
    project_name = "test-project"
    project_description = "A test project"
    
    actions = extension._generate_sphinx_structure(opts, project_name, project_description)
    
    # Verify the number and types of actions
    assert len(actions) >= 5  # At least 5 actions for Sphinx docs
    
    # Check for common Sphinx files
    paths = [opt.get("path") for _, opt in actions if isinstance(opt, dict) and "path" in opt]
    assert "docs/conf.py" in paths
    assert "docs/index.rst" in paths
    assert "docs/Makefile" in paths
    assert "docs/_static" in paths
    assert "docs/_templates" in paths


def test_mkdocs_structure_generation():
    """Test MkDocs structure generation."""
    extension = DocsExtension()
    opts = {}
    project_name = "test-project"
    project_description = "A test project"
    
    actions = extension._generate_mkdocs_structure(opts, project_name, project_description)
    
    # Verify the number and types of actions
    assert len(actions) >= 4  # At least 4 actions for MkDocs docs
    
    # Check for common MkDocs files
    paths = [opt.get("path") for _, opt in actions if isinstance(opt, dict) and "path" in opt]
    assert "mkdocs.yml" in paths
    assert "docs/index.md" in paths
    assert "docs/api" in paths
    assert "docs/api/index.md" in paths
