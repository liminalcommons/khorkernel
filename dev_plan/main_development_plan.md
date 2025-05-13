# Khora Kernel: Main Development Plan

## Overview
Khora Kernel is a powerful scaffolding system designed to streamline the creation and management of software projects. It leverages a flexible extension-based architecture to support various project types, technologies, and development practices.

## Core Architecture
The core architecture of Khora Kernel is detailed in the diagram below and in the [Architecture Document](architecture.md).

```mermaid
graph TD
    User["User"] --> CLI["Khora CLI"]
    CLI -- Invokes --> ConfigMgr["Configuration Manager"]
    CLI -- Initiates --> ScaffoldEngine["Scaffolding Engine"]
    ConfigMgr -- Provides Config --> ScaffoldEngine
    ConfigMgr -- Provides Config --> KhoraExtensions["Khora Extensions (Core & Plugins)"]
    ScaffoldEngine -- Manages/Loads/Runs --> ExtMgr["Extension Manager"]
    ExtMgr -- Loads/Runs --> KhoraExtensions
    KhoraExtensions -- Use APIs --> ScaffoldEngine
    KhoraExtensions -- Read/Write Metadata --> CtxMgr["Context Manager"]
    CtxMgr -- Manages --> ContextFile["`.khora/context.yaml`"]
    ScaffoldEngine -- Writes Project --> FileSystem["Generated Project Files"]
    ContextFile -- Stored on --> FileSystem