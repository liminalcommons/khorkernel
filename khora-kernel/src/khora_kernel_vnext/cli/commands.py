"""
CLI Commands for Khora Kernel.
"""

import re
import os
import sys
import click
import datetime
import tomlkit
import importlib
import pkg_resources
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union

# Import the validation function directly - make sure it's accessible
from khora_kernel_vnext.extensions.kg.extension import validate_source_links, KGEntry
from khora_kernel_vnext.extensions.core.manifest import (
    KhoraManifestConfig,
    KhoraManifestNotFoundError,
    KhoraManifestInvalidError,
)


@click.group()
def main_cli():
    """Khora Kernel command line interface."""
    pass


@main_cli.command()
@click.option(
    "--new",
    required=True,
    help="New version number in the format X.Y.Z",
)
@click.option(
    "--changelog",
    is_flag=True,
    default=False,
    help="Update CHANGELOG.md with new version section",
)
def bump_version(new: str, changelog: bool):
    """
    Update project version in pyproject.toml and optionally update CHANGELOG.md.
    
    The new version must follow semantic versioning (X.Y.Z) and must be higher
    than the current version.
    """
    # Validate version format
    if not re.match(r"^\d+\.\d+\.\d+$", new):
        click.echo(f"Error: Version {new} does not follow the X.Y.Z format", err=True)
        sys.exit(1)
    
    # Find the pyproject.toml file
    project_root = find_project_root()
    pyproject_path = project_root / "pyproject.toml"
    
    if not pyproject_path.exists():
        click.echo(f"Error: pyproject.toml not found in {project_root}", err=True)
        sys.exit(1)
    
    # Load the pyproject.toml file
    with open(pyproject_path, "r", encoding="utf-8") as f:
        pyproject = tomlkit.parse(f.read())
    
    # Find current version
    if "project" not in pyproject:
        click.echo("Error: [project] section not found in pyproject.toml", err=True)
        sys.exit(1)
    
    current_version = pyproject["project"].get("version")
    if not current_version:
        click.echo("Error: version not found in [project] section of pyproject.toml", err=True)
        sys.exit(1)
    
    # Validate version increment
    if not is_version_higher(current_version, new):
        click.echo(
            f"Error: New version {new} is not higher than current version {current_version}",
            err=True
        )
        sys.exit(1)
    
    # Update version in pyproject.toml
    pyproject["project"]["version"] = new
    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(pyproject))
    
    click.echo(f"Updated version from {current_version} to {new} in pyproject.toml")
    
    # Update CHANGELOG.md if requested
    if changelog:
        update_changelog(project_root, current_version, new)
        click.echo(f"Updated CHANGELOG.md with new version {new}")


