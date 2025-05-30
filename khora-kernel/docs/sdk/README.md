# Khora Kernel SDK Documentation

## Overview

The Khora Kernel SDK provides a standardized set of interfaces, base classes, and utilities for developing extensions for the Khora project scaffolding system. It builds on top of PyScaffold's extension system to provide a more structured, type-safe, and feature-rich development experience.

## Core Concepts

### Extension Lifecycle

The Khora extension system follows a predictable lifecycle:

1. **Registration**: Extensions are registered with PyScaffold via entry points
2. **CLI Augmentation**: Extensions add their command-line options
3. **Activation**: When enabled, extensions register their actions
4. **Action Execution**: Actions run in the order defined by their hooks
5. **Context Contribution**: Extensions can contribute to the project's context.yaml

### Key Components

- **KhoraExtension**: Base class for all Khora extensions
- **Actions**: Functions that modify the PyScaffold structure
- **Templates**: Template files for generating project files
- **Context Contributors**: Interfaces for contributing to context.yaml
- **Configuration Accessors**: Utilities for accessing Khora manifest config

## Using the SDK

### Creating a New Extension

To create a new extension, create a new class that inherits from `KhoraExtension`:

```python
from khora_kernel_vnext.sdk import KhoraExtension

class MyAwesomeExtension(KhoraExtension):
    name = "my_awesome"  # Will be --my-awesome in CLI
    
    def activate(self, actions):
        # Only proceed if the extension is enabled
        if not self.opts.get(self.name):
            return actions
            
        # Register your actions
        actions = self.register(
            actions, 
            my_action_function, 
            after="define_structure"
        )
        
        return actions
```

### Defining Actions

Actions are functions that modify the PyScaffold structure and options:

```python
from khora_kernel_vnext.sdk import KhoraAction, create_extension_action
from pyscaffold.actions import Structure, ScaffoldOpts
from pyscaffold.operations import no_overwrite

def my_action_function(struct: Structure, opts: ScaffoldOpts):
    # Use the KhoraConfigAccessor to get configuration
    from khora_kernel_vnext.sdk import get_config_accessor
    config = get_config_accessor(opts)
    
    if not config.is_feature_enabled("my_feature"):
        return struct, opts
        
    # Create your structure modifications
    new_files = {
        "my_directory/my_file.py": (
            "# Generated by MyAwesomeExtension\n\ndef hello():\n    print('Hello')\n",
            no_overwrite(),
        )
    }
    
    # Merge with existing structure
    struct.update(new_files)
    
    return struct, opts

# Alternatively, use the factory function
my_named_action = create_extension_action(
    "generate_my_files",
    my_action_function,
    "Generates files for MyAwesomeExtension"
)
```

### Working with Templates

The SDK provides utilities for loading and rendering templates:

```python
from khora_kernel_vnext.sdk import TemplateManager

def generate_from_templates(struct, opts):
    # Create a template manager for your extension
    template_mgr = TemplateManager("my_awesome")
    
    # Load a template
    template_content = template_mgr.get_template("my_template")
    
    # Render with context
    rendered_content = template_mgr.render_pyscaffold_template(
        template_content,
        {"project_name": opts.get("project_path").name}
    )
    
    # Add to structure
    struct["my_file.py"] = (rendered_content, no_overwrite())
    
    return struct, opts
```

### Contributing to Context

Extensions can contribute structured information to the context.yaml file:

```python
from khora_kernel_vnext.sdk import add_component_to_opts, ContributedComponent

def contribute_to_context(struct, opts):
    # Create a component
    component = ContributedComponent(
        name="my_component",
        component_type="service",
        metadata={
            "language": "python",
            "endpoints": ["GET /api/v1/resource"],
        }
    )
    
    # Add to opts for later context.yaml generation
    add_component_to_opts(opts, "my_component", component.to_dict())
    
    return struct, opts
```

### Accessing Configuration

The SDK provides structured access to the Khora manifest configuration:

```python
from khora_kernel_vnext.sdk import get_config_accessor

def my_action(struct, opts):
    config = get_config_accessor(opts)
    
    # Check if a feature is enabled
    if config.is_feature_enabled("my_feature"):
        # Do something
        pass
        
    # Get a path with default
    api_dir = config.get_path("api_dir", "api")
    
    # Get plugin-specific configuration
    my_plugin_config = config.get_plugin_config("my_awesome")
    
    # Validate required configuration is present
    required_paths = [
        ["features", "my_feature"],
        ["paths", "api_dir"]
    ]
    if not config.validate_required_config(required_paths):
        # Handle missing config
        pass
        
    return struct, opts
```

## Best Practices

### Error Handling

Always use try/except blocks to catch exceptions in your extensions and provide meaningful error messages:

```python
import logging
logger = logging.getLogger(__name__)

def my_action(struct, opts):
    try:
        # Your code
        return struct, opts
    except Exception as e:
        logger.error(f"Error in MyAwesomeExtension: {e}")
        return struct, opts
```

### Testing Extensions

Test your extensions using pytest:

```python
import pytest
from pyscaffold.extensions import Extension
from khora_kernel_vnext.extensions.my_awesome import MyAwesomeExtension

def test_extension_activation():
    # Create extension instance
    ext = MyAwesomeExtension()
    ext.opts = {"my_awesome": True}
    
    # Create a dummy actions list
    actions = []
    
    # Run activation
    result = ext.activate(actions)
    
    # Assert that actions were added
    assert len(result) > 0
```

### Documentation

Document your extension with docstrings and explanatory comments:

```python
"""
MyAwesomeExtension for Khora Kernel.

This extension adds awesome functionality to the project.
It requires features.my_feature to be enabled in pyproject.toml.
"""
```

## Key SDK Components Reference

### Extension Module

- `KhoraExtension`: Base class for all Khora extensions
- `KhoraAction`: Type alias for action functions
- `KhoraActionParams`: Type alias for action return type
- `create_extension_action`: Factory function for creating named actions

### Context Module

- `ContextContributor`: Protocol for extensions contributing to context.yaml
- `ContributedComponent`: Class representing a component in context.yaml
- `add_component_to_opts`: Helper to add component information to opts
- `get_component_from_opts`: Helper to get component information from opts

### Templates Module

- `TemplateManager`: Class for managing extension templates
- `get_extension_template`: Function to get a template from an extension's templates directory

### Config Module

- `KhoraConfigAccessor`: Class for accessing Khora configuration
- `get_config_accessor`: Factory function for creating config accessors

### Utils Module

- `ensure_directory`: Create a directory if it doesn't exist
- `copy_directory_structure`: Copy a directory structure
- `safe_run_command`: Safely run a shell command
- `snake_to_camel`, `snake_to_pascal`, `camel_to_snake`: String case conversion
- `store_value_in_opts`: Store values in PyScaffold opts
- `get_nested_value`: Access nested values in dictionaries
- `sanitize_filename`: Sanitize a string for use as a filename

## Registering Your Extension

Register your extension in your project's `pyproject.toml`:

```toml
[project.entry-points."pyscaffold.cli"]
my_awesome = "my_package.my_module:MyAwesomeExtension"
```

## Extension Registration and Discovery

Extensions are discovered via entry points in the "pyscaffold.cli" group. The Khora command-line interface will find all registered extensions and make them available for use.
