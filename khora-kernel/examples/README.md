# Khora Kernel Extension Examples

This directory contains example extensions that demonstrate how to use the Khora Kernel SDK to build custom extensions.

## Custom Header Extension

The `custom_extension` directory contains a simple example extension that adds a custom README.md file to generated projects and contributes to the project's context.yaml.

### Features

- Creates a custom README.md based on project configuration
- Contributes component information to context.yaml
- Demonstrates SDK usage patterns

### How to Use

1. Register the extension in your project's `pyproject.toml`:

```toml
[project.entry-points."pyscaffold.cli"]
custom_header = "khora_kernel_vnext.examples.custom_extension:CustomHeaderExtension"
```

2. Create a new project with the extension:

```bash
khora create my-project --custom-header
```

### Implementation Details

The extension demonstrates key SDK components:

- `KhoraExtension`: Base class for extensions
- `create_extension_action`: Factory function for creating extension actions
- `KhoraConfigAccessor`: Safe access to project configuration
- `ContributedComponent`: Creating components for context.yaml

## Building Your Own Extensions

To create your own extension:

1. Create a new Python package with a module containing your extension class
2. Inherit from `KhoraExtension` and implement the required methods
3. Register your actions using the `register` method
4. Add docstrings to make your extension self-documenting
5. Register your extension via entry points in pyproject.toml

See the [SDK Documentation](../docs/sdk/README.md) for detailed information on building extensions.

## Testing Your Extensions

To test your extension, you can:

1. Install your package in development mode: `pip install -e .`
2. Create a test project: `khora create test-project --your-extension`
3. Examine the generated project structure

You can also write unit tests using pytest as demonstrated in `tests/sdk/test_sdk_components.py`.