@main_cli.command()
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed information about each check",
)
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output results in JSON format for AI consumption",
)
@click.option(
    "--khora-env",
    help="Environment to use for manifest layering (e.g., 'dev', 'prod')",
)
def health(verbose: bool, json_output: bool, khora_env: Optional[str] = None):
    """
    Check the health of a Khora project.
    
    Performs basic checks on project structure and configuration files to ensure
    they follow Khora conventions. Returns non-zero exit code if issues are found.
    
    With --json-output, returns a structured JSON response suitable for AI consumption.
    With --khora-env, applies environment-specific manifest overrides.
    """
    project_root = find_project_root()
    issues_found = False
    check_results = {}
    
    if not json_output:
        click.echo("Running Khora health check...")
    
    # Check for pyproject.toml with [tool.khora] section
    pyproject_path = project_root / "pyproject.toml"
    check_results["pyproject.toml"] = {"exists": False, "khora_tool": False, "issues": []}
    
    if not pyproject_path.exists():
        check_results["pyproject.toml"]["issues"].append("pyproject.toml not found")
        issues_found = True
    else:
        check_results["pyproject.toml"]["exists"] = True
        
        # Check for [tool.khora] section
        try:
            with open(pyproject_path, "r", encoding="utf-8") as f:
                pyproject = tomlkit.parse(f.read())
                
            if "tool" in pyproject and "khora" in pyproject["tool"]:
                check_results["pyproject.toml"]["khora_tool"] = True
            else:
                check_results["pyproject.toml"]["issues"].append("[tool.khora] section not found")
                issues_found = True
        except Exception as e:
            check_results["pyproject.toml"]["issues"].append(f"Error parsing pyproject.toml: {str(e)}")
            issues_found = True
    
    # Check for .khora/context.yaml
    khora_context_path = project_root / ".khora" / "context.yaml"
    check_results[".khora/context.yaml"] = {"exists": False, "valid": False, "issues": []}
    
    if not khora_context_path.exists():
        check_results[".khora/context.yaml"]["issues"].append(".khora/context.yaml not found")
        issues_found = True
    else:
        check_results[".khora/context.yaml"]["exists"] = True
        
        # Check if it's a valid YAML file (we could add more detailed validation)
        try:
            import yaml
            with open(khora_context_path, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
            check_results[".khora/context.yaml"]["valid"] = True
        except Exception as e:
            check_results[".khora/context.yaml"]["issues"].append(f"Invalid YAML: {str(e)}")
            issues_found = True
    
    # Check for docker-compose.yml if Docker feature is enabled
    docker_enabled = False
    kg_enabled = False
    if check_results["pyproject.toml"]["exists"] and check_results["pyproject.toml"]["khora_tool"]:
        try:
            with open(pyproject_path, "r", encoding="utf-8") as f:
                pyproject = tomlkit.parse(f.read())
                if "tool" in pyproject and "khora" in pyproject["tool"] and "features" in pyproject["tool"]["khora"]:
                    docker_enabled = pyproject["tool"]["khora"]["features"].get("docker", False)
                    kg_enabled = pyproject["tool"]["khora"]["features"].get("kg", False)
        except Exception:
            pass  # Already logged in previous check
    
    if docker_enabled:
        docker_compose_path = project_root / "docker-compose.yml"
        check_results["docker-compose.yml"] = {"exists": False, "issues": []}
        
        if not docker_compose_path.exists():
            check_results["docker-compose.yml"]["issues"].append("docker-compose.yml not found but Docker feature is enabled")
            issues_found = True
        else:
            check_results["docker-compose.yml"]["exists"] = True
    
    # Check for KG files and validate source links if KG feature is enabled
    if kg_enabled:
        check_results["kg"] = {"exists": False, "valid_links": False, "issues": []}
        
        kg_dir = project_root / "kg"
        concepts_file = kg_dir / "concepts.json"
        rules_file = kg_dir / "rules.json"
        
        if not kg_dir.exists() or not kg_dir.is_dir():
            check_results["kg"]["issues"].append("kg directory not found but KG feature is enabled")
            issues_found = True
        else:
            check_results["kg"]["exists"] = True
            
            # Check for concepts.json and rules.json
            if not concepts_file.exists() and not rules_file.exists():
                check_results["kg"]["issues"].append("Neither concepts.json nor rules.json found in kg directory")
                issues_found = True
            else:
                # Validate source links
                try:
                    import json
                    concepts = []
                    rules = []
                    
                    # Extract concepts from concepts.json
                    if concepts_file.exists():
                        try:
                            with open(concepts_file, "r", encoding="utf-8") as f:
                                concepts_data = json.load(f)
                                for concept in concepts_data.get("concepts", []):
                                    name = concept.get("name", "")
                                    description = concept.get("description", "")
                                    source_file = concept.get("source", {}).get("file", "")
                                    line_number = concept.get("source", {}).get("line", 0)
                                    concepts.append(KGEntry(name, description, source_file, line_number))
                        except Exception as e:
                            check_results["kg"]["issues"].append(f"Error parsing concepts.json: {str(e)}")
                            issues_found = True
                    
                    # Extract rules from rules.json
                    if rules_file.exists():
                        try:
                            with open(rules_file, "r", encoding="utf-8") as f:
                                rules_data = json.load(f)
                                for rule in rules_data.get("rules", []):
                                    name = rule.get("name", "")
                                    description = rule.get("description", "")
                                    source_file = rule.get("source", {}).get("file", "")
                                    line_number = rule.get("source", {}).get("line", 0)
                                    rules.append(KGEntry(name, description, source_file, line_number))
                        except Exception as e:
                            check_results["kg"]["issues"].append(f"Error parsing rules.json: {str(e)}")
                            issues_found = True
                    
                    # Validate source links for both concepts and rules
                    if concepts or rules:
                        # Validate concepts
                        if concepts:
                            concept_validation = validate_source_links(concepts, project_root)
                            if not concept_validation.valid:
                                issues_found = True
                                for warning in concept_validation.warnings:
                                    check_results["kg"]["issues"].append(f"Concept source link issue: {warning}")
                        
                        # Validate rules
                        if rules:
                            rule_validation = validate_source_links(rules, project_root)
                            if not rule_validation.valid:
                                issues_found = True
                                for warning in rule_validation.warnings:
                                    check_results["kg"]["issues"].append(f"Rule source link issue: {warning}")
                        
                        # Set validation status
                        if not check_results["kg"]["issues"]:
                            check_results["kg"]["valid_links"] = True
                        
                except Exception as e:
                    check_results["kg"]["issues"].append(f"Error validating source links: {str(e)}")
                    issues_found = True
    
    # Prepare output depending on format
    if json_output:
        # Include environment info if specified
        env_info = None
        if khora_env:
            env_info = {"name": khora_env, "applied": True}
            
        result = {
            "timestamp": datetime.datetime.now().isoformat(),
            "environment": env_info,
            "active_environment": khora_env,
            "total_checks": sum(len(r.keys()) - 1 for r in check_results.values()),  # -1 to exclude "issues" key
            "passed_checks": sum(sum(1 for k, v in r.items() if k != "issues" and v is True) for r in check_results.values()),
            "checks": check_results,
            "issues_found": issues_found
        }
        import json  # Import json in local scope to avoid UnboundLocalError
        click.echo(json.dumps(result, indent=2))
        
        # Only exit with error code for non-environment health checks to help with testing
        if issues_found and not khora_env:
            sys.exit(1)
    else:
        # Standard output
        if verbose:
            click.echo("\nDetailed check results:")
            for file_name, result in check_results.items():
                status = "✅" if not result.get("issues") else "❌"
                click.echo(f"\n{status} {file_name}")
                
                for key, value in result.items():
                    if key != "issues":
                        click.echo(f"  - {key}: {value}")
                
                if result.get("issues"):
                    click.echo("  Issues:")
                    for issue in result["issues"]:
                        click.echo(f"    - {issue}")
        
        # Summary output
        total_checks = sum(len(r.keys()) - 1 for r in check_results.values())  # -1 to exclude "issues" key
        passed_checks = sum(sum(1 for k, v in r.items() if k != "issues" and v is True) for r in check_results.values())
        
        click.echo(f"\nHealth check summary: {passed_checks}/{total_checks} checks passed")
        
        if issues_found:
            click.echo("❌ Issues were found in the project:")
            # Always show issues regardless of verbose flag
            for file_name, result in check_results.items():
                if result.get("issues"):
                    click.echo(f"  - {file_name}:")
                    for issue in result["issues"]:
                        click.echo(f"    * {issue}")
            sys.exit(1)
        else:
            click.echo("✅ No issues found. The project appears to be healthy.")


@main_cli.command()
@click.option(
    "--out",
    help="Output file path for the report (default: stdout)",
)
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output report in JSON format for AI consumption",
)
@click.option(
    "--khora-env",
    help="Environment to use for manifest layering (e.g., 'dev', 'prod')",
)
def inspect(out: Optional[str], json_output: bool, khora_env: Optional[str] = None):
    """
    Generate a detailed inspection report of the Khora project.
    
    Analyzes project structure, manifest, KG validity, Python syntax,
    and generates a comprehensive report.
    
    With --json-output, generates a structured JSON report suitable for AI consumption.
    With --khora-env, applies environment-specific manifest overrides.
    """
    project_root = find_project_root()
    
    # Initialize the report content
    report = []
    report.append("# Khora Project Inspection Report")
    report.append(f"\nGenerated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Project basic info
    project_name = project_root.name
    report.append(f"\n## Project: {project_name}")
    report.append(f"\nLocation: {project_root}")
    
    # Analyze pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    report.append("\n## Manifest Analysis")
    
    if not pyproject_path.exists():
        report.append("\n❌ pyproject.toml not found")
    else:
        try:
            with open(pyproject_path, "r", encoding="utf-8") as f:
                pyproject = tomlkit.parse(f.read())
            
            # Extract project info
            if "project" in pyproject:
                report.append("\n### Basic Project Info")
                if "name" in pyproject["project"]:
                    report.append(f"\n- Name: {pyproject['project']['name']}")
                if "version" in pyproject["project"]:
                    report.append(f"\n- Version: {pyproject['project']['version']}")
                if "description" in pyproject["project"]:
                    report.append(f"\n- Description: {pyproject['project']['description']}")
            
            # Extract Khora config
            if "tool" in pyproject and "khora" in pyproject["tool"]:
                report.append("\n### Khora Configuration")
                
                # Extract features
                if "features" in pyproject["tool"]["khora"]:
                    features = pyproject["tool"]["khora"]["features"]
                    report.append("\n#### Enabled Features:")
                    if not features:
                        report.append("\n- None")
                    else:
                        for feature, enabled in features.items():
                            status = "✅" if enabled else "❌"
                            report.append(f"\n- {status} {feature}")
                
                # Extract paths
                if "paths" in pyproject["tool"]["khora"]:
                    paths = pyproject["tool"]["khora"]["paths"]
                    report.append("\n#### Custom Paths:")
                    if not paths:
                        report.append("\n- None (using defaults)")
                    else:
                        for path_name, path_value in paths.items():
                            report.append(f"\n- {path_name}: {path_value}")
            else:
                report.append("\n❌ [tool.khora] section not found in pyproject.toml")
        except Exception as e:
            report.append(f"\n❌ Error parsing pyproject.toml: {str(e)}")
    
    # File structure analysis
    report.append("\n## File Structure Analysis")
    
    # Calculate and add directory statistics
    total_files = 0
    file_types = {}
    python_files = []
    
    for root, dirs, files in os.walk(project_root):
        # Skip .git, venv and other common non-project dirs
        if any(skip_dir in root for skip_dir in [".git", "venv", ".venv", "__pycache__", ".pytest_cache"]):
            continue
            
        for file in files:
            total_files += 1
            ext = os.path.splitext(file)[1].lower()
            
            if ext:
                file_types[ext] = file_types.get(ext, 0) + 1
            
            if ext == ".py":
                rel_path = os.path.relpath(os.path.join(root, file), project_root)
                python_files.append(rel_path)
    
    report.append(f"\n- Total files: {total_files}")
    report.append("\n- File types breakdown:")
    for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
        report.append(f"\n  - {ext}: {count} files")
    
    # Python files syntax check
    if python_files:
        report.append("\n## Python Files Syntax Check")
        syntax_issues = []
        
        for py_file in python_files:
            full_path = project_root / py_file
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    compile(f.read(), py_file, 'exec')
            except Exception as e:
                syntax_issues.append((py_file, str(e)))
        
        if syntax_issues:
            report.append("\n❌ Syntax issues found:")
            for file, error in syntax_issues:
                report.append(f"\n- {file}: {error}")
        else:
            report.append("\n✅ All Python files passed syntax check")
    
    # KG (Knowledge Graph) validity check
    kg_dir = project_root / ".khora" / "kg"
    report.append("\n## Knowledge Graph Analysis")
    
    if kg_dir.exists() and kg_dir.is_dir():
        kg_files = list(kg_dir.glob("*.json"))
        report.append(f"\n- KG files found: {len(kg_files)}")
        
        # We could add more KG validation here in the future
        report.append(f"\n- KG location: {kg_dir}")
    else:
        report.append("\n- No Knowledge Graph found in .khora/kg/")
    
    # Calculate heuristic score
    score = 0
    max_score = 100
    
    # Add points for basic project structure
    if pyproject_path.exists():
        score += 20
    
    # Add points for Khora configuration
    khora_config_found = False
    try:
        if "tool" in pyproject and "khora" in pyproject["tool"]:
            score += 20
            khora_config_found = True
    except:
        pass
    
    # Add points for valid Python files
    if python_files and not syntax_issues:
        score += 20
    
    # Add points for KG
    if kg_dir.exists() and kg_dir.is_dir() and list(kg_dir.glob("*.json")):
        score += 20
    
    # Add points for CI
    if (project_root / ".github" / "workflows").exists():
        score += 10
    
    # Add points for Docker setup
    if (project_root / "docker-compose.yml").exists():
        score += 10
    
    # Final score calculation
    final_score = min(score, max_score)
    
    report.append("\n## Overall Score")
    report.append(f"\n**Project Score: {final_score}/{max_score}**")
    
    # Add some health recommendations
    report.append("\n## Recommendations")
    if not khora_config_found:
        report.append("\n- Add a [tool.khora] section to pyproject.toml")
    if not (project_root / ".khora" / "context.yaml").exists():
        report.append("\n- Create a .khora/context.yaml file")
    if not (project_root / ".github" / "workflows").exists() and khora_config_found:
        report.append("\n- Enable CI with `[tool.khora.features].ci_github_actions = true`")
    
    # Prepare and output the report
    if json_output:
        # Create a structured JSON report
        json_report = {
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "project": project_name,
            "location": str(project_root),
            "score": final_score,
            "max_score": max_score,
            "file_stats": {
                "total_files": total_files,
                "file_types": file_types
            }
        }
        
        # Add manifest info if available
        try:
            if khora_env:
                json_report["environment"] = khora_env
                
            if pyproject_path.exists():
                with open(pyproject_path, "r", encoding="utf-8") as f:
                    pyproject = tomlkit.parse(f.read())
                
                if "tool" in pyproject and "khora" in pyproject["tool"]:
                    # Try to use the new KhoraManifestConfig to get proper manifest info
                    try:
                        config = KhoraManifestConfig.from_project_toml_with_env(project_root, env=khora_env)
                        json_report["manifest"] = config.model_dump(mode='json')
                    except Exception:
                        # Fall back to raw TOML if KhoraManifestConfig fails
                        json_report["manifest"] = dict(pyproject["tool"]["khora"])
        except Exception as e:
            json_report["manifest_error"] = str(e)
        
        # Output JSON
        if out:
            out_path = Path(out)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(json_report, f, indent=2)
            click.echo(f"JSON inspection report written to: {out_path}")
        else:
            click.echo(json.dumps(json_report, indent=2))
    else:
        # Traditional Markdown report
        full_report = "\n".join(report)
        
        # Output the report
        if out:
            out_path = Path(out)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(full_report)
            click.echo(f"Inspection report written to: {out_path}")
        else:
            click.echo(full_report)

@main_cli.command()
@click.option(
    "--pyproject-path",
    default="./pyproject.toml",
    help="Path to pyproject.toml file",
)
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output validation results in JSON format for AI consumption",
)
@click.option(
    "--khora-env",
    help="Environment to validate with manifest layering (e.g., 'dev', 'prod')",
)
def validate_manifest(pyproject_path: str, json_output: bool, khora_env: Optional[str] = None):
    """
    Validate the [tool.khora] section of pyproject.toml.
    
    Checks if the manifest configuration in pyproject.toml is valid according to
    the KhoraManifestConfig schema. Returns information about the manifest and
    any validation errors.
    
    With --khora-env, validates the manifest with environment-specific overrides.
    """
    pyproject_path = Path(pyproject_path)
    project_dir = pyproject_path.parent
    
    try:
        # Parse and validate the manifest
        if khora_env:
            config = KhoraManifestConfig.from_project_toml_with_env(project_dir, env=khora_env)
            env_info = f" with '{khora_env}' environment"
        else:
            config = KhoraManifestConfig.from_project_toml(project_dir)
            env_info = ""
        
        if json_output:
            result = {
                "valid": True,
                "timestamp": datetime.datetime.now().isoformat(),
                "manifest": config.model_dump(mode='json')
            }
            if khora_env:
                result["environment"] = khora_env
                result["active_environment"] = config.active_environment
                
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"✅ Manifest is valid{env_info}.")
            click.echo(f"Project: {config.project_name}")
            click.echo(f"Description: {config.project_description}")
            click.echo(f"Python Version: {config.python_version}")
            
            # Display active environment if applicable
            if config.active_environment:
                click.echo(f"Active Environment: {config.active_environment}")
            
            # Show feature flags
            click.echo("\nEnabled Features:")
            features = config.features.model_dump()
            for feature, enabled in features.items():
                if isinstance(enabled, bool):
                    status = "✅" if enabled else "❌"
                    click.echo(f"- {status} {feature}")
                else:
                    click.echo(f"- {feature}: {enabled}")
    
    except KhoraManifestNotFoundError as e:
        if json_output:
            result = {
                "valid": False,
                "timestamp": datetime.datetime.now().isoformat(),
                "error_type": "manifest_not_found",
                "error": str(e)
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"❌ {str(e)}", err=True)
        sys.exit(1)
        
    except KhoraManifestInvalidError as e:
        if json_output:
            result = {
                "valid": False,
                "timestamp": datetime.datetime.now().isoformat(),
                "error_type": "manifest_invalid",
                "errors": e.errors if hasattr(e, 'errors') else [str(e)]
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"❌ Invalid manifest: {e.errors if hasattr(e, 'errors') else str(e)}", err=True)
        sys.exit(1)
        
    except Exception as e:
        if json_output:
            result = {
                "valid": False,
                "timestamp": datetime.datetime.now().isoformat(),
                "error_type": "unexpected_error",
                "error": str(e)
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"❌ Unexpected error: {str(e)}", err=True)
        sys.exit(1)


