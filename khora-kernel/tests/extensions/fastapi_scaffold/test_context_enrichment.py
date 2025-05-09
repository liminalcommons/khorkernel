"""
Tests for FastAPI component context enrichment functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
import os
import yaml
from pathlib import Path

from unittest.mock import patch, MagicMock

from khora_kernel_vnext.extensions.fastapi_scaffold.extension import (
    FastApiScaffoldExtension,
    analyze_fastapi_endpoints,
    extract_fastapi_components,
    fastapi_context_contribution
)
from khora_kernel_vnext.extensions.core.extension import CoreExtension


def test_analyze_fastapi_endpoints():
    """Test extraction of endpoint information from FastAPI code using AST."""
    # Example FastAPI code with endpoints
    code = """
from fastapi import FastAPI, HTTPException, Depends

app = FastAPI(title="Test API", version="1.0.0")

@app.get("/", tags=["root"], summary="Root endpoint")
def root():
    \"\"\"Root endpoint that returns a welcome message.\"\"\"
    return {"message": "Welcome to the API"}

@app.post("/items", tags=["items"])
def create_item(item: dict):
    return {"item_id": 123, **item}

@app.get("/items/{item_id}")
def get_item(item_id: int):
    return {"item_id": item_id, "name": "Test Item"}
"""
    
    # Parse the endpoints from the code
    endpoints = analyze_fastapi_endpoints(code)
    
    # Verify the extracted endpoints
    assert len(endpoints) == 3
    
    # Check root endpoint
    root_endpoint = next(ep for ep in endpoints if ep["path"] == "/")
    assert root_endpoint["method"] == "get"
    assert root_endpoint["name"] == "root"
    assert root_endpoint["tags"] == ["root"]
    assert root_endpoint["summary"] == "Root endpoint"
    assert "Root endpoint that returns a welcome message" in root_endpoint["description"]
    
    # Check create_item endpoint
    create_endpoint = next(ep for ep in endpoints if ep["path"] == "/items" and ep["method"] == "post")
    assert create_endpoint["name"] == "create_item"
    assert create_endpoint["tags"] == ["items"]
    
    # Check get_item endpoint
    get_endpoint = next(ep for ep in endpoints if "/items/{item_id}" in ep["path"])
    assert get_endpoint["method"] == "get"
    assert get_endpoint["name"] == "get_item"


def test_extract_fastapi_components():
    """Test extraction of component information from template content."""
    # Example template content
    template_content = """
from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="{{ opts.project_path.name }}",
    version="{{ opts.version }}",
    description="{{ opts.description }}"
)

@app.get("/", tags=["health"])
def root():
    \"\"\"Root endpoint for API health check.\"\"\"
    return {"status": "ok"}

@app.get("/items", tags=["items"])
def list_items():
    \"\"\"List all items.\"\"\"
    return {"items": []}
