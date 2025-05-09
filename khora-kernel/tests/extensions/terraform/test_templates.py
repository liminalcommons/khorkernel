import pytest
from string import Template

from khora_kernel_vnext.extensions.terraform.extension import TerraformExtension


def test_main_tf_template():
    """Test if the main_tf template is correctly substituted"""
    extension = TerraformExtension()
    template_path = "khora_kernel_vnext.extensions.terraform.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    main_template = get_template("main_tf", relative_to=template_path)
    
    # Substitute values
    project_name = "test-project"
    substituted = main_template.substitute(project_name=project_name)
    
    # Check if substitution was done correctly
    assert "${project_name}" not in substituted
    assert project_name in substituted
    assert "resource" in substituted
    assert "module" in substituted


def test_variables_tf_template():
    """Test if the variables_tf template contains necessary variable definitions"""
    extension = TerraformExtension()
    template_path = "khora_kernel_vnext.extensions.terraform.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    vars_template = get_template("variables_tf", relative_to=template_path)
    
    # Substitute values
    project_name = "test-project"
    substituted = vars_template.substitute(project_name=project_name)
    
    # Check for key variable definitions
    assert "variable \"project_name\"" in substituted
    assert "variable \"environment\"" in substituted
    assert "variable \"region\"" in substituted
    assert project_name in substituted


def test_outputs_tf_template():
    """Test if the outputs_tf template contains necessary output definitions"""
    extension = TerraformExtension()
    template_path = "khora_kernel_vnext.extensions.terraform.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    outputs_template = get_template("outputs_tf", relative_to=template_path)
    
    # Substitute values
    substituted = outputs_template.substitute()
    
    # Check for key output definitions
    assert "output \"project_info\"" in substituted
    assert "description" in substituted
    assert "value" in substituted


def test_terraform_tfvars_template():
    """Test if the terraform_tfvars template is correctly substituted"""
    extension = TerraformExtension()
    template_path = "khora_kernel_vnext.extensions.terraform.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    tfvars_template = get_template("terraform_tfvars", relative_to=template_path)
    
    # Substitute values
    project_name = "test-project"
    substituted = tfvars_template.substitute(project_name=project_name)
    
    # Check if substitution was done correctly
    assert "${project_name}" not in substituted
    assert project_name in substituted
    assert "environment" in substituted
    assert "region" in substituted


def test_versions_tf_template():
    """Test if the versions_tf template contains required provider definitions"""
    extension = TerraformExtension()
    template_path = "khora_kernel_vnext.extensions.terraform.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    versions_template = get_template("versions_tf", relative_to=template_path)
    
    # Substitute values
    substituted = versions_template.substitute()
    
    # Check for provider definitions
    assert "terraform {" in substituted
    assert "required_version" in substituted
    assert "required_providers" in substituted
    assert "aws" in substituted
    assert "hashicorp/aws" in substituted


def test_readme_md_template():
    """Test if the readme_md template is correctly substituted"""
    extension = TerraformExtension()
    template_path = "khora_kernel_vnext.extensions.terraform.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    readme_template = get_template("readme_md", relative_to=template_path)
    
    # Substitute values
    project_name = "test-project"
    substituted = readme_template.substitute(project_name=project_name)
    
    # Check if substitution was done correctly
    assert "${project_name}" not in substituted
    assert project_name in substituted
    assert "Infrastructure" in substituted
    assert "Prerequisites" in substituted
    assert "Getting Started" in substituted


def test_env_main_tf_template():
    """Test if the environment main_tf template is correctly substituted"""
    extension = TerraformExtension()
    template_path = "khora_kernel_vnext.extensions.terraform.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    env_main_template = get_template("env_main_tf", relative_to=template_path)
    
    # Substitute values
    project_name = "test-project"
    env_name = "dev"
    substituted = env_main_template.substitute(
        project_name=project_name,
        env_name=env_name
    )
    
    # Check if substitution was done correctly
    assert "${project_name}" not in substituted
    assert "${env_name}" not in substituted
    assert project_name in substituted
    assert env_name in substituted
    assert "module \"main\"" in substituted


def test_env_tfvars_template():
    """Test if the env_tfvars template is correctly substituted"""
    extension = TerraformExtension()
    template_path = "khora_kernel_vnext.extensions.terraform.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    env_tfvars_template = get_template("env_tfvars", relative_to=template_path)
    
    # Substitute values
    project_name = "test-project"
    env_name = "dev"
    substituted = env_tfvars_template.substitute(
        project_name=project_name,
        env_name=env_name
    )
    
    # Check if substitution was done correctly
    assert "${project_name}" not in substituted
    assert "${env_name}" not in substituted
    assert project_name in substituted
    assert env_name in substituted
    assert "project_name = \"test-project\"" in substituted


def test_workflow_template():
    """Test if the GitHub Actions workflow template is correctly substituted"""
    extension = TerraformExtension()
    template_path = "khora_kernel_vnext.extensions.terraform.templates"
    
    # Import the get_template function to access the template
    from pyscaffold.templates import get_template
    
    # Get the template
    workflow_template = get_template("terraform_workflow_yml", relative_to=template_path)
    
    # Substitute values
    project_name = "test-project"
    substituted = workflow_template.substitute(project_name=project_name)
    
    # Check if substitution was done correctly
    assert "${project_name}" not in substituted
    assert project_name in substituted
    assert "terraform-validation" in substituted
    assert "terraform-plan" in substituted
    assert "hashicorp/setup-terraform" in substituted
    assert "tfsec" in substituted
