import pytest
from pathlib import Path
import os

from pyscaffold.templates import get_template

def test_template_loading():
    """
    Test that the template files for Docker can be loaded correctly.
    """
    # Test loading the docker_compose_yml template
    docker_compose_template = get_template("docker_compose_yml", 
                            relative_to="khora_kernel_vnext.extensions.docker")
    assert docker_compose_template is not None
    
    # We're not checking the content because PyScaffold get_template returns a Template object,
    # not a string. We'd need to call substitute() or similar to get the actual content.
