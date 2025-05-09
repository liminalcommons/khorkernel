"""
Khora Kernel Plugin SDK.

This package provides the interfaces, base classes, and utilities for 
developing plugins (extensions) for the Khora Kernel.
"""

from .extension import (
    KhoraExtension,
    KhoraAction,
    KhoraActionParams,
    KhoraComponentProvider,
    create_extension_action,
)
from .context import (
    ContextContributor,
    ContributedComponent,
    ComponentInfo,
    add_component_to_opts,
    get_component_from_opts,
)
from .templates import TemplateManager, get_extension_template
from .config import KhoraConfigAccessor, get_config_accessor
from .utils import (
    ensure_directory,
    copy_directory_structure,
    safe_run_command,
    snake_to_camel,
    snake_to_pascal,
    camel_to_snake,
    store_value_in_opts,
    get_nested_value,
    sanitize_filename,
)

__all__ = [
    # Extension module
    "KhoraExtension",
    "KhoraAction",
    "KhoraActionParams",
    "KhoraComponentProvider",
    "create_extension_action",
    
    # Context module
    "ContextContributor",
    "ContributedComponent",
    "ComponentInfo",
    "add_component_to_opts",
    "get_component_from_opts",
    
    # Templates module
    "TemplateManager",
    "get_extension_template",
    
    # Config module
    "KhoraConfigAccessor",
    "get_config_accessor",
    
    # Utils module
    "ensure_directory",
    "copy_directory_structure",
    "safe_run_command",
    "snake_to_camel",
    "snake_to_pascal",
    "camel_to_snake",
    "store_value_in_opts",
    "get_nested_value",
    "sanitize_filename",
]
