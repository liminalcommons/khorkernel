"""
Example custom extension using the Khora Kernel SDK.

This is a sample extension that demonstrates how to use the Khora Kernel SDK
to create a custom extension that adds a README.md file with a custom header
based on project configuration.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from pyscaffold.actions import Action, ScaffoldOpts, Structure
from pyscaffold.operations import no_overwrite

from khora_kernel_vnext.sdk import (
    KhoraExtension, 
    create_extension_action,
    get_config_accessor,
    ContributedComponent,
    add_component_to_opts
)

# Create a logger for this extension
logger = logging.getLogger(__name__)

class CustomHeaderExtension(KhoraExtension):
    """
    Example extension that adds a README.md with a custom header.
    
    This extension demonstrates how to use the Khora Kernel SDK to:
    - Create a custom extension
    - Add custom README content
    - Contribute to context.yaml
    """
    
    name = "custom_header"  # Will be available as --custom-header in CLI
    
    def activate(self, actions: List[Action]) -> List[Action]:
        """
        Activate the extension by registering actions.
        
        Args:
            actions: List of PyScaffold actions to modify
            
        Returns:
            Modified list of actions with this extension's actions registered
        """
        # Only proceed if the extension is enabled
        if not self.opts.get(self.name):
            return actions
            
        logger.info("Activating CustomHeaderExtension")
        
        # Register actions
        actions = self.register(
            actions, 
            create_custom_readme, 
            after="define_structure"
        )
        
        actions = self.register(
            actions,
            contribute_to_context,
            after="create_custom_readme"
        )
        
        return actions
        
    def requires(self) -> List[str]:
        """
        Define extension dependencies.
        
        Returns:
            List of extension names that this extension depends on
        """
        # Depend on the core extension
        return ["khora_core"]


def create_custom_readme(struct: Structure, opts: ScaffoldOpts) -> tuple[Structure, ScaffoldOpts]:
    """
    Create a custom README.md file.
    
    Args:
        struct: PyScaffold structure
        opts: PyScaffold options
        
    Returns:
        Updated structure and options
    """
    logger.info("Creating custom README.md")
    
    # Get config accessor for safe config access
    config = get_config_accessor(opts)
    
    # Get project name
    project_name = opts.get("project_path", Path(".")).name
    
    # Generate README content
    content = [
        f"# {project_name}",
        "",
        "## Overview",
        "",
        "This project was generated with Khora Kernel and the custom_header extension.",
        "",
        "## Features",
        "",
    ]
    
    # Add feature information if available
    if config.has_config and hasattr(config.config, "features"):
        for feature_name in dir(config.config.features):
            if not feature_name.startswith("_") and getattr(config.config.features, feature_name):
                content.append(f"- {feature_name}")
        
    # Add a blank line
    content.append("")
    
    # Join content into a string
    readme_content = "\n".join(content)
    
    # Add to structure
    struct["README.md"] = (readme_content, no_overwrite())
    
    return struct, opts


def contribute_to_context(struct: Structure, opts: ScaffoldOpts) -> tuple[Structure, ScaffoldOpts]:
    """
    Contribute to context.yaml.
    
    Args:
        struct: PyScaffold structure
        opts: PyScaffold options
        
    Returns:
        Updated structure and options
    """
    logger.info("Contributing to context.yaml")
    
    # Create a component
    component = ContributedComponent(
        name="documentation",
        component_type="documentation",
        metadata={
            "generator": "custom_header_extension",
            "files": ["README.md"]
        }
    )
    
    # Add to opts for later context.yaml generation
    add_component_to_opts(opts, "documentation", component.to_dict())
    
    return struct, opts
