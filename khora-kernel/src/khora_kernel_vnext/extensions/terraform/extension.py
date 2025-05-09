import argparse
import logging
from pathlib import Path

from pyscaffold.actions import Action, ActionParams, ScaffoldOpts, Structure
from pyscaffold.extensions import Extension
from pyscaffold.operations import no_overwrite
from pyscaffold.templates import get_template

_logger = logging.getLogger(__name__)

class TerraformExtension(Extension):
    """Generates scaffolding for Infrastructure as Code with Terraform."""

    name = "khora_terraform"  # kebab-case for the CLI flag

    def augment_cli(self, parser: argparse.ArgumentParser):
        """Add a CLI option for this extension"""
        parser.add_argument(
            self.flag, # self.flag is derived from self.name
            dest=self.name,
            action="store_true",
            default=False,
            help="Add Terraform IaC scaffolding to the project",
        )
        return self

    def activate(self, actions: list[Action]) -> list[Action]:
        """Activate extension rules."""
        actions = self.register(actions, add_terraform_scaffolding, after="define_structure")
        return actions


def add_terraform_scaffolding(
    struct: Structure, opts: ScaffoldOpts
) -> ActionParams:
    """Add the Terraform IaC scaffolding to the project structure.

    Args:
        struct: project representation as (possibly) nested :obj:`dict`.
        opts: given options.

    Returns:
        Project structure and options
    """
    # Get the Pydantic model from opts
    khora_config = opts.get("khora_config")
    
    if not khora_config:
        _logger.warning("Khora config not found in opts. Skipping Terraform scaffolding generation.")
        return struct, opts
        
    # Check if the Terraform feature is enabled
    if not getattr(khora_config.features, "terraform", False):
        _logger.info("Khora Terraform feature not enabled. Skipping Terraform scaffolding generation.")
        return struct, opts

    # Get the project name from khora_config or fall back to opts['name']
    project_name = getattr(khora_config, "project_name", None)
    if not project_name:
        project_name = opts.get("name", "khora-project")  # PyScaffold sets 'name', but as fallback use a default
        _logger.info(f"Using project name from PyScaffold: {project_name}")
    
    # Create infra/terraform directory structure if it doesn't exist
    infra_dir = struct.setdefault("infra", {})
    if not isinstance(infra_dir, dict): # If infra was a file, overwrite with dict
        infra_dir = {}
        struct["infra"] = infra_dir
        
    terraform_dir = infra_dir.setdefault("terraform", {})
    if not isinstance(terraform_dir, dict): # If terraform was a file, overwrite
        terraform_dir = {}
        infra_dir["terraform"] = terraform_dir

    # Create the necessary files for Terraform

    # Root terraform files
    # main.tf
    main_tf_template = get_template("main_tf", relative_to="khora_kernel_vnext.extensions.terraform.templates")
    main_tf_content = main_tf_template.substitute(
        project_name=project_name
    )
    terraform_dir["main.tf"] = (main_tf_content, no_overwrite())
    
    # variables.tf
    variables_tf_template = get_template("variables_tf", relative_to="khora_kernel_vnext.extensions.terraform.templates")
    variables_tf_content = variables_tf_template.substitute(
        project_name=project_name
    )
    terraform_dir["variables.tf"] = (variables_tf_content, no_overwrite())
    
    # outputs.tf
    outputs_tf_template = get_template("outputs_tf", relative_to="khora_kernel_vnext.extensions.terraform.templates")
    outputs_tf_content = outputs_tf_template.substitute()
    terraform_dir["outputs.tf"] = (outputs_tf_content, no_overwrite())
    
    # terraform.tfvars
    tfvars_template = get_template("terraform_tfvars", relative_to="khora_kernel_vnext.extensions.terraform.templates")
    tfvars_content = tfvars_template.substitute(
        project_name=project_name
    )
    terraform_dir["terraform.tfvars"] = (tfvars_content, no_overwrite())
    
    # versions.tf
    versions_tf_template = get_template("versions_tf", relative_to="khora_kernel_vnext.extensions.terraform.templates")
    versions_tf_content = versions_tf_template.substitute()
    terraform_dir["versions.tf"] = (versions_tf_content, no_overwrite())
    
    # README.md
    readme_template = get_template("readme_md", relative_to="khora_kernel_vnext.extensions.terraform.templates")
    readme_content = readme_template.substitute(
        project_name=project_name
    )
    terraform_dir["README.md"] = (readme_content, no_overwrite())
    
    # Create modules directory
    modules_dir = terraform_dir.setdefault("modules", {})
    if not isinstance(modules_dir, dict):
        modules_dir = {}
        terraform_dir["modules"] = modules_dir
        
    # Add .gitkeep to modules directory to ensure it's committed
    modules_dir[".gitkeep"] = ("# This file ensures the directory is not empty in git", no_overwrite())
    
    # Create environments directory structure
    envs_dir = terraform_dir.setdefault("environments", {})
    if not isinstance(envs_dir, dict):
        envs_dir = {}
        terraform_dir["environments"] = envs_dir
    
    # Create dev environment
    dev_dir = envs_dir.setdefault("dev", {})
    if not isinstance(dev_dir, dict):
        dev_dir = {}
        envs_dir["dev"] = dev_dir
    
    # Create dev environment files
    dev_main_template = get_template("env_main_tf", relative_to="khora_kernel_vnext.extensions.terraform.templates")
    dev_main_content = dev_main_template.substitute(
        project_name=project_name,
        env_name="dev"
    )
    dev_dir["main.tf"] = (dev_main_content, no_overwrite())
    
    dev_tfvars_template = get_template("env_tfvars", relative_to="khora_kernel_vnext.extensions.terraform.templates")
    dev_tfvars_content = dev_tfvars_template.substitute(
        project_name=project_name,
        env_name="dev"
    )
    dev_dir["terraform.tfvars"] = (dev_tfvars_content, no_overwrite())
    
    # Create prod environment
    prod_dir = envs_dir.setdefault("prod", {})
    if not isinstance(prod_dir, dict):
        prod_dir = {}
        envs_dir["prod"] = prod_dir
    
    # Create prod environment files
    prod_main_template = get_template("env_main_tf", relative_to="khora_kernel_vnext.extensions.terraform.templates")
    prod_main_content = prod_main_template.substitute(
        project_name=project_name,
        env_name="prod"
    )
    prod_dir["main.tf"] = (prod_main_content, no_overwrite())
    
    prod_tfvars_template = get_template("env_tfvars", relative_to="khora_kernel_vnext.extensions.terraform.templates")
    prod_tfvars_content = prod_tfvars_template.substitute(
        project_name=project_name,
        env_name="prod"
    )
    prod_dir["terraform.tfvars"] = (prod_tfvars_content, no_overwrite())
    
    # Add GitHub Actions workflow for Terraform if CI is enabled
    if getattr(khora_config.features, "ci_github_actions", False):
        # Ensure .github/workflows directory exists in the structure
        github_dir = struct.setdefault(".github", {})
        if not isinstance(github_dir, dict): # If .github was a file, overwrite with dict
            github_dir = {}
            struct[".github"] = github_dir
            
        workflows_dir = github_dir.setdefault("workflows", {})
        if not isinstance(workflows_dir, dict): # If workflows was a file, overwrite
            workflows_dir = {}
            github_dir["workflows"] = workflows_dir
        
        # Add terraform.yml workflow
        terraform_workflow_template = get_template("terraform_workflow_yml", relative_to="khora_kernel_vnext.extensions.terraform.templates")
        terraform_workflow_content = terraform_workflow_template.substitute(
            project_name=project_name
        )
        
        workflows_dir["terraform.yml"] = (terraform_workflow_content, no_overwrite())
        
        _logger.info("Generated .github/workflows/terraform.yml for Terraform IaC.")
    
    _logger.info("Generated Terraform IaC scaffolding in infra/terraform directory.")
    
    return struct, opts