"""

    # Mock opts
    opts = {
        "project_path": Path("test_project"),
        "version": "0.1.0",
        "description": "Test project description"
    }
    
    # Extract component information
    components = extract_fastapi_components(template_content, opts)
    
    # Verify the extracted component information
    assert components["type"] == "fastapi"
    assert "api_info" in components
    assert components["api_info"]["endpoints_count"] == 2
    
    # Check endpoints in component info
    endpoints = components["api_info"]["endpoints"]
    assert len(endpoints) == 2
    
    # Check root endpoint
    root_endpoint = next(ep for ep in endpoints if ep["path"] == "/")
    assert root_endpoint["method"] == "get"
    assert root_endpoint["tags"] == ["health"]
    
    # Check list_items endpoint
    items_endpoint = next(ep for ep in endpoints if ep["path"] == "/items")
    assert items_endpoint["method"] == "get"
    assert items_endpoint["name"] == "list_items"


def test_fastapi_context_contribution():
    """Test the fastapi_context_contribution action."""
    # Create test structure and opts
    struct = {}
    opts = {
        "khora_config": MagicMock()
    }
    
    # Configure mock khora_config
    opts["khora_config"].features.fastapi = True
    
    # Mock the extract_fastapi_components function
    mock_components = {
        "type": "fastapi",
        "api_info": {
            "endpoints_count": 1,
            "endpoints": [
                {
                    "path": "/test",
                    "method": "get",
                    "name": "test_endpoint",
                    "tags": ["test"],
                    "summary": "Test endpoint",
                    "description": "Test endpoint description"
                }
            ]
        }
    }
    
    with patch("khora_kernel_vnext.extensions.fastapi_scaffold.extension.extract_fastapi_components", 
               return_value=mock_components):
        # Call the action
        result_struct, result_opts = fastapi_context_contribution(struct, opts)
        
        # Verify the results
        assert result_struct == struct  # Structure should not be modified
        assert "component_info" in result_opts
        assert "fastapi" in result_opts["component_info"]
        assert result_opts["component_info"]["fastapi"] == mock_components


def test_component_info_in_context_yaml():
    """
    Test that component info is correctly included in context.yaml.
    Tests integration between FastAPI extension and Core extension.
    """
    # Create test opts with component_info
    opts = {
        "project_path": Path("/tmp/test_project"),
        "khora_config": MagicMock(),
        "component_info": {
            "fastapi": {
                "type": "fastapi",
                "api_info": {
                    "endpoints_count": 2,
                    "endpoints": [
                        {
                            "path": "/",
                            "method": "get",
                            "name": "root",
                            "tags": ["root"],
                            "summary": "Root endpoint"
                        },
                        {
                            "path": "/items",
                            "method": "get",
                            "name": "list_items",
                            "tags": ["items"],
                            "summary": "List items"
                        }
                    ]
                }
            }
        }
    }
    
    # Configure mock khora_config
    opts["khora_config"].project_description = "Test project description"
    opts["khora_config"].paths.model_dump.return_value = {"src": "src", "docs": "docs"}
    
    # Create the CoreExtension instance
    core_extension = CoreExtension()
    
    # Mock reading the VERSION file
    with patch("builtins.open", MagicMock()), \
         patch("pathlib.Path.read_text", return_value="0.1.0"), \
         patch("yaml.dump") as mock_yaml_dump:
        
        # Call the context generation action
        struct = {}
        result_struct, _ = core_extension._generate_khora_context_yaml(struct, opts)
        
        # Get the context data that would be written to context.yaml
        context_data = mock_yaml_dump.call_args[0][0]
        
        # Verify components section in the context data
        assert "components" in context_data
        assert "fastapi" in context_data["components"]
        assert context_data["components"]["fastapi"]["type"] == "fastapi"
        assert context_data["components"]["fastapi"]["api_info"]["endpoints_count"] == 2
        assert len(context_data["components"]["fastapi"]["api_info"]["endpoints"]) == 2
        
        # Verify the context.yaml file is included in the structure
        assert ".khora" in result_struct
        assert "context.yaml" in result_struct[".khora"]


def test_fastapi_extension_actions_registration():
    """Test that FastAPI extension registers both actions correctly."""
    extension = FastApiScaffoldExtension()
    extension.opts = {"khora_fastapi_scaffold": True}
    
    # Create a list of mock actions
    action1 = MagicMock(__name__="action1")
    action2 = MagicMock(__name__="define_structure")
    action3 = MagicMock(__name__="_generate_khora_context_yaml")
    action4 = MagicMock(__name__="action4")
    actions = [action1, action2, action3, action4]
    
    # Activate the extension
    result = extension.activate(actions)
    
    # Verify the actions list now has correct ordering
    # and includes both our structure generation and context contribution actions
    assert len(result) == 6  # original 4 + 2 new actions
    
    # Find our added actions by indexing
    # First one should be added after define_structure
    assert result[2].__name__ == "fastapi_generate_api_structure"
    
    # Second one should be added before _generate_khora_context_yaml
    context_yaml_index = result.index(action3)
    assert result[context_yaml_index - 1].__name__ == "fastapi_context_contribution"
