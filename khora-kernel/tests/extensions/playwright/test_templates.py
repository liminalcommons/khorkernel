import pytest
from string import Template

from khora_kernel_vnext.extensions.playwright.extension import PlaywrightExtension


def test_playwright_config_template():
    """Test if the playwright_config_py template is correctly substituted"""
    extension = PlaywrightExtension()
    template_path = "khora_kernel_vnext.extensions.playwright.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    config_template = get_template("playwright_config_py", relative_to=template_path)
    
    # Substitute values
    project_name = "test-project"
    substituted = config_template.substitute(project_name=project_name)
    
    # Check if substitution was done correctly
    assert "${project_name}" not in substituted
    assert project_name in substituted
    assert "Playwright configuration" in substituted


def test_conftest_template():
    """Test if the conftest_py template is correctly structured"""
    extension = PlaywrightExtension()
    template_path = "khora_kernel_vnext.extensions.playwright.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    conftest_template = get_template("conftest_py", relative_to=template_path)
    
    # Substitute values
    substituted = conftest_template.substitute()
    
    # Check for key components
    assert "pytest.fixture" in substituted
    assert "playwright" in substituted
    assert "browser" in substituted
    assert "context" in substituted
    assert "page" in substituted


def test_sample_test_template():
    """Test if the sample_test_py template is correctly substituted"""
    extension = PlaywrightExtension()
    template_path = "khora_kernel_vnext.extensions.playwright.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    test_template = get_template("sample_test_py", relative_to=template_path)
    
    # Substitute values
    project_name = "test-project"
    substituted = test_template.substitute(project_name=project_name)
    
    # Check if substitution was done correctly
    assert "${project_name}" not in substituted
    assert project_name in substituted
    assert "test_basic_navigation" in substituted
    assert "page.goto" in substituted


def test_requirements_template():
    """Test if the requirements_txt template contains necessary packages"""
    extension = PlaywrightExtension()
    template_path = "khora_kernel_vnext.extensions.playwright.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    requirements_template = get_template("requirements_txt", relative_to=template_path)
    
    # Substitute values
    substituted = requirements_template.substitute()
    
    # Check for key packages
    assert "playwright" in substituted
    assert "pytest-playwright" in substituted
    assert "pytest" in substituted


def test_workflow_template():
    """Test if the GitHub Actions workflow template is correctly substituted"""
    extension = PlaywrightExtension()
    template_path = "khora_kernel_vnext.extensions.playwright.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    workflow_template = get_template("playwright_workflow_yml", relative_to=template_path)
    
    # Substitute values
    project_name = "test-project"
    python_version = "3.9"
    substituted = workflow_template.substitute(
        project_name=project_name,
        python_version=python_version,
        matrix_python_version="${{ matrix.python-version }}",
        HOME_PATH="$HOME",
        GITHUB_PATH="$GITHUB_PATH"
    )
    
    # Check if substitution was done correctly
    assert "${project_name}" not in substituted
    assert project_name in substituted
    assert python_version in substituted
    assert "playwright install" in substituted
    assert "pytest" in substituted
