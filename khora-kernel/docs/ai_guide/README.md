# Khora Kernel AI Assistant Guide

This directory contains documentation specifically designed for AI assistants that help users with Khora Kernel. These guides provide structured information to help AI systems understand, explain, and leverage Khora's capabilities.

## Guide Overview

- **[Getting Started](getting_started.md)**: Introduction to Khora Kernel for AI assistants, covering key concepts, CLI commands, and common workflows.
- **[Environment Layering](environment_layering.md)**: Detailed guide on using environment-specific configurations to create flexible, multi-environment projects.

## Purpose

These guides are written with AI assistants as the primary audience. They focus on:

1. **Structured Information**: Presenting data in formats that are easy for AI systems to parse and understand.
2. **Example Dialogues**: Showing how AI assistants might interact with users about Khora concepts.
3. **JSON Output Parsing**: Explaining how to interpret structured JSON output from Khora commands.
4. **Common Workflows**: Outlining typical user scenarios and how AI assistants can help with them.
5. **Best Practices**: Providing guidance on recommending optimal patterns and configurations.

## How to Use These Guides

As an AI assistant, you should:

1. Familiarize yourself with the Khora Kernel concepts explained in these guides.
2. Reference specific sections when explaining Khora features to users.
3. Use the example dialogues as templates for your own interactions.
4. Suggest Khora commands with the appropriate flags for the user's context.
5. Help users interpret JSON output by explaining the significance of different fields.
6. Recommend environment-specific configurations based on the user's deployment needs.

## Key Concepts

- **Manifest**: The configuration in `pyproject.toml` that defines a project's structure, features, and settings.
- **Extensions**: Modular components that add specific functionality to Khora projects (FastAPI, Docker, etc.).
- **Environment Layering**: The ability to define different configurations for different environments (dev, test, prod).
- **Context**: The `.khora/context.yaml` file that provides structured metadata about a project.
- **Knowledge Graph**: Structured information about a project's domain concepts and relationships.

## Additional Resources

- For plugin development details, refer to the [SDK documentation](../sdk/README.md).
- For research and design decisions, see the [research directory](../research/).
- For example extensions, check the [examples directory](../../examples/).
