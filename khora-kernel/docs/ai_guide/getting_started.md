# Getting Started with Khora Kernel for AI Assistants

This guide is specifically designed to help AI assistants understand how to use Khora Kernel effectively when assisting users with project scaffolding, configuration, and maintenance.

## Overview

Khora Kernel is a powerful project scaffolding tool that helps create well-structured Python projects with pre-configured components like FastAPI, Docker, CI/CD, and more. As an AI assistant, you can leverage Khora to help users set up projects that follow best practices with minimal effort.

## Core Concepts

### 1. The Manifest

The `pyproject.toml` file contains a `[tool.khora]` section that serves as the project's manifest. This manifest defines:

- Basic project metadata
- Enabled features and extensions
- Environment-specific configurations
- Paths and customizations

Example manifest:

```toml
[tool.khora]
project_name = "MyAwesomeAPI"
project_description = "A FastAPI service with Docker support"
python_version = "3.11"

[tool.khora.features]
fastapi = true
docker = true
ci_github_actions = true
kg = true

[tool.khora.paths]
api_dir = "src/api"
```

### 2. Environment-Specific Configurations

Khora supports environment-specific overrides through layered configurations:

```toml
[tool.khora.env.dev]
python_version = "3.12"  # Use newer Python in development

[tool.khora.env.dev.features]
docker = false  # Disable Docker in development

[tool.khora.env.prod]
project_description = "Production version of MyAwesomeAPI"

[tool.khora.env.prod.ports]
http = 80  # Use port 80 in production
```

### 3. The Context

After scaffolding, Khora generates a `.khora/context.yaml` file containing structured metadata about the project. This context is particularly valuable for AI assistants to understand the project's configuration, structure, and components.

## Key CLI Commands

As an AI assistant, you'll help users interact with Khora through these commands:

### Creating a Project

```bash
khora create my-project --fastapi --docker --ci-github-actions
```

With environment specification:

```bash
khora create my-project --fastapi --docker --khora-env prod
```

### Checking Project Health

```bash
khora health
```

With JSON output (ideal for AI processing):

```bash
khora health --json-output
```

### Inspecting Project Structure

```bash
khora inspect
```

With JSON output:

```bash
khora inspect --json-output
```

### Validating the Manifest

```bash
khora validate-manifest
```

With environment specification and JSON output:

```bash
khora validate-manifest --khora-env dev --json-output
```

### Listing Available Extensions

```bash
khora list-extensions
```

## Parsing JSON Output

When commands are run with the `--json-output` flag, the output is in a structured format ideal for AI processing:

### Manifest Validation

```json
{
  "valid": true,
  "timestamp": "2025-05-08T22:15:30.123456",
  "manifest": {
    "project_name": "MyProject",
    "python_version": "3.11",
    "features": {
      "fastapi": true,
      "docker": true
    }
  }
}
```

Or when validation fails:

```json
{
  "valid": false,
  "timestamp": "2025-05-08T22:15:30.123456",
  "errors": [
    {
      "loc": ["project_name"],
      "msg": "Field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Health Check

```json
{
  "status": "healthy",
  "timestamp": "2025-05-08T22:15:30.123456",
  "environment": {
    "name": "dev",
    "applied": true
  },
  "checks": [
    {
      "name": "docker_compose",
      "status": "pass",
      "details": "docker-compose.yml is valid"
    },
    {
      "name": "requirements",
      "status": "pass",
      "details": "All required packages are installed"
    }
  ]
}
```

## Understanding context.yaml

The `.khora/context.yaml` file is a gold mine of project information for AI assistants:

```yaml
kernel_version: "0.5.0"
schema_version: "0.5.0"
generated_at: "2025-05-08T22:15:30.123456Z"
project:
  name: "MyAwesomeAPI"
  description: "A FastAPI service with Docker support"
  paths:
    api_dir: "src/api"
features:
  fastapi: true
  docker: true
  ci_github_actions: true
environment:
  name: "prod"
  applied: true
  description: "Production configuration"
components:
  api:
    endpoints:
      - path: "/api/v1/items"
        methods: ["GET", "POST"]
        implementation: "src/api/v1/items.py"
      - path: "/api/v1/items/{item_id}"
        methods: ["GET", "PUT", "DELETE"]
        implementation: "src/api/v1/items.py"
  docker:
    services:
      - name: "api"
        image: "myawesomeapi:latest"
        ports: ["80:8000"]
knowledge_graph:
  concepts:
    - name: "Item"
      properties: ["id", "name", "description"]
      relations: ["belongs_to:User"]
    - name: "User"
      properties: ["id", "username", "email"]
      relations: ["has_many:Item"]
```

## Guiding Users Through Project Configuration

As an AI assistant, you can help users by:

1. **Suggesting appropriate extensions** based on their project needs
2. **Explaining configuration options** in the manifest
3. **Recommending environment-specific settings** for development, testing, and production
4. **Interpreting health and validation results** to identify and fix issues
5. **Exploring the project structure** using the context.yaml to understand components

## Example Assistant Workflows

### 1. Creating a New Project

```
User: "I want to create a new API project with Python."

AI: "I'd recommend using Khora Kernel to scaffold your project with best practices. Let me help you create a FastAPI project with Docker support:

First, let's create the project with:
```bash
khora create my-api-project --fastapi --docker
```

This will set up a complete API project with:
- FastAPI for your API endpoints
- Docker for containerization
- A structured project layout
- Basic endpoint examples
- Required dependencies"
```

### 2. Configuring Environment-Specific Settings

```
User: "I need my app to run on port 80 in production but use the default in development."

AI: "Great use case for Khora's environment layering! Let's modify your pyproject.toml:

```toml
[tool.khora.env.prod]
project_description = "Production version of my API"

[tool.khora.env.prod.ports]
http = 80  # Use standard HTTP port in production
```

Now when you deploy to production, run Khora commands with:
```bash
khora validate-manifest --khora-env prod
```

The generated Docker and API configurations will use port 80 in production, while keeping the default port 8000 in development."
```

### 3. Analyzing Project Health

```
User: "Can you check if my project has any issues?"

AI: "Let me check the health of your Khora project:

```bash
khora health --json-output
```

This shows:
- Your Docker configuration is valid
- All required dependencies are installed
- The API structure follows best practices
- Your CI pipeline is correctly configured

One warning: Your production environment is missing security gates. Consider enabling them with:

```toml
[tool.khora.env.prod.features]
security_gates = true
```"
```

## Best Practices for AI Assistants

1. **Use JSON output when possible** - Always use `--json-output` flags when available to get structured data that's easier to parse programmatically.

2. **Understand environment-specific configurations** - Check if a project uses different environments and use the appropriate `--khora-env` flag when running commands.

3. **Reference the context.yaml** - This file provides extensive metadata about the project structure and can help you understand complex projects quickly.

4. **Validate before suggesting changes** - Use `khora validate-manifest` to check if proposed changes to the manifest are valid before recommending them to users.

5. **Explain Khora concepts to users** - Many users may not be familiar with Khora's full capabilities. Explain concepts like environment layering, extensions, and context generation when suggesting them.
