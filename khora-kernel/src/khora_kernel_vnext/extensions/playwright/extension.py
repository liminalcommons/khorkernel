import argparse
import logging
from pathlib import Path

from pyscaffold.actions import Action, ActionParams, ScaffoldOpts, Structure
from pyscaffold.extensions import Extension
from pyscaffold.operations import no_overwrite
from pyscaffold.templates import get_template

_logger = logging.getLogger(__name__)

class PlaywrightExtension(Extension):
    """Generates scaffolding for UI testing with Playwright."""

    name = "khora_playwright"  # kebab-case for the CLI flag

    def augment_cli(self, parser: argparse.ArgumentParser):
        """Add a CLI option for this extension"""
        parser.add_argument(
            self.flag, # self.flag is derived from self.name
            dest=self.name,
            action="store_true",
            default=False,
            help="Add Playwright UI testing scaffolding to the project",
        )
        return self

    def activate(self, actions: list[Action]) -> list[Action]:
        """Activate extension rules."""
        actions = self.register(actions, add_playwright_scaffolding, after="define_structure")
        return actions


def add_playwright_scaffolding(
    struct: Structure, opts: ScaffoldOpts
) -> ActionParams:
    """Add the Playwright UI testing scaffolding to the project structure.

    Args:
        struct: project representation as (possibly) nested :obj:`dict`.
        opts: given options.

    Returns:
        Project structure and options
    """
    # Get the Pydantic model from opts
    khora_config = opts.get("khora_config")
    
    if not khora_config:
        _logger.warning("Khora config not found in opts. Skipping Playwright scaffolding generation.")
        return struct, opts
        
    # Check if the Playwright feature is enabled
    if not getattr(khora_config.features, "playwright", False):
        _logger.info("Khora Playwright feature not enabled. Skipping Playwright scaffolding generation.")
        return struct, opts

    # Get Python version from khora_config
    python_version = getattr(khora_config, "python_version", "3.9") # Default Python version
    
    # Get the project name from khora_config or fall back to opts['name']
    project_name = getattr(khora_config, "project_name", None)
    if not project_name:
        project_name = opts.get("name", "khora-project")  # PyScaffold sets 'name', but as fallback use a default
        _logger.info(f"Using project name from PyScaffold: {project_name}")
    
    # Create tests/ui directory structure if it doesn't exist
    tests_dir = struct.setdefault("tests", {})
    if not isinstance(tests_dir, dict): # If tests was a file, overwrite with dict
        tests_dir = {}
        struct["tests"] = tests_dir
        
    ui_dir = tests_dir.setdefault("ui", {})
    if not isinstance(ui_dir, dict): # If ui was a file, overwrite
        ui_dir = {}
        tests_dir["ui"] = ui_dir

    # Create the necessary files for Playwright testing
    
    # playwright.config.py
    playwright_config_template = get_template("playwright_config_py", relative_to="khora_kernel_vnext.extensions.playwright.templates")
    playwright_config_content = playwright_config_template.substitute(
        project_name=project_name
    )
    ui_dir["playwright.config.py"] = (playwright_config_content, no_overwrite())
    
    # conftest.py
    conftest_template = get_template("conftest_py", relative_to="khora_kernel_vnext.extensions.playwright.templates")
    conftest_content = conftest_template.substitute()
    ui_dir["conftest.py"] = (conftest_content, no_overwrite())
    
    # requirements.txt
    requirements_template = get_template("requirements_txt", relative_to="khora_kernel_vnext.extensions.playwright.templates")
    requirements_content = requirements_template.substitute()
    ui_dir["requirements.txt"] = (requirements_content, no_overwrite())
    
    # Sample test files
    tests_subdir = ui_dir.setdefault("tests", {})
    if not isinstance(tests_subdir, dict):
        tests_subdir = {}
        ui_dir["tests"] = tests_subdir
    
    # __init__.py for tests directory
    tests_subdir["__init__.py"] = ("# UI tests package", no_overwrite())
    
    # sample_test.py
    sample_test_template = get_template("sample_test_py", relative_to="khora_kernel_vnext.extensions.playwright.templates")
    sample_test_content = sample_test_template.substitute(
        project_name=project_name
    )
    tests_subdir["test_sample.py"] = (sample_test_content, no_overwrite())
    
    # Add GitHub Actions workflow for Playwright tests if CI is enabled
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
        
        # Add playwright.yml workflow
        playwright_workflow_template = get_template("playwright_workflow_yml", relative_to="khora_kernel_vnext.extensions.playwright.templates")
        playwright_workflow_content = playwright_workflow_template.substitute(
            python_version=python_version,
            project_name=project_name,
            matrix_python_version="${{ matrix.python-version }}",
            HOME_PATH="$HOME",
            GITHUB_PATH="$GITHUB_PATH"
        )
        
        workflows_dir["playwright.yml"] = (playwright_workflow_content, no_overwrite())
        
        _logger.info("Generated .github/workflows/playwright.yml for Playwright UI tests.")
    
    _logger.info("Generated Playwright UI testing scaffolding in tests/ui directory.")
    
    return struct, opts
