"""
Template management utilities for Khora extensions.

This module provides utilities for loading, customizing, and rendering templates
for extensions, making it easier to work with both PyScaffold's template system
and Jinja2 templates.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from pyscaffold.templates import get_template as pyscaffold_get_template

# Import jinja2 at module level for easier testing and mocking
try:
    import jinja2
except ImportError:
    jinja2 = None

logger = logging.getLogger(__name__)


def render_template(template_content, context: Dict[str, Any]) -> str:
    """
    Render a template with the given context.
    
    This is a convenient function that determines whether to use PyScaffold
    or Jinja2 template rendering based on the template content.
    
    Args:
        template_content: Template content (string or Template object)
        context: Dictionary of variables to use in template rendering
        
    Returns:
        The rendered template as a string
    """
    # Check if we have a string.Template object
    import string
    if isinstance(template_content, string.Template):
        # Use safe_substitute to avoid KeyError for missing placeholders
        return template_content.safe_substitute(context)
    
    # For regular strings, use PyScaffold template rendering style
    result = template_content
    for key, value in context.items():
        placeholder = "{{{{ {} }}}}".format(key)
        result = result.replace(placeholder, str(value))
        
    return result


def get_extension_template(
    template_name: str, 
    extension_name: str, 
    extension_module: Optional[str] = None
) -> str:
    """
    Get a template from an extension's templates directory.
    
    This is a wrapper around PyScaffold's get_template function that allows
    extensions to load templates from their own templates directory.
    
    Args:
        template_name: Name of the template file without the .template extension
        extension_name: Name of the extension
        extension_module: Optional module path for the extension, defaults to
                         khora_kernel_vnext.extensions.<extension_name>
        
    Returns:
        The template content as a string
    """
    relative_to = extension_module
    if relative_to is None:
        relative_to = f"khora_kernel_vnext.extensions.{extension_name}.templates"
        
    try:
        return pyscaffold_get_template(template_name, relative_to=relative_to)
    except Exception as e:
        logger.error(f"Failed to load template {template_name} from {relative_to}: {e}")
        # Return empty string to avoid breaking the pipeline
        return ""
        

class TemplateManager:
    """
    Manager for extension templates.
    
    This class provides utilities for loading, customizing, and rendering templates
    for extensions. It supports both PyScaffold's template system and Jinja2 templates.
    """
    
    def __init__(self, extension_name: str, template_dir: Optional[str] = None):
        """
        Initialize the template manager.
        
        Args:
            extension_name: Name of the extension
            template_dir: Optional custom template directory path relative to the extension
        """
        self.extension_name = extension_name
        self.template_module = f"khora_kernel_vnext.extensions.{extension_name}"
        
        if template_dir:
            self.template_module = f"{self.template_module}.{template_dir}"
        else:
            self.template_module = f"{self.template_module}.templates"
            
        logger.debug(f"Initialized TemplateManager for {extension_name} with module {self.template_module}")
        
    def get_template(self, template_name: str) -> str:
        """
        Get a template by name.
        
        Args:
            template_name: Name of the template file without the .template extension
            
        Returns:
            The template content as a string
        """
        return get_extension_template(template_name, self.extension_name, self.template_module)
        
    def render_jinja2_template(self, template_content: str, context: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template with the given context.
        
        Args:
            template_content: Jinja2 template content
            context: Dictionary of variables to use in template rendering
            
        Returns:
            The rendered template as a string
        """
        # Use the module-level import for better testing
        if jinja2 is None:
            logger.error("Jinja2 is not installed. Cannot render Jinja2 template.")
            return template_content
            
        try:
            template = jinja2.Template(template_content)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render Jinja2 template: {e}")
            return template_content
            
    def render_pyscaffold_template(self, template_content, context: Dict[str, Any]) -> str:
        """
        Render a PyScaffold template with the given context.
        
        This method handles PyScaffold's template syntax with {{ variable }} substitution.
        
        Args:
            template_content: PyScaffold template content (string or Template object)
            context: Dictionary of variables to use in template rendering
            
        Returns:
            The rendered template as a string
        """
        # Check if we have a string.Template object and delegate to render_template
        import string
        if isinstance(template_content, string.Template):
            return template_content.safe_substitute(context)
            
        # For strings, use the regular PyScaffold template rendering
        result = template_content
        for key, value in context.items():
            placeholder = "{{{{ {} }}}}".format(key)
            result = result.replace(placeholder, str(value))
            
        return result
        
    def get_all_templates(self) -> Dict[str, str]:
        """
        Get all templates for this extension.
        
        Returns:
            Dictionary mapping template names to their content
        """
        templates = {}
        
        try:
            # Try to get the actual filesystem path for the template module
            module_parts = self.template_module.split(".")
            package_path = Path(__file__).parent.parent  # khora_kernel_vnext directory
            for part in module_parts:
                package_path = package_path / part
                
            if not package_path.exists() or not package_path.is_dir():
                logger.warning(f"Template directory {package_path} does not exist.")
                return templates
                
            # Get all .template files in the directory
            for filename in package_path.glob("*.template"):
                template_name = filename.stem  # Remove .template extension
                templates[template_name] = self.get_template(template_name)
                
            logger.debug(f"Found {len(templates)} templates in {package_path}")
        except Exception as e:
            logger.error(f"Failed to list templates for {self.extension_name}: {e}")
            
        return templates
