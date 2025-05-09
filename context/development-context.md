# Khora Kernel vNext: Context Summary for Development Session

**Objective:** This document summarizes the current state, goals, architecture, target application drivers, and next steps for the 'Khora Kernel vNext' project. It provides context for continuing development, particularly for AI agents.

### 1. Khora Kernel vNext: Project Overview

*   **Project Name:** Khora Kernel vNext
*   **Core Goal:** Develop a modular, extensible scaffolding tool, built upon the PyScaffold framework, designed for rapid Python project setup. It emphasizes integrating development best practices (linting, testing, security, CI/CD, Docker), strong AI collaboration support via a machine-readable `context.yaml` and Knowledge Graph (KG) integration, and a streamlined developer experience.
*   **Target Architecture:** Modular Micro-Kernel with Typed Plugin Ecosystem (adapting PyScaffold). Core logic resides in a minimal kernel engine, with most functionality implemented as discrete PyScaffold extensions (plugins).

### 2. Target Application Driver (Khora Live Transcriber System)

The development of Khora Kernel vNext is primarily driven by the need to effectively bootstrap and support projects like the "Khora Live Transcriber". Key aspects of this target system influencing kernel requirements include:

*   **Vision Summary:** (from `VISION.md`) The Khora system aims to transform raw conversational data (like transcripts) into structured insights and artifacts (summaries, actions) using AI synthesis (Claude). It envisions a "conscious participating field" integrated tightly with user workspaces (initially Coda) for capturing, processing, and leveraging conversational intelligence.
*   **Key Architectural Components (Target System):** (from `ARCHITECTURE.md`)
    *   FastAPI API Server
    *   Typer CLI Handler
    *   Core `TranscriptionService`
    *   Audio Input Handler (e.g., `sounddevice`)
    *   Deepgram Client (Streaming API)
    *   Pydantic Settings Configuration Manager
    *   File Output Writer
    *   Structured Logging System (`structlog` recommended)
    *   Dependency Injection Container (`python-dependency-injector`)
    *   (Future) PostgreSQL Database + SQLAlchemy + Alembic
    *   (Future) Background Task processing (initially FastAPI `BackgroundTasks`)
*   **Architectural Drivers (Target System influencing Kernel):**
    *   Need for separate API (`FastAPI`) and CLI (`Typer`) entry points.
    *   Requirement for robust configuration management (`pydantic-settings`, `.env`).
    *   Use of Dependency Injection (`python-dependency-injector`).
    *   Emphasis on structured JSON logging (`structlog`).
    *   Plan for future PostgreSQL/SQLAlchemy/Alembic integration.
    *   Initial deployment via local Python/`uv` environments, necessitating clear dependency management (`uv`) and Docker support for containerization.
    *   Adoption of a Monorepo strategy (`ADR-001` referenced in `ARCHITECTURE.md`).
    *   Need for standard best practices: Testing (Pytest), Linting/Formatting (Ruff/Black), Type Checking (MyPy).

### 3. Current Kernel Development Phase:

*   **Focus:** Completing the Minimum Viable Kernel (MVK - v0.1).
*   **MVK Goal Alignment:** The MVK aims to generate the foundational elements required by the Khora Live Transcriber's initial architecture:
    *   Basic Python project structure suitable for the Monorepo.
    *   FastAPI application skeleton (`main.py`, `requirements.txt`, `Dockerfile` for the API component).
    *   Minimal `docker-compose.yml` to run the API service.
    *   Basic CI workflow (`ci.yml`) for linting/testing.
    *   Essential pre-commit hooks (`.pre-commit-config.yaml`).
    *   Initial `context.yaml` capturing manifest configurations for AI awareness.

### 4. Kernel Development Plan Status (`phase1.json` Summary):

The MVK v0.1 development is tracked in `TODO/phase1.json`.

*   **Structure:** Organised into MVK feature/task tickets (`MVK-*`), Fix tickets (`FIX-*`), and Test verification tickets (`MVK-TEST-*`).
*   **Key Completed Tickets:**
    *   `MVK-META-01`: Kernel dev environment setup.
    *   `MVK-CORE-01`: Manifest parsing implementation.
    *   `MVK-CORE-03`: Minimal context file generation logic.
    *   `FIX-TEST-CORE-01`: Fixed manifest parsing unit tests.
    *   `FIX-TEST-CORE-03`: Fixed context generation unit tests.
    *   `FIX-TPL-LOAD`: Fixed template loading paths/names in extensions.
    *   `MVK-TEST-01`: Verified all core extension unit tests pass.
    *   `FIX-INTEG-PUTUP`: Resolved integration test failures related to extension discovery by refactoring tests to use `pyscaffold.api.create_project`.
*   **Pending Verification:**
    *   The feature implementations (`MVK-FEAT-01` to `04`) and core extension activation (`MVK-CORE-02`) are now believed to be working correctly following the fix for `FIX-INTEG-PUTUP`, but require final validation through the end-to-end integration tests.
    *   The primary task remaining for MVK v0.1 completion is `MVK-TEST-02`.

### 5. Guiding Principles & Scopes:

*   **Key Principles:** Development adheres to Khora principles: AI-Ready Context, Reproducibility, Explicit Configuration, Extensibility, Security by Default, etc.
*   **Four Scopes:** Actively considering the impact on:
    *   **Agentic System:** Via `context.yaml`.
    *   **DevRelSecOps System:** The core output (CI/CD, Docker, hooks).
    *   **Code System (Target Project):** Providing a functional starting point.
    *   **Meta-Evolutionary System:** The kernel's own testability, maintainability, and versioning.

### 6. Immediate Next Step:

*   Execute ticket **`MVK-TEST-02: Testing: Verify Integration Tests for MVK Extensions`**.
    *   This involves running the full integration test suite (specifically `test_mvk_integration.py` and `test_precommit_integration.py`).
    *   These tests utilize the refactored approach (calling `pyscaffold.api.create_project` programmatically) to ensure all MVK extensions (`khora-core`, `fastapi-scaffold`, `khora-docker`, `khora-ci-github-actions`, and implicitly pre-commit) work together correctly to produce the expected project scaffold based on the Khora Live Transcriber MVK fixture configuration.
    *   Successful completion of these tests will validate the functionality of the MVK v0.1 feature set and mark the end of Phase 1. Any failures will indicate remaining bugs in the feature extension implementations that need addressing.