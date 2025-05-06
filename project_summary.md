# Khora Kernel Project Summary

## Overview
Khora Kernel is a drop-in folder that provides instant project scaffolding with best practices. It's designed for both solo developers and teams working with AI partners, providing Sprint-0 backlog, CI configuration, Docker stack, security gates, and a machine-readable context graph in under 5 minutes.

## Current Version: 1.0.6 (May 6, 2025)

## Key Features
- GitHub Issue & PR templates
- CI pipelines for lint, typecheck, and security scans
- Docker Compose stack (API/Worker/DB)
- Knowledge Graph generator
- AI Context File generation
- Pre-commit hooks
- Lite-Mode for laptop development
- Plugin system with support for terraform, playwright, etc.
- Security gates and scanning

## Recent Development History

### Version 1.0.6 (Current)
- Added version consistency checks across documentation and code
- Enhanced self-test script with additional validation rules
- Updated documentation in USER_GUIDE and AI_USER_GUIDE
- Updated version references from 1.0.5 → 1.0.6 across the repository
- Improved knowledge graph rendering with better visualization options
- Optimized CI workflows for faster builds and deployments
- Fixed version inconsistency between README and VERSION file
- Fixed minor formatting issues in generated context files
- Fixed security scan false positives in dependency checks

### Version 1.0.5
- Updated version constants and headers from 1.0.4 → 1.0.5
- Regenerated context and badges to embed kernel_version: 1.0.5
- Removed duplicate pre-commit config
- Added CHANGELOG.md following Keep-a-Changelog format
- Improved human/AI documentation parity

### Version 1.0.4
- Fixed Jinja Template Error in docker-build.j2
- Fixed Context Generation for handling plugins in the manifest
- Enhanced Knowledge Graph with new concept and rule tags
- Updated JSON files and context with new KG entries

## AI Integration
The kernel automatically generates and maintains context files crucial for AI partners:
- `.khora/context.yaml` - Machine-readable project capsule
- `kg/concepts.json` - Domain vocabulary extracted from Markdown
- `kg/rules.json` - Business rules extracted from Markdown
- `docker-compose.yml` - Runtime service graph
- `.github/workflows/*` - CI rules & process definitions

An LLM agent can load `.khora/context.yaml` to instantly understand the project's structure, features, and conventions without parsing vast amounts of code or documentation.
