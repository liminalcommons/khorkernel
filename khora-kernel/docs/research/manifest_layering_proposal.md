# Manifest Layering/Inheritance Proposal

## Overview

This document explores the feasibility and potential approaches for implementing layered manifest configuration in Khora Kernel vNext. The goal is to allow for more flexible and modular configuration that can be inherited and overridden at different levels.

## Problem Statement

Currently, Khora projects have a single configuration point in `pyproject.toml` under the `[tool.khora]` section. This approach works well for simple projects but has limitations:

1. No ability to share common configuration across multiple projects
2. Limited support for environment-specific overrides (dev, test, prod)
3. No inheritance model for organizational defaults
4. Difficulty managing complex configurations that span multiple files or repositories

## Existing Patterns

Several frameworks and tools provide configuration layering mechanisms that could serve as inspiration:

### 1. Spring Profiles (Java)

Spring Framework supports environment-specific configuration through profiles:
- Base configuration is defined in `application.properties`
- Environment-specific overrides in `application-{profile}.properties`
- Profiles activated via command line or environment variables

### 2. Python Settings Management

Libraries like Dynaconf and Python-Decouple support:
- Hierarchical configuration from multiple sources
- Environment-specific overrides
- Secret management
- Configuration layering from files, environment variables, etc.

### 3. Docker Compose

Docker Compose uses a simple inheritance model:
- Base configuration in `docker-compose.yml`
- Overrides in `docker-compose.override.yml`
- Extended with environment-specific files like `docker-compose.prod.yml`

### 4. Terraform Workspaces

Terraform uses workspaces and variable files:
- Base configuration in `main.tf`
- Environment-specific variables in `{env}.tfvars`
- Modules system for reusable configuration blocks

## Proposed Approaches

### Approach 1: Environment-Specific Overrides

```
[tool.khora]
# Base configuration
features = { docker = true }

[tool.khora.env.dev]
# Development environment overrides
features = { docker = true, ci_github_actions = false }

[tool.khora.env.prod]
# Production environment overrides
features = { docker = true, ci_github_actions = true }
```

**Pros:**
- Simple to implement and understand
- Works with existing TOML structure
- Clean separation of common vs. environment-specific settings

**Cons:**
- Limited to a single file
- No organizational defaults across projects
- No dynamic inheritance

### Approach 2: External Configuration Files

Support for loading external configuration files that are merged with the local configuration:

```toml
[tool.khora]
# Base configuration
extends = ["~/khora-defaults.toml", "./khora-team-defaults.toml"]
features = { docker = true }
```

**Pros:**
- Support for organizational defaults
- Configuration sharing across projects
- More modular configuration

**Cons:**
- More complex implementation
- Need to define merging rules
- Potential performance impact when loading multiple files

### Approach 3: Layered Configuration with Priority

A more sophisticated approach with explicit layering and priorities:

```toml
[tool.khora]
layers = [
    { source = "organization", path = "~/khora-org-defaults.toml", priority = 10 },
    { source = "team", path = "./khora-team-defaults.toml", priority = 20 },
    { source = "project", priority = 30 },  # Current file
    { source = "environment", priority = 40 }  # Environment-specific overrides
]
```

**Pros:**
- Highly flexible
- Clear priority order
- Support for multiple inheritance sources
- Most powerful approach for complex configurations

**Cons:**
- Most complex to implement
- Might be overkill for simple projects
- Requires more documentation and user education

## Implementation Considerations

### 1. Loading Mechanism

For any layered configuration approach, we need a mechanism to load and merge configurations:

```python
def load_layered_config(base_config):
    # Find and load all configuration layers
    layers = discover_config_layers(base_config)
    
    # Sort by priority
    sorted_layers = sort_by_priority(layers)
    
    # Merge configurations
    final_config = {}
    for layer in sorted_layers:
        deep_merge(final_config, layer)
    
    return final_config
```

### 2. Merging Rules

Clear rules for merging configurations are essential:

- Simple scalar values (strings, numbers) are overwritten by higher-priority layers
- Lists can be appended, prepended, or replaced based on markers
- Dictionaries are deep-merged by default
- Special merge operators for complex cases (e.g., `+=` for additions)

### 3. Schema Validation

With more complex configuration, schema validation becomes more important:

- Validate the final merged configuration against a JSON schema
- Provide clear error messages for invalid configurations
- Support for defaults based on the schema

## Recommended Approach

Based on the analysis, we recommend a hybrid approach:

1. Start with **Approach 1** (Environment-Specific Overrides) as a simpler first step
2. Add support for **Approach 2** (External Configuration Files) in a later release
3. Consider **Approach 3** (Layered Configuration with Priority) only if needed based on user feedback

This incremental approach balances immediate utility with future flexibility.

## Proof of Concept Implementation

```python
import tomlkit
from pathlib import Path

def load_config_with_env_overrides(config_path, environment=None):
    """Load configuration with environment-specific overrides."""
    with open(config_path, "r") as f:
        config = tomlkit.parse(f.read())
    
    # Check if we have Khora configuration
    if "tool" not in config or "khora" not in config["tool"]:
        return config
    
    khora_config = config["tool"]["khora"]
    
    # Apply environment overrides if specified
    if environment and "env" in khora_config and environment in khora_config["env"]:
        env_overrides = khora_config["env"][environment]
        deep_merge(khora_config, env_overrides)
        
        # Remove the env section to avoid confusion
        if "env" in khora_config:
            del khora_config["env"]
    
    return config

def deep_merge(base, override):
    """Deep merge override dict into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
```

## Next Steps

1. Implement environment-specific overrides as a first step
2. Gather user feedback on the approach
3. Develop comprehensive documentation and examples
4. Consider expanded layering capabilities based on user needs

## Conclusion

Layered configuration will provide significant benefits for complex Khora projects, particularly in enterprise environments with shared standards and multiple deployment environments. Starting with a simple approach and evolving based on user feedback will ensure we deliver immediate value while laying groundwork for more advanced capabilities.
