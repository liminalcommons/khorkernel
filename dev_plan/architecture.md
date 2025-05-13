# Khora Kernel: Architecture Diagram

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