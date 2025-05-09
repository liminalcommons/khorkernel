"""
Context contribution interfaces for Khora Kernel.

This module provides the interfaces and utilities for extensions to contribute
structured information to the context.yaml file, enabling rich project documentation.
"""

import logging
from typing import Any, Dict, List, Optional, Protocol, TypeVar, Union

from pyscaffold.actions import ScaffoldOpts

logger = logging.getLogger(__name__)

# Type aliases for type hinting
ComponentInfo = Dict[str, Any]  # The structured component info data
ComponentName = str  # The name/key for a component in context.yaml


class ContributedComponent:
    """
    Represents a single component that will be contributed to context.yaml.
    
    This class provides a structured way to define component information
    that will be included in the "components" section of context.yaml.
    """
    
    def __init__(
        self,
        name: str,
        component_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        subcomponents: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize a component to contribute to context.yaml.
        
        Args:
            name: Unique identifier for this component
            component_type: Type of component (e.g., "api", "database", "frontend")
            metadata: Additional metadata about the component
            subcomponents: List of nested components
        """
        self.name = name
        self.component_type = component_type
        self.metadata = metadata or {}
        self.subcomponents = subcomponents or []
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the component to a dictionary for context.yaml.
        
        Returns:
            Dictionary representation of the component
        """
        result = {
            "type": self.component_type,
            **self.metadata
        }
        
        if self.subcomponents:
            result["subcomponents"] = self.subcomponents
            
        return result


class ContextContributor(Protocol):
    """
    Protocol for extensions that contribute to the context.yaml file.
    
    Extensions implementing this protocol can contribute structured information
    to context.yaml for project documentation and machine-readable metadata.
    """
    
    def contribute_to_context(self, opts: ScaffoldOpts) -> Dict[str, Any]:
        """
        Contribute structured information to context.yaml.
        
        Args:
            opts: PyScaffold options containing project configuration
            
        Returns:
            Dictionary containing data to be added to context.yaml
        """
        ...


def add_component_to_opts(opts: ScaffoldOpts, component_name: str, component_info: ComponentInfo) -> None:
    """
    Add component information to the opts dictionary for later context.yaml generation.
    
    This is a helper function that extensions can use to store component information
    in the opts dictionary, which will later be used by the core extension to
    generate the context.yaml file.
    
    Args:
        opts: PyScaffold options dictionary
        component_name: Name/key for the component in the context.yaml
        component_info: Structured information about the component
    """
    if "component_info" not in opts:
        opts["component_info"] = {}
        
    existing = opts["component_info"].get(component_name)
    if existing:
        logger.warning(
            f"Component '{component_name}' already exists in component_info. "
            "Overwriting with new information."
        )
        
    opts["component_info"][component_name] = component_info
    logger.debug(f"Added component '{component_name}' to component_info in opts")


def get_component_from_opts(opts: ScaffoldOpts, component_name: str) -> Optional[ComponentInfo]:
    """
    Get component information from the opts dictionary.
    
    Args:
        opts: PyScaffold options dictionary
        component_name: Name/key for the component to retrieve
        
    Returns:
        Component information if found, None otherwise
    """
    if "component_info" not in opts:
        return None
        
    return opts["component_info"].get(component_name)


def merge_component_infos(original: ComponentInfo, addition: ComponentInfo) -> ComponentInfo:
    """
    Merge two component information dictionaries.
    
    This function performs a deep merge of the two dictionaries, with values
    from addition taking precedence over values from original for simple keys.
    Lists are concatenated, and nested dictionaries are recursively merged.
    
    Args:
        original: Original component information
        addition: Additional component information to merge
        
    Returns:
        Merged component information
    """
    result = original.copy()
    
    for key, value in addition.items():
        if key not in result:
            # Simple case: key doesn't exist in original
            result[key] = value
        elif isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge dictionaries
            result[key] = merge_component_infos(result[key], value)
        elif isinstance(result[key], list) and isinstance(value, list):
            # Concatenate lists
            result[key] = result[key] + value
        else:
            # Override original value
            result[key] = value
            
    return result
