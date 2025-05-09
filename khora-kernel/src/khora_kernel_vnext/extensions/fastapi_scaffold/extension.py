"""
FastAPI Scaffolding Extension for Khora Kernel.

This extension generates a basic FastAPI application structure if requested
in the [tool.khora.features] section of the target project's pyproject.toml.
It also contributes API component information for context.yaml enrichment.
"""
import argparse
import ast
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import os

from pyscaffold.actions import Action, ActionParams, ScaffoldOpts, Structure
from pyscaffold.extensions import Extension
from pyscaffold.operations import no_overwrite # 'define' was unused
# The ensure_parent_dir_exists function doesn't exist in PyScaffold
from pyscaffold.templates import get_template

# Assuming khora manifest parsing logic is available.
# This might need to be adjusted based on where MVK-CORE-01 placed it.
# For now, let's assume a utility function or class exists.
# from khora_kernel_vnext.manifest import KhoraManifestParser # Placeholder

LOG = logging.getLogger(__name__)

DEFAULT_API_DIR = "api"
# PyScaffold's get_template function automatically adds ".template" to the filename,
# so we need to specify just the base name without ".template"
MAIN_PY_TEMPLATE = get_template("main_py", relative_to="khora_kernel_vnext.extensions.fastapi_scaffold.templates")
REQUIREMENTS_TXT_TEMPLATE = get_template("requirements_txt", relative_to="khora_kernel_vnext.extensions.fastapi_scaffold.templates")
DOCKERFILE_TEMPLATE = get_template("dockerfile_j2", relative_to="khora_kernel_vnext.extensions.fastapi_scaffold.templates")


def analyze_fastapi_endpoints(code_str: str) -> List[Dict[str, Any]]:
    """
    Analyze FastAPI code using AST to extract endpoint information.
    
    Args:
        code_str: String containing the FastAPI application code
        
    Returns:
        List of dictionaries containing endpoint information
    """
    endpoints = []
    
    try:
        # Parse the code into an AST
        tree = ast.parse(code_str)
        
        # Find decorated functions that might be FastAPI endpoints
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    # Check if decorator is an app method call (e.g., @app.get)
                    if (isinstance(decorator, ast.Call) and 
                        isinstance(decorator.func, ast.Attribute) and
                        isinstance(decorator.func.value, ast.Name) and
                        decorator.func.value.id == 'app'):
                        
                        http_method = decorator.func.attr.lower()  # get, post, put, etc.
                        
                        # Get path from the first argument if available
                        path = "/"
                        if decorator.args:
                            # Try to get the string value - use ast.Constant instead of ast.Str (Python 3.8+)
                            if isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                                path = decorator.args[0].value
                            # Fallback for older Python versions
                            elif isinstance(decorator.args[0], ast.Str):
                                path = decorator.args[0].s
                        
                        # Extract other metadata from decorator keywords
                        tags = []
                        summary = None
                        description = None
                        
                        for keyword in decorator.keywords:
                            if keyword.arg == 'tags' and isinstance(keyword.value, ast.List):
                                for elt in keyword.value.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                        tags.append(elt.value)
                                    # Fallback for older Python versions
                                    elif isinstance(elt, ast.Str):
                                        tags.append(elt.s)
                            elif keyword.arg == 'summary':
                                if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                                    summary = keyword.value.value
                                # Fallback for older Python versions
                                elif isinstance(keyword.value, ast.Str):
                                    summary = keyword.value.s
                        
                        # Try to get docstring for description
                        if ast.get_docstring(node):
                            description = ast.get_docstring(node)
                        
                        endpoint_info = {
                            "path": path,
                            "method": http_method,
                            "name": node.name,
                            "tags": tags,
                            "summary": summary,
                            "description": description
                        }
                        
                        endpoints.append(endpoint_info)
        
        return endpoints
    except Exception as e:
        LOG.error(f"Error analyzing FastAPI endpoints: {e}")
        return []


def extract_fastapi_components(template_content: str | object, opts: ScaffoldOpts) -> Dict[str, Any]:
    """
    Extract FastAPI component information from template content and format for context.yaml.
    
    Args:
        template_content: String containing the FastAPI template content or a Template object
        opts: ScaffoldOpts containing configuration information
        
    Returns:
        Dictionary containing FastAPI component information
    """
    # Process template to get actual code that will be generated
    # Handle both string and Template objects
    if hasattr(template_content, 'template'):
        # It's a Template object
        code_str = template_content.template
    elif isinstance(template_content, str):
        code_str = template_content
    else:
        # If we can't determine what it is, return a basic structure
        return {
            "type": "fastapi",
            "api_info": {
                "endpoints_count": 0,
                "endpoints": []
            }
        }
    
    # Replace template variables with placeholder values for AST parsing
    # This is a basic implementation; might need more sophisticated template processing
    code_str = code_str.replace("{{ opts.project_path.name }}", "ProjectName")
    code_str = code_str.replace("{{ opts.version }}", "0.1.0")
    code_str = code_str.replace("{{ opts.description }}", "API Description")
    
    # Extract endpoints
    endpoints = analyze_fastapi_endpoints(code_str)
    
    # Format components for context.yaml
    fastapi_components = {
        "type": "fastapi",
        "api_info": {
            "endpoints_count": len(endpoints),
            "endpoints": endpoints
        }
    }
    
    return fastapi_components


