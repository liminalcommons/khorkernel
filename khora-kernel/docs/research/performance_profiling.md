# Performance Profiling of Scaffolding Process

## Introduction

This document provides an analysis of the performance characteristics of the Khora Kernel scaffolding process. The goal is to identify bottlenecks and opportunities for optimization to improve the overall user experience, particularly for complex projects with multiple extensions.

## Profiling Methodology

For this analysis, we used the following profiling tools and methodology:

1. **cProfile**: To collect detailed execution statistics
2. **SnakeViz**: For visualization of profiling results
3. **Timeit**: For focused measurement of specific components
4. **Custom instrumentation**: Added timing decorators to key functions

The test environment consists of:

- macOS 12.6 (Intel i9)
- Python 3.10.8
- Khora Kernel v0.4.0-dev
- All common extensions activated (docker, ci_github_actions, fastapi_scaffold, kg, playwright, terraform, docs)

## Profiling Results

### Overall Execution Time

The overall scaffolding process for a standard project with all extensions enabled takes approximately 2.57 seconds. This breaks down as follows:

| Phase | Time (s) | % of Total |
|-------|----------|------------|
| Initialization | 0.12 | 4.7% |
| Extension Activation | 0.95 | 37.0% |
| Action Processing | 1.35 | 52.5% |
| Finalization | 0.15 | 5.8% |
| **Total** | **2.57** | **100%** |

### Hotspots

The profiling identified several performance hotspots:

1. **Template Rendering** (0.68s, 26.5% of total): Particularly the Jinja2 template processing for complex templates like docker-compose.yml and GitHub Actions workflows.

2. **File Operations** (0.53s, 20.6% of total): Creating and writing files, especially for large or numerous files.

3. **Extension Activation** (0.41s, 16.0% of total): The overhead of initializing and activating multiple extensions.

4. **Action Processing Framework** (0.33s, 12.8% of total): The overhead in PyScaffold's action processing system.

5. **Config Processing** (0.24s, 9.3% of total): Parsing and validating configuration values.

### Call Graph Analysis

The call graph shows that the most intensive call paths are:

1. `create_project → process_extensions → activate_extension → activate → render_template`
2. `create_project → process_extensions → activate_extension → activate → create_file`
3. `create_project → process_extensions → activate_extension → _load_requirements`

## Optimization Opportunities

Based on the profiling results, we've identified the following optimization opportunities:

### 1. Template Rendering Optimization

The Jinja2 template rendering shows significant overhead. Optimizations include:

- **Template Caching**: Cache compiled templates between renders
- **Lazy Template Loading**: Only load templates when actually needed
- **Simplified Templates**: Reduce complexity in the largest templates

**Estimated Impact**: 15-20% improvement in overall scaffolding time

**Implementation Approach**:
```python
_template_cache = {}

def render_template_optimized(template_str, context):
    """Optimized template rendering with caching."""
    template_hash = hash(template_str)
    if template_hash not in _template_cache:
        _template_cache[template_hash] = jinja2.Template(template_str)
    
    return _template_cache[template_hash].render(**context)
```

### 2. Parallel File Operations

File I/O operations are inherently I/O-bound and can benefit from parallelization:

- **Batch File Creation**: Group file writes into batches
- **Parallel File Creation**: Use `concurrent.futures` for parallel execution
- **Asynchronous I/O**: For larger files, consider async I/O

**Estimated Impact**: 10-15% improvement in overall scaffolding time

**Implementation Approach**:
```python
from concurrent.futures import ThreadPoolExecutor

def create_files_in_parallel(file_specs, max_workers=4):
    """Create multiple files in parallel."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(create_file, path, content): path 
            for path, content in file_specs
        }
        
        for future in as_completed(futures):
            path = futures[future]
            try:
                future.result()
                logger.debug(f"Created file: {path}")
            except Exception as exc:
                logger.error(f"Error creating file {path}: {exc}")
```

### 3. Lazy Extension Activation

Extensions that aren't actively used in a project still incur activation overhead:

- **Conditional Activation**: Only activate extensions when needed based on configuration
- **Lazy Loading**: Defer loading extension modules until activation
- **Extension Profiling**: Add per-extension timing for better targeting

**Estimated Impact**: 5-10% improvement in overall scaffolding time

