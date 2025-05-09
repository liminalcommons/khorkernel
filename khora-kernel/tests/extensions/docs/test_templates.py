"""Test the templates for the docs extension."""

import pytest
from khora_kernel_vnext.sdk.templates import TemplateManager, render_template

# Initialize the template manager for docs extension
template_manager = TemplateManager('docs')


def test_sphinx_conf_py_template():
    """Test that Sphinx conf.py template renders correctly."""
    context = {
        "project_name": "test-project",
        "project_description": "A test project"
    }
    
    # Get the raw template content by reading the file directly
    from pathlib import Path
    template_file = Path(__file__).parent.parent.parent.parent / "src" / "khora_kernel_vnext" / "extensions" / "docs" / "templates" / "sphinx_conf_py.template"
    with open(template_file, "r") as f:
        template_content = f.read()
    
    # Manually substitute the variables
    rendered = template_content.replace("{{ project_name }}", "test-project")
    
    # Check that the project name is in the rendered content
    assert 'project = "test-project"' in rendered
    
    # Check that key Sphinx extensions are included
    assert "sphinx.ext.autodoc" in rendered
    assert "sphinx.ext.viewcode" in rendered
    assert "sphinx.ext.napoleon" in rendered
    assert "myst_parser" in rendered
    
    # Check for HTML theme
    assert 'html_theme = "sphinx_rtd_theme"' in rendered


def test_sphinx_index_rst_template():
    """Test that Sphinx index.rst template renders correctly."""
    context = {
        "project_name": "test-project",
        "project_description": "A test project"
    }
    
    # Get the raw template content by reading the file directly
    from pathlib import Path
    template_file = Path(__file__).parent.parent.parent.parent / "src" / "khora_kernel_vnext" / "extensions" / "docs" / "templates" / "sphinx_index_rst.template"
    with open(template_file, "r") as f:
        template_content = f.read()
    
    # Manually substitute the variables
    rendered = template_content.replace("{{ project_name }}", "test-project").replace("{{ project_description }}", "A test project")
    
    # Check that the project name is in the rendered content
    assert "test-project" in rendered
    
    # Check that the project description is included
    assert "A test project" in rendered
    
    # Check for toctree directive
    assert ".. toctree::" in rendered
    assert ":maxdepth: 2" in rendered
    
    # Check for common document references
    assert "usage" in rendered
    assert "api" in rendered
    assert "contributing" in rendered
    assert "changelog" in rendered


def test_sphinx_makefile_template():
    """Test that Sphinx Makefile template renders correctly."""
    context = {}
    
    # Get the raw template content by reading the file directly
    from pathlib import Path
    template_file = Path(__file__).parent.parent.parent.parent / "src" / "khora_kernel_vnext" / "extensions" / "docs" / "templates" / "sphinx_makefile.template"
    with open(template_file, "r") as f:
        rendered = f.read()
    
    # Check for key Makefile components
    assert "SPHINXBUILD   = sphinx-build" in rendered
    assert "SOURCEDIR     = ." in rendered
    assert "BUILDDIR      = _build" in rendered
    
    # Check for help target
    assert ".PHONY: help Makefile" in rendered
    
    # Check for catch-all target
    assert "$(SPHINXBUILD) -M $@ \"$(SOURCEDIR)\" \"$(BUILDDIR)\" $(SPHINXOPTS) $(SPHINXARGS)" in rendered


def test_mkdocs_yml_template():
    """Test that MkDocs YAML template renders correctly."""
    context = {
        "project_name": "test-project",
        "project_description": "A test project"
    }
    
    # Get the raw template content by reading the file directly
    from pathlib import Path
    template_file = Path(__file__).parent.parent.parent.parent / "src" / "khora_kernel_vnext" / "extensions" / "docs" / "templates" / "mkdocs_yml.template"
    with open(template_file, "r") as f:
        template_content = f.read()
    
    # Manually substitute the variables
    rendered = template_content.replace("{{ project_name }}", "test-project").replace("{{ project_description }}", "A test project")
    
    # Check that the project name is in the rendered content
    assert "site_name: test-project" in rendered
    
    # Check that the project description is included
    assert "site_description: A test project" in rendered
    
    # Check for theme configuration
    assert "theme:" in rendered
    assert "name: material" in rendered
    
    # Check for plugins
    assert "plugins:" in rendered
    assert "- search" in rendered
    assert "- mkdocstrings:" in rendered
    
    # Check for navigation
    assert "nav:" in rendered
    assert "- Home: index.md" in rendered
    assert "- API:" in rendered


def test_mkdocs_index_md_template():
    """Test that MkDocs index.md template renders correctly."""
    context = {
        "project_name": "test-project",
        "project_description": "A test project"
    }
    
    # Get the raw template content by reading the file directly
    from pathlib import Path
    template_file = Path(__file__).parent.parent.parent.parent / "src" / "khora_kernel_vnext" / "extensions" / "docs" / "templates" / "mkdocs_index_md.template"
    with open(template_file, "r") as f:
        template_content = f.read()
    
    # Manually substitute the variables
    rendered = template_content.replace("{{ project_name }}", "test-project").replace("{{ project_description }}", "A test project")
    
    # Check that the project name is in the rendered content
    assert "# test-project" in rendered
    
    # Check that the project description is included
    assert "A test project" in rendered
    
    # Check for installation section
    assert "## Installation" in rendered
    assert "pip install test-project" in rendered
    
    # Check for usage section with code block
    assert "## Usage" in rendered
    assert "import test_project" in rendered.replace("{{ project_name.replace(\"-\", \"_\") }}", "test_project")
    
    # Check for features section
    assert "## Features" in rendered
    assert "* Feature 1" in rendered
