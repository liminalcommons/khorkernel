# Khora Kernel

## Overview

Khora Kernel is a powerful scaffolding system designed to simplify and enhance the creation of Khora projects. Built upon PyScaffold, it enables the quick setup of well-structured Python projects with pre-configured components. Khora Kernel promotes a streamlined development workflow through its extensible architecture, a machine-readable context model, automatic knowledge graph generation, standard pre-built components, and environment-specific configurations.

## Features

*   **Rapid Project Scaffolding:** Quickly generate new Khora projects with a standardized structure.
*   **Extensible Architecture:** A robust plugin system (extensions) allows for the addition of features like FastAPI integration, Docker support, CI/CD pipelines, and more.
*   **Environment-Specific Configurations:** Manage different configurations for various environments (e.g., development, testing, production) seamlessly.
*   **Machine-Readable Context:** Automatically generates a `.khora/context.yaml` file containing project metadata, facilitating automation and integration.
*   **Knowledge Graph Generation:** Automatically creates a knowledge graph from the project's content, offering insights and aiding documentation.
*   **Comprehensive CLI:** A user-friendly command-line interface (`khora`) for managing projects.
*   **Developer SDK:** Provides tools and guidelines for creating custom extensions to tailor Khora Kernel to specific needs.

## Getting Started

### Prerequisites

*   Python 3.12 or higher.

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    ```
2.  Navigate to the project directory:
    ```bash
    cd khora-kernel
    ```
3.  Install the package in editable mode (which includes all core and development dependencies):
    ```bash
    pip install -e .
    ```

    Core dependencies include: `pyyaml`, `jinja2`, `typer`, `pyscaffold`, `pydantic`, `click`, `tomlkit`.
    Development dependencies include: `pytest`, `hatchling`, `ruff`, `black`, `mypy`, `pre-commit`.
    All dependencies are listed in the [`pyproject.toml`](khora-kernel/pyproject.toml:0) file.

## Usage

Khora Kernel is primarily used via its command-line interface, `khora`.

## CLI Commands

The `khora` CLI provides several commands to manage your projects:

*   **`khora create <project-name>`**:
    *   Scaffolds a new Khora project.
    *   Example: `khora create my-awesome-project`
*   **`khora list-extensions`**:
    *   Lists all available extensions that can be added to a project.
*   **`khora health`**:
    *   Performs health checks on the Khora Kernel environment or a specific project.
*   **`khora inspect`**:
    *   Provides detailed information about a Khora project's configuration and structure.
*   **`khora validate-manifest`**:
    *   Validates the project's manifest file (`.khora/context.yaml`).

## Extensibility

Khora Kernel's functionality can be extended using a plugin system. Extensions can add new features, commands, or integrations.

*   **Activating Extensions:** Extensions are typically activated during project creation using flags.
    *   Example: `khora create my-project --fastapi` (to include the FastAPI extension).
*   **Listing Extensions:** Use `khora list-extensions` to see all available plugins.

## Environment-Specific Configurations

Manage different settings for various deployment or development environments using the [`pyproject.toml`](khora-kernel/pyproject.toml:0) file.

*   Configurations are defined under the `[tool.khora.env.<env_name>]` section.
*   Activate a specific environment configuration using the `--khora-env <env_name>` flag with `khora` commands.

## Developer SDK

Khora Kernel includes a Software Development Kit (SDK) for creating custom extensions. This allows developers to build new functionalities and integrate them seamlessly into the Khora ecosystem. Refer to the SDK documentation for more details on developing your own extensions.
