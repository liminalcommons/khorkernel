# Khora Kernel SDK API Reference

This document provides a detailed API reference for all components of the Khora Kernel SDK.

## Extension Module

The extension module provides the foundation for creating Khora extensions.

### KhoraExtension

```python
class KhoraExtension(Extension, abc.ABC)
```

Base class for all Khora extensions. Inherits from PyScaffold's Extension class and adds Khora-specific functionality.

#### Attributes

| Name | Type | Description |
|------|------|-------------|
| `persist` | `bool` | Whether the extension persists its options to the config file (default: `True`) |
| `sdk_version` | `str` | Version of SDK this extension is compatible with |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `activate` | `activate(self, actions: List[Action]) -> List[Action]` | Abstract method that all extensions must implement. Registers the extension's actions. |
| `register` | `register(self, actions: List[Action], action: KhoraAction, before: Optional[str] = None, after: Optional[str] = None) -> List[Action]` | Register an action with the PyScaffold action list with enhanced error handling. |
| `augment_cli` | `augment_cli(self, parser: argparse.ArgumentParser) -> "KhoraExtension"` | Add a CLI option for this extension. |
| `requires` | `requires(self) -> List[str]` | Define extension dependencies. By default, returns `["khora_core"]`. |
| `validate_config` | `validate_config(self, opts: ScaffoldOpts) -> bool` | Validate that the necessary configuration exists for this extension. |
| `create_merged_structure` | `create_merged_structure(self, original: Structure, addition: Structure) -> Structure` | Safely merge two PyScaffold structures. |

### KhoraComponentProvider

```python
class KhoraComponentProvider(Protocol)
```

Protocol for extensions that provide component information to context.yaml.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_component_info` | `get_component_info(self, opts: ScaffoldOpts) -> Dict[str, Any]` | Extract component information for context.yaml. |

### Type Aliases

| Name | Type | Description |
|------|------|-------------|
| `KhoraAction` | `Callable[[Structure, ScaffoldOpts], Tuple[Structure, ScaffoldOpts]]` | Type alias for action functions |
| `KhoraActionParams` | `Tuple[Structure, ScaffoldOpts]` | Type alias for action parameters and return values |
| `KhoraHookPoint` | `Tuple[str, ...]` | Type alias for hook point tuples, e.g., `('after', 'define_structure')` |

### Functions

#### create_extension_action

```python
def create_extension_action(
    name: str,
    action_func: Callable[[Structure, ScaffoldOpts], KhoraActionParams],
    description: str = ""
) -> KhoraAction
```

Create a named extension action with consistent logging and error handling.

#### Parameters

- `name`: Name for the action
- `action_func`: Function implementing the action
- `description`: Optional description of what the action does

#### Returns

A wrapped action function with the given name, standardized logging, and error handling.

## Context Module

The context module provides utilities for working with context.yaml contributions.

### ContextContributor

```python
class ContextContributor(Protocol)
```

Protocol for extensions that contribute to context.yaml.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `contribute_to_context` | `contribute_to_context(self, struct: Structure, opts: ScaffoldOpts) -> Tuple[Structure, ScaffoldOpts]` | Contribute to context.yaml by modifying struct and/or opts. |

### ComponentInfo

```python
class ComponentInfo(TypedDict)
```

Type definition for component information in context.yaml.

#### Attributes

| Name | Type | Description |
|------|------|-------------|
| `name` | `str` | Name of the component |
| `type` | `str` | Type of the component |
| `metadata` | `Dict[str, Any]` | Metadata for the component |

### ContributedComponent

```python
class ContributedComponent
```

Class representing a component in context.yaml.

#### Constructor

```python
def __init__(self, name: str, component_type: str, metadata: Dict[str, Any] = None)
```

#### Parameters

- `name`: Name of the component
- `component_type`: Type of the component
- `metadata`: Optional metadata for the component

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `to_dict` | `to_dict(self) -> Dict[str, Any]` | Convert the component to a dictionary. |

### Functions

#### add_component_to_opts

```python
def add_component_to_opts(opts: ScaffoldOpts, component_name: str, component_data: Dict[str, Any]) -> None
```

Add component information to opts for later context.yaml generation.

#### Parameters

- `opts`: PyScaffold options
- `component_name`: Name of the component
- `component_data`: Data for the component

#### get_component_from_opts

```python
def get_component_from_opts(opts: ScaffoldOpts, component_name: str) -> Optional[Dict[str, Any]]
```

Get component information from opts.

#### Parameters

- `opts`: PyScaffold options
- `component_name`: Name of the component

#### Returns

Component data as a dictionary if found, None otherwise.

## Templates Module

The templates module provides utilities for working with templates.

### TemplateManager

```python
class TemplateManager
```

Manager for extension templates.

#### Constructor

```python
def __init__(self, extension_name: str, template_dir: Optional[str] = None)
```

#### Parameters

- `extension_name`: Name of the extension
- `template_dir`: Optional custom template directory path relative to the extension

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_template` | `get_template(self, template_name: str) -> str` | Get a template by name. |
| `render_jinja2_template` | `render_jinja2_template(self, template_content: str, context: Dict[str, Any]) -> str` | Render a Jinja2 template with the given context. |
| `render_pyscaffold_template` | `render_pyscaffold_template(self, template_content: str, context: Dict[str, Any]) -> str` | Render a PyScaffold template with the given context. |
| `get_all_templates` | `get_all_templates(self) -> Dict[str, str]` | Get all templates for this extension. |

### Functions

#### get_extension_template

```python
def get_extension_template(
    template_name: str, 
    extension_name: str, 
    extension_module: Optional[str] = None
) -> str
```

