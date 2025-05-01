# Khora Kernel Plugins

Khora Kernel plugins extend the functionality of the bootstrap process, adding specialized tooling, workflows, and scaffolding based on your project needs.

## Available Plugins

The following plugins are available:

### 1. Terraform

**Description**: Adds infrastructure-as-code scaffolding using Terraform, with templates for AWS deployment.

**Features**:
- Creates basic Terraform files in `infra/terraform/`
- Adds CI/CD workflows for Terraform validation and planning
- Includes sample configurations for AWS ECS and RDS
- Generates documentation

**Usage**: 
1. Enable in KERNEL_MANIFEST.yaml:
   ```yaml
   plugins:
     - terraform
   ```
2. Run bootstrap script:
   ```bash
   python .khorkernel/scripts/bootstrap_backlog.py
   ```
3. Initialize Terraform:
   ```bash
   cd infra/terraform
   terraform init
   ```

### 2. Playwright

**Description**: Adds browser testing capabilities with Playwright for automated UI testing.

**Features**:
- Sets up Playwright test directory structure in `tests/ui/`
- Adds GitHub workflow for running UI tests
- Includes sample test fixtures and configuration
- Configures screenshot and video capture

**Usage**:
1. Enable in KERNEL_MANIFEST.yaml:
   ```yaml
   plugins:
     - playwright
   ```
2. Run bootstrap script:
   ```bash
   python .khorkernel/scripts/bootstrap_backlog.py
   ```
3. Install Playwright dependencies:
   ```bash
   pip install playwright
   playwright install
   ```

## Creating Custom Plugins

Creating your own plugin is straightforward:

1. Create a new directory in `.khorkernel/plugins/YOUR_PLUGIN_NAME/`
2. Add a `plugin.py` file with a `render` function that will be called during bootstrap:

```python
def render(project_root, manifest, jinja_env):
    """
    Main entry point for the plugin.
    
    Args:
        project_root (pathlib.Path): Path to the project root
        manifest (dict): The parsed KERNEL_MANIFEST.yaml contents
        jinja_env (jinja2.Environment): Configured Jinja environment
    """
    # Your plugin logic here
    # Example: Creating files, rendering templates, etc.
    print(f"Running YOUR_PLUGIN_NAME plugin...")
    
    # Example: Create a directory
    output_dir = project_root / "your" / "custom" / "path"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Example: Render a template
    if (kernel_dir / "plugins" / "YOUR_PLUGIN_NAME" / "template.j2").exists():
        template = jinja_env.get_template(f"plugins/YOUR_PLUGIN_NAME/template.j2")
        output = template.render(**manifest)
        (output_dir / "output_file.txt").write_text(output)
```

3. Add any templates or static files your plugin needs
4. Enable your plugin in KERNEL_MANIFEST.yaml:
   ```yaml
   plugins:
     - YOUR_PLUGIN_NAME
   ```

## Plugin API Reference

The plugin interface is intentionally simple:

- **render(project_root, manifest, jinja_env)**: Main function called during bootstrap
  - **project_root**: Absolute path to the project root directory (pathlib.Path)
  - **manifest**: Dict containing the parsed KERNEL_MANIFEST.yaml
  - **jinja_env**: Configured Jinja2 Environment with loaders set up

Plugins should handle errors gracefully and provide clear log messages for the user.