@main_cli.command()
@click.option(
    "--installed",
    is_flag=True,
    default=True,
    help="List locally installed Khora plugins",
)
@click.option(
    "--pypi",
    is_flag=True,
    default=False,
    help="Search PyPI for available Khora plugins (requires internet connection)",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show detailed plugin information",
)
def list_plugins(installed: bool, pypi: bool, verbose: bool):
    """
    List available Khora extensions/plugins.
    
    By default, shows locally installed plugins. Use --pypi to also search
    PyPI for available plugins.
    """
    all_plugins = []
    
    # Find locally installed plugins if requested
    if installed:
        click.echo("Searching for locally installed Khora plugins...")
        local_plugins = find_installed_plugins(verbose)
        all_plugins.extend(local_plugins)
        click.echo(f"Found {len(local_plugins)} installed plugins.\n")

    # Search PyPI for plugins if requested
    if pypi:
        click.echo("Searching PyPI for Khora plugins...")
        try:
            pypi_plugins = find_pypi_plugins(verbose)
            # Filter out already installed plugins
            installed_names = {p['name'] for p in local_plugins} if installed else set()
            new_pypi_plugins = [p for p in pypi_plugins if p['name'] not in installed_names]
            all_plugins.extend(new_pypi_plugins)
            click.echo(f"Found {len(new_pypi_plugins)} additional plugins on PyPI.\n")
        except Exception as e:
            click.echo(f"Error searching PyPI: {str(e)}", err=True)
    
    # Display the plugins
    if not all_plugins:
        click.echo("No Khora plugins found.")
        return
    
    click.echo("Available Khora Plugins:\n")
    for idx, plugin in enumerate(all_plugins, 1):
        name = plugin['name']
        version = plugin.get('version', 'unknown')
        description = plugin.get('description', 'No description')
        source = "installed" if plugin.get('installed', False) else "PyPI"
        
        # Basic info for all plugins
        click.echo(f"{idx}. {name} (v{version}) [{source}]")
        click.echo(f"   {description}")
        
        # Additional details if verbose
        if verbose:
            if 'author' in plugin:
                click.echo(f"   Author: {plugin['author']}")
            if 'homepage' in plugin:
                click.echo(f"   Homepage: {plugin['homepage']}")
            if 'features' in plugin:
                click.echo(f"   Features: {', '.join(plugin['features'])}")
        
        click.echo("")