Get a template from an extension's templates directory.

#### Parameters

- `template_name`: Name of the template file without the .template extension
- `extension_name`: Name of the extension
- `extension_module`: Optional module path for the extension, defaults to "khora_kernel_vnext.extensions.<extension_name>.templates"

#### Returns

The template content as a string.

## Config Module

The config module provides utilities for accessing configuration.

### KhoraConfigAccessor

```python
class KhoraConfigAccessor
```

Accessor for Khora configuration in PyScaffold options.

#### Constructor

```python
def __init__(self, opts: ScaffoldOpts)
```

#### Parameters

- `opts`: PyScaffold options containing Khora configuration

#### Properties

| Name | Type | Description |
|------|------|-------------|
| `has_config` | `bool` | Whether Khora configuration is available. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_config_value` | `get_config_value(self, path: List[str], default: Optional[T] = None) -> Optional[T]` | Get a configuration value by path. |
| `is_feature_enabled` | `is_feature_enabled(self, feature_name: str) -> bool` | Check if a feature is enabled in the Khora manifest. |
| `get_path` | `get_path(self, path_name: str, default: str) -> str` | Get a path from the Khora manifest. |
| `get_plugin_config` | `get_plugin_config(self, plugin_name: str) -> Optional[Any]` | Get configuration for a specific plugin. |
| `validate_required_config` | `validate_required_config(self, required_paths: List[List[str]]) -> bool` | Validate that required configuration paths exist. |

### Functions

#### get_config_accessor

```python
def get_config_accessor(opts: ScaffoldOpts) -> KhoraConfigAccessor
```

Create a configuration accessor from PyScaffold options.

#### Parameters

- `opts`: PyScaffold options containing Khora configuration

#### Returns

A KhoraConfigAccessor instance.

## Utils Module

The utils module provides utility functions for common tasks.

### Functions

#### ensure_directory

```python
def ensure_directory(path: Union[str, Path]) -> Path
```

Create a directory if it doesn't exist.

#### Parameters

- `path`: Path to the directory to create

#### Returns

Path to the created directory.

#### copy_directory_structure

```python
def copy_directory_structure(source_dir: Path, target_dir: Path, ignore_patterns: List[str] = None) -> None
```

Copy a directory structure.

#### Parameters

- `source_dir`: Source directory to copy from
- `target_dir`: Target directory to copy to
- `ignore_patterns`: Optional list of glob patterns to ignore

#### safe_run_command

```python
def safe_run_command(
    command: List[str],
    cwd: Optional[Path] = None,
    check: bool = False,
    capture_output: bool = False
) -> subprocess.CompletedProcess
```

Safely run a shell command.

#### Parameters

- `command`: Command to run as a list of strings
- `cwd`: Optional working directory
- `check`: Whether to raise an exception if the command fails
- `capture_output`: Whether to capture command output

#### Returns

A subprocess.CompletedProcess instance.

#### snake_to_camel

```python
def snake_to_camel(snake_str: str) -> str
```

Convert a snake_case string to camelCase.

#### Parameters

- `snake_str`: String in snake_case

#### Returns

String in camelCase.

#### snake_to_pascal

```python
def snake_to_pascal(snake_str: str) -> str
```

Convert a snake_case string to PascalCase.

#### Parameters

- `snake_str`: String in snake_case

#### Returns

String in PascalCase.

#### camel_to_snake

```python
def camel_to_snake(camel_str: str) -> str
```

Convert a camelCase string to snake_case.

#### Parameters

- `camel_str`: String in camelCase or PascalCase

#### Returns

String in snake_case.

#### store_value_in_opts

```python
def store_value_in_opts(opts: ScaffoldOpts, key: str, value: Any) -> None
```

Store a value in PyScaffold opts.

#### Parameters

- `opts`: PyScaffold options
- `key`: Key to store the value under
- `value`: Value to store

#### get_nested_value

```python
def get_nested_value(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any
```

Access nested values in dictionaries.

#### Parameters

- `data`: Dictionary to access
- `keys`: List of keys to traverse
- `default`: Default value to return if the path doesn't exist

#### Returns

The value at the given path, or the default value if the path doesn't exist.

#### sanitize_filename

```python
def sanitize_filename(filename: str) -> str
```

Sanitize a string for use as a filename.

#### Parameters

- `filename`: String to sanitize

#### Returns

Sanitized filename.

## PyScaffold Integration

### Action Pipeline

The PyScaffold action pipeline is the core of PyScaffold's extension system. Khora extends this pipeline with additional actions and hooks.

#### Structure and Options

The PyScaffold action pipeline operates on two key data structures:

1. `Structure`: A dictionary mapping file paths to (content, operation) tuples, representing the files to be created.
2. `ScaffoldOpts`: A dictionary-like object containing configuration options for the scaffolding process.

Every action in the pipeline takes these two objects as input and returns modified versions as output:

```python
def my_action(struct: Structure, opts: ScaffoldOpts) -> Tuple[Structure, ScaffoldOpts]:
    # Modify struct and/or opts
    return struct, opts
```

#### Common Operations

When adding files to the structure, you can specify operations to control how files are written:

```python
from pyscaffold.operations import no_overwrite, create

# Don't overwrite if the file exists
struct["file.txt"] = ("content", no_overwrite())

# Always create the file, overwriting if necessary
struct["file2.txt"] = ("content", create())
```

### Entry Points

Khora extensions are registered with PyScaffold via entry points in the `pyproject.toml` file:

```toml
[project.entry-points."pyscaffold.cli"]
my_extension = "my_package.my_module:MyExtension"
```

This makes the extension available to the PyScaffold CLI and to the Khora Kernel.
