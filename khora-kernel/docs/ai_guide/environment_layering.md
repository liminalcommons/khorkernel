# Environment-Specific Configuration Layering in Khora

This guide explains how AI assistants can leverage Khora Kernel's environment-specific configuration layering to create more flexible and adaptable projects.

## Overview

Environment-specific configuration layering allows you to define different settings for different environments (development, testing, production) within a single manifest. This powerful feature enables:

- Varying configuration between environments without duplicating the entire manifest
- Adapting project features, settings, and dependencies to the specific needs of each environment
- Creating environment-aware scaffolding that follows best practices automatically

## Manifest Structure for Environment Layering

Environment-specific configurations are defined in `pyproject.toml` using the `[tool.khora.env.<env_name>]` sections, where `<env_name>` is the environment identifier (e.g., "dev", "test", "prod").

### Base Structure

```toml
# Base configuration (applies to all environments)
[tool.khora]
project_name = "MyService"
python_version = "3.11"

[tool.khora.features]
fastapi = true
docker = true
ci_github_actions = true

# Environment-specific overrides
[tool.khora.env.dev]
python_version = "3.12"  # Override specific fields

[tool.khora.env.dev.features]
docker = false  # Disable features in specific environments

[tool.khora.env.prod]
project_description = "Production instance of MyService"

[tool.khora.env.prod.ports]
http = 80  # Add environment-specific settings
```

### Deep Merging Behavior

When an environment is activated, Khora performs a deep merge of the base configuration with the environment-specific configuration:

1. All base settings from `[tool.khora]` are used as the starting point
2. For each key in the environment section, values override matching fields in the base configuration
3. For nested dictionaries (like `features`), a deep merge occurs rather than complete replacement
4. Environment-specific values always take precedence over base values
5. If a field exists only in the environment-specific section, it's added to the merged configuration

## Using Environment-Specific Configurations

### CLI Usage

To use an environment-specific configuration when working with the Khora CLI:

```bash
khora create my-project --fastapi --docker --khora-env prod
```

The `--khora-env` flag can be used with several commands:

```bash
# Validate a manifest for a specific environment
khora validate-manifest --khora-env dev

# Create a project with environment-specific settings
khora create my-service --khora-env prod

# Inspect a project's environment-specific configuration
khora inspect --khora-env test --json-output
```

### Programmatic API Usage

For AI agents using Khora's API directly:

```python
from khora_kernel.sdk import create_project

# Create with environment-specific configuration
create_project(
    project_name="my-service",
    features=["fastapi", "docker"],
    environment="prod"
)
```

## Environment Information in Context

When a project is scaffolded with an environment-specific configuration, the `.khora/context.yaml` file will include information about the active environment:

```yaml
environment:
  name: "prod"  # The name of the active environment
  applied: true  # Confirms environment-specific settings were applied
  description: "Production configuration"  # Optional description
```

This allows AI agents to understand which environment was used when examining an existing project.

## Common Environment-Specific Customizations

As an AI assistant, you can recommend several common patterns for environment layering:

### Development vs. Production

```toml
[tool.khora.env.dev]
# More verbose logging for development
log_level = "DEBUG"
# Use a local database for development
database_url = "sqlite:///dev.db"
# Faster iteration with auto-reload
enable_auto_reload = true

[tool.khora.env.prod]
# Less verbose logging for production
log_level = "WARNING"
# Use a robust database for production
database_url = "postgresql://user:pass@db:5432/prod"
# Don't auto-reload in production
enable_auto_reload = false
# Use standard HTTP port
ports.http = 80
```

### Feature Toggling

```toml
[tool.khora.features]
# Base features for all environments
fastapi = true
docker = true

[tool.khora.env.dev.features]
# Enable development tools
docs = true
debug_toolbar = true
# Disable docker for local development
docker = false

[tool.khora.env.test.features]
# Enable test-specific features
test_coverage = true
mock_services = true

[tool.khora.env.prod.features]
# Enable production features
security_gates = true
performance_monitoring = true
```

### Security Settings

```toml
[tool.khora.env.dev.security]
# Relaxed settings for development
cors_allow_origins = ["*"]
enable_debug_endpoints = true

[tool.khora.env.prod.security]
# Strict settings for production
cors_allow_origins = ["https://myapp.example.com"]
enable_debug_endpoints = false
content_security_policy = "default-src 'self'"
```

## Best Practices for AI Assistants

When helping users with environment-specific configurations:

1. **Start with the base configuration** - Define common settings at the root level
2. **Leverage strategic overrides** - Only override what needs to change in each environment
3. **Use clear environment names** - Stick to common conventions like "dev", "test", "staging", "prod"
4. **Document environment differences** - Add comments explaining why settings differ between environments
5. **Consider validation** - Recommend using `khora validate-manifest --khora-env <env>` to verify each environment works correctly
6. **JSON output for analysis** - Use `--json-output` flags when analyzing environment-specific configurations

## Diagnostic Approach

When helping users troubleshoot environment configuration issues:

1. Check if the environment name is spelled correctly in both the manifest and CLI commands
2. Verify that the environment sections use the correct nesting (`[tool.khora.env.dev.features]`, not `[tool.khora.features.env.dev]`)
3. Examine the merged configuration using `khora validate-manifest --khora-env <env> --json-output`
4. Look for any typos or syntax errors in the environment-specific sections
5. Ensure the environment-specific values are compatible with extension requirements

## Example Dialog

```
User: "I want my app to use SQLite in development but PostgreSQL in production"

AI: "Khora's environment layering is perfect for this. Let's add these configurations to your pyproject.toml:

```toml
[tool.khora.databases]
default = {
  type = "sqlite",
  name = "dev.db"
}

[tool.khora.env.prod.databases]
default = {
  type = "postgresql",
  host = "db",
  port = 5432,
  name = "prod_db",
  user = "app_user"
}
```

When scaffolding with `--khora-env prod`, Khora will generate PostgreSQL configurations for Docker, environment variables, and connection code. With no environment flag, it will use SQLite as the default."