def fastapi_context_contribution(struct: Structure, opts: ScaffoldOpts) -> ActionParams:
    """
    Action to contribute FastAPI component information to opts for context.yaml generation.
    """
    khora_config = opts.get("khora_config")
    
    if not khora_config or not getattr(khora_config.features, "fastapi", False):
        # FastAPI not enabled, nothing to contribute
        return struct, opts
    
    LOG.info("Extracting FastAPI component information for context enrichment...")
    
    # Get template content
    template_content = MAIN_PY_TEMPLATE
    
    # Extract component information
    fastapi_components = extract_fastapi_components(template_content, opts)
    
    # Store in opts for core extension to use
    if "component_info" not in opts:
        opts["component_info"] = {}
    
    # Add FastAPI components to component_info
    opts["component_info"]["fastapi"] = fastapi_components
    
    LOG.info(f"Added FastAPI component information: {len(fastapi_components['api_info']['endpoints'])} endpoints")
    
    return struct, opts


def fastapi_generate_api_structure(struct: Structure, opts: ScaffoldOpts) -> ActionParams:
    """
    Action to generate the FastAPI app structure.
    This function will be called via PyScaffold's action system.
    """
    # Get the Pydantic model from opts
    khora_config = opts.get("khora_config")
    
    if not khora_config:
        LOG.warning("Khora config not found in opts. Skipping FastAPI scaffolding.")
        return struct, opts
        
    # Check if the FastAPI feature is enabled
    if not getattr(khora_config.features, "fastapi", False):
        LOG.info("FastAPI feature not enabled in [tool.khora.features]. Skipping scaffolding.")
        return struct, opts

    # Get API directory from paths
    api_dir_name = getattr(khora_config.paths, "api_dir", DEFAULT_API_DIR)
    api_dir = Path(opts["project_path"]) / api_dir_name

    LOG.info(f"Generating FastAPI structure in {api_dir}...")

    # Define the files to be created
    files: Structure = {
        str(api_dir / "main.py"): (
            MAIN_PY_TEMPLATE,
            no_overwrite(),
        ),
        str(api_dir / "requirements.txt"): (
            REQUIREMENTS_TXT_TEMPLATE,
            no_overwrite(),
        ),
        str(api_dir / "Dockerfile"): (
            DOCKERFILE_TEMPLATE, # Jinja2 template
            no_overwrite(),
        ),
    }

    # PyScaffold automatically creates parent directories when merging structures,
    # so we don't need to manually create them

    # Merge with existing structure
    struct = {**struct, **files}
    
    # Add variables for Jinja2 template rendering for Dockerfile
    docker_config = getattr(getattr(khora_config, "plugins_config", {}), "docker", {})
    opts["docker_api_service_name"] = getattr(docker_config, "api_service_name", "api")
    opts["api_dir_name"] = api_dir_name # To be used in Dockerfile COPY command

    return struct, opts


class FastApiScaffoldExtension(Extension):
    """Generates a basic FastAPI application structure."""

    name = "fastapi_scaffold" # Name used to activate the extension

    def augment_cli(self, parser: argparse.ArgumentParser):
        """Add a CLI option for this extension"""
        parser.add_argument(
            self.flag, # self.flag is derived from self.name
            dest=self.name,
            action="store_true",
            default=False,
            help="Activate FastAPI scaffolding for the project",
        )
        return self

    def activate(self, actions: List[Action]) -> List[Action]:
        """
        Activate extension. See :obj:`pyscaffold.extensions.Extension.activate`.
        """
        # Here we would ideally parse the pyproject.toml of the TARGET project.
        # PyScaffold's options (`opts`) usually carry this information after
        # it has read the pyproject.toml.
        # For now, we assume that the parsing logic from MVK-CORE-01
        # has run and populated `opts['khora_config']`.

        # Register our action to generate the FastAPI structure
        actions = self.register(
            actions,
            fastapi_generate_api_structure,
            after="define_structure",
        )
        
        # Register the action to contribute component information to context.yaml
        # This should run before the core extension's context generation
        actions = self.register(
            actions,
            fastapi_context_contribution,
            before="_generate_khora_context_yaml",
        )
        
        LOG.info("FastAPI Scaffold Extension activated with context enrichment.")
        return actions

    # We might need a `requires` method if we depend on another extension
    # to parse the khora manifest first.
    # def requires(self) -> List[str]:
    #     return ["khora_core"] # Example if core extension handles manifest parsing
