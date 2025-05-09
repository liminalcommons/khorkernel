import argparse
import logging
from pathlib import Path

from pyscaffold.actions import Action, ActionParams, ScaffoldOpts, Structure
from pyscaffold.extensions import Extension
from pyscaffold.operations import no_overwrite
from pyscaffold.templates import get_template

_logger = logging.getLogger(__name__)

class CIGitHubActionsExtension(Extension):
    """Generates a GitHub Actions CI workflow file."""

    name = "khora_ci_github_actions"  # kebab-case for the CLI flag

    def augment_cli(self, parser: argparse.ArgumentParser):
        """Add a CLI option for this extension"""
        parser.add_argument(
            self.flag, # self.flag is derived from self.name
            dest=self.name,
            action="store_true",
            default=False,
            help="Add GitHub Actions CI workflow to the project",
        )
        return self

    def activate(self, actions: list[Action]) -> list[Action]:
        """Activate extension rules."""
        actions = self.register(actions, add_ci_workflow_file, after="define_structure")
        return actions

def add_ci_workflow_file(
    struct: Structure, opts: ScaffoldOpts
) -> ActionParams:
    """Add the .github/workflows/ci.yml file to the project structure.

    Args:
        struct: project representation as (possibly) nested :obj:`dict`.
        opts: given options.

    Returns:
        Project structure and options
    """
    # Get the Pydantic model from opts
    khora_config = opts.get("khora_config")
    
    if not khora_config:
        _logger.warning("Khora config not found in opts. Skipping CI workflow generation.")
        return struct, opts
        
    # Check if the CI GitHub Actions feature is enabled
    if not getattr(khora_config.features, "ci_github_actions", False):
        _logger.info("Khora CI GitHub Actions feature not enabled. Skipping CI workflow generation.")
        return struct, opts

    # Get Python version from khora_config
    python_version = getattr(khora_config, "python_version", "3.9") # Default Python version
    
    # Check if security gates are enabled
    security_gates_enabled = getattr(khora_config.features, "security_gates", False)
    
    # Prepare security gates steps
    security_gates_step = ""
    if security_gates_enabled:
        security_gates_step = """- name: Security scanning with pip-audit
      run: |
        uv pip install pip-audit
        uv pip audit
        
    - name: Security scanning with Bandit
      run: |
        uv pip install bandit
        bandit -r . -x ./tests
        
    - name: Secret scanning with TruffleHog
      run: |
        pip install trufflehog
        trufflehog --no-history . || true # Continue on errors for now, this is informational"""
    
    ci_workflow_template = get_template("ci_workflow_yml", relative_to="khora_kernel_vnext.extensions.ci_github_actions")
    
    # Get the project name from khora_config or fall back to opts['name']
    project_name = getattr(khora_config, "project_name", None)
    if not project_name:
        project_name = opts.get("name", "khora-project")  # PyScaffold sets 'name', but as fallback use a default
        _logger.info(f"Using project name from PyScaffold: {project_name}")
    
    ci_workflow_content = ci_workflow_template.substitute(
        python_version=python_version,
        project_name=project_name,
        matrix_python_version="${{ matrix.python-version }}",
        HOME_PATH="$HOME",
        GITHUB_PATH="$GITHUB_PATH",
        security_gates_step=security_gates_step
    )

    # Ensure .github/workflows directory exists in the structure
    github_dir = struct.setdefault(".github", {})
    if not isinstance(github_dir, dict): # If .github was a file, overwrite with dict
        github_dir = {}
        struct[".github"] = github_dir
        
    workflows_dir = github_dir.setdefault("workflows", {})
    if not isinstance(workflows_dir, dict): # If workflows was a file, overwrite
        workflows_dir = {}
        github_dir["workflows"] = workflows_dir

    workflows_dir["ci.yml"] = (ci_workflow_content, no_overwrite())
    
    _logger.info(f"Generated .github/workflows/ci.yml for Python {python_version}.")

    # Generate context-delta.yml workflow for KG feature
    context_delta_template = get_template("context_delta_yml", relative_to="khora_kernel_vnext.extensions.ci_github_actions")
    
    context_delta_content = context_delta_template.substitute(
        python_version=python_version,
        project_name=project_name,
        HOME_PATH="$HOME",
        GITHUB_PATH="$GITHUB_PATH"
    )
    
    workflows_dir["context-delta.yml"] = (context_delta_content, no_overwrite())
    
    _logger.info("Generated .github/workflows/context-delta.yml for Khora context change tracking.")

    return struct, opts
