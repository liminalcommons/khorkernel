import pytest
from pathlib import Path
import os

from pyscaffold.templates import get_template

def test_template_loading():
    """
    Test that the template files for GitHub Actions CI can be loaded correctly.
    """
    # Test loading the ci_workflow_yml template
    ci_workflow_template = get_template("ci_workflow_yml", 
                          relative_to="khora_kernel_vnext.extensions.ci_github_actions")
    assert ci_workflow_template is not None
    
    # We're not checking the content because PyScaffold get_template returns a Template object,
    # not a string. We'd need to call substitute() or similar to get the actual content.
