"""Integration tests for Phase 4 features."""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
from khora_kernel_vnext.cli.commands import main_cli


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for the test project."""
    temp_dir = tempfile.mkdtemp()
    old_cwd = os.getcwd()
    os.chdir(temp_dir)
    
    # Create a minimal pyproject.toml file
    pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"
description = "A test project for Khora integration tests"

[tool.khora]
features = { documentation = true }

[project.optional-dependencies.dev]
pytest = ">=7.0.0"
"""
    with open("pyproject.toml", "w", encoding="utf-8") as f:
        f.write(pyproject_content)
        
    # Create a basic .khora directory with a minimal context.yaml
    os.makedirs(".khora", exist_ok=True)
    with open(".khora/context.yaml", "w", encoding="utf-8") as f:
        f.write("""
project:
  name: test-project
  version: 0.1.0
  description: A test project for Khora integration tests
features:
  documentation: true
""")
    
    try:
        yield Path(temp_dir)
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(temp_dir)


def test_list_plugins_integration():
    """Test the list-plugins command integration."""
    runner = CliRunner()
    
    with patch('khora_kernel_vnext.cli.commands.find_installed_plugins') as mock_find_local:
        mock_find_local.return_value = [
            {
                'name': 'khora-docs-extension',
                'version': '0.1.0',
                'description': 'Documentation extension for Khora',
                'installed': True
            }
        ]
        
        # Run the command
        result = runner.invoke(main_cli, ['list-plugins'])
        
        # Verify the output
        assert result.exit_code == 0
        assert 'khora-docs-extension' in result.output
        assert '0.1.0' in result.output
        assert 'Documentation extension for Khora' in result.output


def test_docs_extension_integration(temp_project_dir):
    """Test the docs extension integration."""
    from khora_kernel_vnext.extensions.docs.extension import DocsExtension
    
    # Create the extension instance
    extension = DocsExtension()
    
    # Set up options similar to what PyScaffold would provide
    opts = {
        "project": "test-project",
        "description": "A test project for Khora integration tests",
        "khora_features": {"documentation": True},
        "docs_type": "sphinx"
    }
    extension.options = opts
    
    # Create a minimal set of actions
    actions = [
        ("ensure", {"path": "src"}),
        ("write_manifest", {}),
        ("finish", {})
    ]
    
    # Apply the extension
    result_actions = extension.activate(actions)
    
    # Verify that new actions were added
    assert len(result_actions) > len(actions)
    
    # Find all the paths that would be created
    paths = []
    for action, opts in result_actions:
        if action in ["create", "ensure"] and "path" in opts:
            paths.append(opts["path"])
    
    # Check that we have the expected Sphinx docs files
    assert "docs/conf.py" in paths
    assert "docs/index.rst" in paths
    assert "docs/Makefile" in paths
    assert "docs/_static" in paths
    assert "docs/_templates" in paths


def test_docs_extension_mkdocs_integration(temp_project_dir):
    """Test the docs extension with MkDocs."""
    from khora_kernel_vnext.extensions.docs.extension import DocsExtension
    
    # Create the extension instance
    extension = DocsExtension()
    
    # Set up options with MkDocs
    opts = {
        "project": "test-project",
        "description": "A test project for Khora integration tests",
        "khora_features": {"documentation": True},
        "docs_type": "mkdocs"
    }
    extension.options = opts
    
    # Create a minimal set of actions
    actions = [
        ("ensure", {"path": "src"}),
        ("write_manifest", {}),
        ("finish", {})
    ]
    
    # Apply the extension
    result_actions = extension.activate(actions)
    
    # Verify that new actions were added
    assert len(result_actions) > len(actions)
    
    # Find all the paths that would be created
    paths = []
    for action, opts in result_actions:
        if action in ["create", "ensure"] and "path" in opts:
            paths.append(opts["path"])
    
    # Check that we have the expected MkDocs files
    assert "mkdocs.yml" in paths
    assert "docs/index.md" in paths
    assert "docs/api" in paths
    assert "docs/api/index.md" in paths


def test_docs_extension_updates_dependencies():
    """Test that the docs extension updates dependencies correctly."""
    from khora_kernel_vnext.extensions.docs.extension import DocsExtension
    
    extension = DocsExtension()
    
    # Test with Sphinx
    action, options = extension._update_dependencies_action("sphinx")
    assert options["target"] == "pyproject.toml"
    
    # Create a mock pyproject.toml content
    test_content = """
[project]
name = "test-project"
version = "0.1.0"

[project.optional-dependencies.dev]
pytest = ">=7.0.0"

[other]
something = "else"
"""
    
    # Apply the updater function
    updater_func = options["modification"]
    updated_content = updater_func(test_content, {})
    
    # Check that dependencies were added
    assert "sphinx" in updated_content
    assert "sphinx-rtd-theme" in updated_content
    assert "myst-parser" in updated_content
    
    # Test with MkDocs
    action, options = extension._update_dependencies_action("mkdocs")
    updater_func = options["modification"]
    updated_content = updater_func(test_content, {})
    
    # Check that dependencies were added
    assert "mkdocs" in updated_content
    assert "mkdocs-material" in updated_content
    assert "mkdocstrings[python]" in updated_content
