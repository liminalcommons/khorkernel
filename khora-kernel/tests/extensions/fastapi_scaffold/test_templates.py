import pytest
from pathlib import Path
import os

from pyscaffold.templates import get_template

def test_template_loading():
    """
    Test that the template files for FastAPI scaffolding can be loaded correctly.
    """
    # Test loading the main_py template
    main_py_template = get_template("main_py", 
                       relative_to="khora_kernel_vnext.extensions.fastapi_scaffold.templates")
    assert main_py_template is not None
    
    # Test loading the requirements_txt template
    requirements_txt_template = get_template("requirements_txt",
                              relative_to="khora_kernel_vnext.extensions.fastapi_scaffold.templates")
    assert requirements_txt_template is not None
    
    # Test loading the Dockerfile template
    dockerfile_template = get_template("dockerfile_j2",
                         relative_to="khora_kernel_vnext.extensions.fastapi_scaffold.templates")
    assert dockerfile_template is not None
    
    # We're not checking the content because PyScaffold get_template returns a Template object,
    # not a string. We'd need to call substitute() or similar to get the actual content.