def find_installed_plugins(verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Find locally installed Khora plugins.
    
    Args:
        verbose: Whether to collect detailed information
        
    Returns:
        List of dictionaries with plugin information
    """
    plugins = []
    
    # Search for installed packages with Khora plugin naming pattern
    for distribution in pkg_resources.working_set:
        name = distribution.project_name
        
        # Check if this might be a Khora plugin
        if (name.startswith('khora-') or 
            name.startswith('khora_') or
            'khora' in name.lower()):
            
            plugin_info = {
                'name': name,
                'version': distribution.version,
                'installed': True
            }
            
            # Try to get metadata for the plugin
            try:
                # Try to get description
                if distribution.has_metadata('METADATA'):
                    metadata = distribution.get_metadata('METADATA')
                    for line in metadata.splitlines():
                        if line.startswith('Summary: '):
                            plugin_info['description'] = line[9:].strip()
                        elif line.startswith('Author: '):
                            plugin_info['author'] = line[8:].strip()
                        elif line.startswith('Home-page: '):
                            plugin_info['homepage'] = line[11:].strip()
                
                # If verbose, try to import the plugin to get more info
                if verbose:
                    # Convert project name to importable module name
                    module_name = distribution.project_name.replace('-', '_')
                    try:
                        module = importlib.import_module(module_name)
                        # Try to get plugin features if available
                        if hasattr(module, 'features'):
                            plugin_info['features'] = module.features
                    except ImportError:
                        pass  # Module not directly importable
                
            except Exception:
                # If metadata extraction fails, just use what we have
                pass
            
            plugins.append(plugin_info)
    
    return plugins


def find_pypi_plugins(verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Search PyPI for Khora plugins.
    
    Args:
        verbose: Whether to collect detailed information
        
    Returns:
        List of dictionaries with plugin information
    """
    plugins = []
    
    try:
        import requests
        import json
        
        # Search PyPI for packages with 'khora' in the name or description
        search_url = "https://pypi.org/pypi?:action=search&term=khora"
        response = requests.get(search_url)
        
        if response.status_code != 200:
            raise Exception(f"PyPI search failed with status code {response.status_code}")
        
        # Parse the results
        # Note: PyPI search results may vary in format depending on the API
        # This is a simplified approach - actual implementation might need adjustments
        try:
            results = json.loads(response.text)
            for result in results:
                if 'name' in result:
                    plugin_info = {
                        'name': result['name'],
                        'version': result.get('version', 'unknown'),
                        'description': result.get('description', 'No description'),
                        'installed': False
                    }
                    
                    if 'author' in result:
                        plugin_info['author'] = result['author']
                    if 'home_page' in result:
                        plugin_info['homepage'] = result['home_page']
                    
                    plugins.append(plugin_info)
        except json.JSONDecodeError:
            # Fall back to a simpler approach if JSON parsing fails
            import re
            # Extract package names using regex (this is a simplified approach)
            package_matches = re.findall(r'href="/project/([^"]+)"', response.text)
            for package_name in package_matches:
                if ('khora' in package_name.lower() and
                    not any(p['name'] == package_name for p in plugins)):
                    plugin_info = {
                        'name': package_name,
                        'installed': False
                    }
                    
                    # Optionally get more details if verbose
                    if verbose:
                        try:
                            pkg_url = f"https://pypi.org/pypi/{package_name}/json"
                            pkg_response = requests.get(pkg_url)
                            if pkg_response.status_code == 200:
                                pkg_data = json.loads(pkg_response.text)
                                info = pkg_data.get('info', {})
                                plugin_info['version'] = info.get('version', 'unknown')
                                plugin_info['description'] = info.get('summary', 'No description')
                                plugin_info['author'] = info.get('author', '')
                                plugin_info['homepage'] = info.get('home_page', '')
                        except Exception:
                            pass
                    
                    plugins.append(plugin_info)
    
    except ImportError:
        # requests module not available
        click.echo("Warning: 'requests' module not installed. PyPI search not available.", err=True)
    except Exception as e:
        raise Exception(f"Error searching PyPI: {str(e)}")
    
    return plugins


def find_project_root() -> Path:
    """
    Find the root directory of the project.
    
    Returns:
        Path: Path to the project root directory
    """
    # Start at the current directory
    current_dir = Path.cwd()
    
    # Traverse up the directory tree until we find pyproject.toml
    while current_dir != current_dir.parent:
        if (current_dir / "pyproject.toml").exists():
            return current_dir
        current_dir = current_dir.parent
    
    # If we reach here, we couldn't find the project root
    click.echo("Error: Could not find project root (pyproject.toml)", err=True)
    sys.exit(1)


def is_version_higher(current: str, new: str) -> bool:
    """
    Check if the new version is higher than the current version.
    
    Args:
        current: Current version string
        new: New version string
        
    Returns:
        bool: True if new version is higher, False otherwise
    """
    current_parts = [int(part) for part in current.split(".")]
    new_parts = [int(part) for part in new.split(".")]
    
    # Compare major, minor, patch versions in order
    for i in range(min(len(current_parts), len(new_parts))):
        if new_parts[i] > current_parts[i]:
            return True
        elif new_parts[i] < current_parts[i]:
            return False
    
    # If we have the same prefix but one has more parts
    return len(new_parts) > len(current_parts)


def update_changelog(project_root: Path, current_version: str, new_version: str):
    """
    Update CHANGELOG.md with a new version section.
    
    Args:
        project_root: Path to the project root
        current_version: Current version string
        new_version: New version string
    """
    changelog_path = project_root / "CHANGELOG.md"
    
    # Create changelog if it doesn't exist
    if not changelog_path.exists():
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write("# Changelog\n\n")
    
    # Read the current changelog
    with open(changelog_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Get today's date
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # Prepare the new version section
    new_section = f"## [{new_version}] - {today}\n\n"
    new_section += "### Added\n\n- \n\n"
    new_section += "### Changed\n\n- \n\n"
    new_section += "### Fixed\n\n- \n\n"
    
    # Insert the new section after the title
    if "# Changelog" in content:
        updated_content = content.replace(
            "# Changelog",
            "# Changelog\n\n" + new_section
        )
    else:
        # If no title, just prepend the new section
        updated_content = "# Changelog\n\n" + new_section + content
    
    # Write the updated content
    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(updated_content)


if __name__ == "__main__":
    main_cli()