**Implementation Approach**:
```python
def get_enabled_extensions(opts):
    """Get only the extensions that are actually enabled."""
    enabled = []
    
    if opts.get("khora_features", {}).get("docker", False):
        enabled.append("docker")
    
    if opts.get("khora_features", {}).get("ci_github_actions", False):
        enabled.append("ci_github_actions")
    
    # ... other features
    
    return enabled

def activate_extensions(project, opts):
    """Activate only enabled extensions."""
    enabled_extensions = get_enabled_extensions(opts)
    
    for ext_name in enabled_extensions:
        ext = load_extension(ext_name)
        ext.activate(project, opts)
```

### 4. Action Processing Optimization

The action processing framework in PyScaffold has unnecessary overhead:

- **Simplified Action Model**: Reduce the complexity of the action pipeline
- **Direct Function Calls**: Replace indirect dispatch with direct calls where possible
- **Action Batching**: Group similar actions for more efficient processing

**Estimated Impact**: 5-10% improvement in overall scaffolding time

**Implementation Approach**:
```python
def process_actions_optimized(actions, opts):
    """Optimized action processing with batching."""
    # Group actions by type
    action_groups = {}
    for action, action_opts in actions:
        if action not in action_groups:
            action_groups[action] = []
        action_groups[action].append(action_opts)
    
    # Process action groups
    for action_type, opts_list in action_groups.items():
        if action_type == "create":
            create_files_in_parallel(opts_list)
        elif action_type == "ensure":
            ensure_dirs_in_parallel(opts_list)
        else:
            # Handle other action types individually
            for opt in opts_list:
                process_action(action_type, opt)
```

### 5. Configuration Processing

Configuration processing shows significant overhead:

- **Schema Validation Optimization**: Use a more efficient schema validator
- **Configuration Caching**: Cache validated configs
- **Reduced Config Copying**: Minimize deep copies of configuration objects

**Estimated Impact**: 3-5% improvement in overall scaffolding time

**Implementation Approach**:
```python
_config_cache = {}

def validate_config(config, schema_id=None):
    """Validate config with caching."""
    cache_key = (id(config), schema_id)
    if cache_key in _config_cache:
        return _config_cache[cache_key]
    
    # Perform validation
    result = _do_validate_config(config, schema_id)
    
    # Cache the result
    _config_cache[cache_key] = result
    return result
```

## Implementation Plan

Based on the above findings, we recommend the following implementation plan:

1. **Phase 1 - Template Rendering Optimization**:
   - Implement template caching
   - Refactor the largest templates
   - Measure impact

2. **Phase 2 - File Operations Optimization**:
   - Implement parallel file creation
   - Benchmark different batch sizes
   - Optimize for common file patterns

3. **Phase 3 - Extension System Improvements**:
   - Implement conditional activation
   - Add extension-specific profiling
   - Optimize extension loading

4. **Future Phases**:
   - Action processing optimization
   - Configuration processing improvements
   - Consider more fundamental architecture changes

## Conclusion

The profiling results show that Khora Kernel's scaffolding process has several opportunities for performance optimization. The largest gains can be achieved by focusing on template rendering and file operations, which together account for nearly half of the overall execution time.

The proposed optimizations could potentially reduce scaffolding time by 30-40% for complex projects, significantly improving the user experience. We recommend implementing these optimizations incrementally, starting with the highest-impact changes, and continuously measuring performance to validate improvements.

## Appendix: Detailed Profiling Data

```
         2800004 function calls (2710001 primitive calls) in 2.568 seconds

   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    2.568    2.568 api.py:27(create_project)
        1    0.022    0.022    2.446    2.446 api.py:94(process_extensions)
       45    0.008    0.000    1.351    0.030 structure.py:105(create_structure)
      108    0.056    0.001    0.679    0.006 templates.py:58(render_template)
      159    0.065    0.000    0.531    0.003 operations.py:41(create)
       45    0.010    0.000    0.411    0.009 extension.py:74(activate)
      108    0.033    0.000    0.330    0.003 actions.py:118(process_action)
       23    0.015    0.001    0.242    0.011 config.py:87(validate_config)
...
```

## References

1. Python Profilers Documentation: https://docs.python.org/3/library/profile.html
2. PyScaffold Documentation: https://pypi.org/project/PyScaffold/
3. Jake VanderPlas, "Python Data Science Handbook: Tools and Techniques for Developers", Chapter on Performance Profiling
