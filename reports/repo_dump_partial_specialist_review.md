# 📦 Partial File Dump  
*(root `khorkernel`, max_bytes=50000)*

## khora-kernel/src/khora_kernel/cli/commands.py  
`23482 bytes`  ·  `b08d7f0`  
```python
"""
CLI Commands for Khora Kernel.
"""

import click
import json
import pathlib
import sys # For sys.exit
import subprocess
import os
from typing import List, Optional
# New imports for 'create' command
from pyscaffold.api import create_project, NO_CONFIG # Import NO_CONFIG
from khora_kernel.extensions.core.extension import CoreExtension
from khora_kernel.extensions.docker.extension import DockerExtension
from khora_kernel.extensions.precommit.extension import PrecommitExtension
from khora_kernel.extensions.fastapi_scaffold.extension import FastApiScaffoldExtension
# from khora_kernel.sdk.utils import KhoraJSONEncoder # If needed for custom JSON encoding

from khora_kernel.sdk.config import KhoraManifestConfig
from khora_kernel.extensions.github_issues_manager.config import GitHubIssuesManagerConfig
from khora_kernel.extensions.github_issues_manager.github_client import GitHubAPIClient
from khora_kernel.sdk.errors import KhoraConfigurationError

# Import all command functions from the specialized modules
from khora_kernel.cli.version_commands import bump_version
from khora_kernel.cli.health_commands import health, inspect
from khora_kernel.cli.manifest_commands import validate_manifest
from khora_kernel.cli.plugin_commands import list_plugins
from khora_kernel.cli.add_commands import add_cli # New import


@click.group()
def main_cli():
    """Khora Kernel command line interface."""
    pass


# --- Project Development Group ---
@click.group("project-dev")
def project_dev_cli():
    """Commands for Khora Kernel's own development and self-management."""
    pass


@project_dev_cli.command("plan-to-issues")
@click.option(
    "--plan-file",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=pathlib.Path),
    required=True,
    help="Path to the Khora JSON plan file.",
)
@click.option(
    "--milestone",
    type=str,
    required=False,
    help="Name of a GitHub milestone to assign to all created issues.",
)
@click.pass_context
def plan_to_issues(ctx, plan_file: pathlib.Path, milestone: str | None):
    """
    Reads a Khora JSON plan file and creates GitHub issues for each ticket.
    This command assumes it's being run from within the khora-kernel project directory
    or a project that has `github_issues_manager` configured.
    """
    click.echo(f"Processing plan file: {plan_file}")
    if milestone:
        click.echo(f"Assigning to milestone: {milestone}")

    try:
        # Load Khora manifest for the current project.
        # Assuming CWD is the project root (e.g., khora-kernel itself)
        project_dir = pathlib.Path.cwd()
        manifest_config = KhoraManifestConfig.from_project_toml(project_dir=project_dir)
        
        if not manifest_config.plugins_config or not manifest_config.plugins_config.github_issues_manager:
            click.secho(
                "Error: GitHub Issues Manager configuration (`[tool.khora.plugins_config.github_issues_manager]`) not found in pyproject.toml.",
                fg="red",
            )
            sys.exit(1)
        
        gh_config: GitHubIssuesManagerConfig = manifest_config.plugins_config.github_issues_manager

        client = GitHubAPIClient(config=gh_config, manifest_config=manifest_config)

    except KhoraConfigurationError as e:
        click.secho(f"Configuration error: {e}", fg="red")
        sys.exit(1)
    except ValueError as e: # For token issues from GitHubAPIClient init
        click.secho(f"Initialization error: {e}", fg="red")
        sys.exit(1)
    except Exception as e:
        click.secho(f"An unexpected error occurred during setup: {e}", fg="red")
        sys.exit(1)

    try:
        with open(plan_file, "r") as f:
            plan_data = json.load(f)
    except FileNotFoundError:
        click.secho(f"Error: Plan file not found at {plan_file}", fg="red")
        sys.exit(1)
    except json.JSONDecodeError:
        click.secho(f"Error: Could not decode JSON from plan file {plan_file}. Malformed JSON.", fg="red")
        sys.exit(1)
    except Exception as e:
        click.secho(f"Error reading plan file {plan_file}: {e}", fg="red")
        sys.exit(1)

    tickets = plan_data.get("tickets")
    if not isinstance(tickets, list):
        click.secho("Error: Plan file must contain a top-level 'tickets' array.", fg="red")
        sys.exit(1)

    created_issues_count = 0
    failed_issues_count = 0
    
    click.echo(f"Found {len(tickets)} ticket(s) in the plan.")

    for i, ticket in enumerate(tickets):
        click.echo(f"\nProcessing ticket {i+1}/{len(tickets)}: {ticket.get('id', 'N/A')} - {ticket.get('title', 'No Title')}")
        
        title = ticket.get("title")
        description = ticket.get("description", "")
        acceptance_criteria = ticket.get("acceptance_criteria", [])
        sprint_assignment = ticket.get("sprint_assignment")
        status = ticket.get("status")
        impact_assessment = ticket.get("impact_assessment", {})
        ticket_labels = ticket.get("labels", [])

        if not title:
            click.secho(f"  Skipping ticket {ticket.get('id', 'N/A')} due to missing title.", fg="yellow")
            failed_issues_count += 1
            continue

        body_parts = []
        if description:
            body_parts.append(f"**Description:**\n{description}\n")
        
        if acceptance_criteria:
            ac_md = "\n".join([f"- {ac}" for ac in acceptance_criteria])
            body_parts.append(f"**Acceptance Criteria:**\n{ac_md}\n")

        if sprint_assignment is not None: # Could be 0
            body_parts.append(f"**Sprint Assignment:** {sprint_assignment}\n")
        
        if status:
            body_parts.append(f"**Status:** {status}\n")

        if impact_assessment:
            ia_parts = ["**Impact Assessment:**"]
            for key, value in impact_assessment.items():
                ia_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
            body_parts.append("\n".join(ia_parts) + "\n")
        
        # Add original ticket ID to body for traceability
        body_parts.append(f"\n_Original Khora Ticket ID: {ticket.get('id', 'N/A')}_")

        issue_body = "\n".join(body_parts).strip()

        try:
            created_issue = client.create_issue(
                title=title,
                body=issue_body,
                labels=ticket_labels,
                milestone_name=milestone,
            )
            click.secho(f"  Successfully created issue: {created_issue.get('html_url')}", fg="green")
            created_issues_count += 1
        except Exception as e:
            click.secho(f"  Failed to create issue for ticket {ticket.get('id', 'N/A')}: {e}", fg="red")
            failed_issues_count += 1
            # Continue processing other tickets as per design

    click.echo("\n--- Summary ---")
    click.secho(f"Successfully created issues: {created_issues_count}", fg="green")
    if failed_issues_count > 0:
        click.secho(f"Failed to create issues: {failed_issues_count}", fg="red")
    else:
        click.secho(f"Failed to create issues: {failed_issues_count}", fg="green")

    if failed_issues_count > 0:
        sys.exit(1)

# --- Sync Stubs Command ---
@main_cli.command("sync-stubs")
@click.option(
    "--proto-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=pathlib.Path),
    required=True,
    help="Directory containing the .proto files.",
)
@click.option(
    "--stubs-out-dir",
    type=click.Path(file_okay=False, dir_okay=True, writable=True, path_type=pathlib.Path),
    required=True,
    help="Output directory for the generated Python stubs.",
)
def sync_stubs(proto_dir: pathlib.Path, stubs_out_dir: pathlib.Path):
    """
    Generates Python gRPC stubs from .proto files.
    """
    click.echo(f"Scanning for .proto files in: {proto_dir.resolve()}")
    click.echo(f"Output directory for stubs: {stubs_out_dir.resolve()}")

    stubs_out_dir.mkdir(parents=True, exist_ok=True)

    proto_files: List[pathlib.Path] = list(proto_dir.rglob("*.proto"))

    if not proto_files:
        click.secho(f"No .proto files found in {proto_dir}", fg="yellow")
        return

    click.echo(f"Found {len(proto_files)} .proto file(s):")
    for pf in proto_files:
        click.echo(f"  - {pf.relative_to(proto_dir)}")

    generated_files_count = 0
    error_count = 0

    for proto_file_path in proto_files:
        # Ensure paths are absolute or relative to a known root for protoc include paths
        # For simplicity, we assume proto_dir is the root for include paths.
        # The proto_file_path itself should be relative to proto_dir for the command,
        # or an absolute path. Here, proto_file_path is already absolute from rglob.
        
        # The command expects the .proto file path relative to the include path (-I).
        # However, grpc_tools.protoc can also take absolute paths for the .proto file.
        # Let's use absolute paths for clarity and robustness.
        
        # Ensure the output directory for this specific proto file's stubs exists
        # This is important if proto files are in subdirectories of proto_dir
        # and we want to mirror that structure in stubs_out_dir.
        # For now, all stubs go to the root of stubs_out_dir.
        # If a mirrored structure is desired, stubs_out_dir would need to be adjusted per proto file.
        # The standard grpc_tools.protoc behavior is to place generated files based on
        # the package directive in the .proto file, relative to the *_out directories.

        # Command construction
        # python -m grpc_tools.protoc -I<proto_dir> --python_out=<stubs_out_dir> --grpc_python_out=<stubs_out_dir> <path_to_proto_file>
        # We use absolute path for proto_file_path for robustness.
        # The -I path should be the root directory from which .proto imports are resolved.
        
        # Get the path of the proto file relative to the proto_dir for the command argument
        # if we want to keep imports clean within proto files.
        # However, passing the absolute path to the proto file directly also works.
        # For this MVP, let's pass the absolute path of the proto file.
        
        cmd = [
            sys.executable,  # Use the current Python interpreter
            "-m",
            "grpc_tools.protoc",
            f"-I{proto_dir.resolve()}",
            f"--python_out={stubs_out_dir.resolve()}",
            f"--grpc_python_out={stubs_out_dir.resolve()}",
            str(proto_file_path.resolve()), # Absolute path to the .proto file
        ]
        
        click.echo(f"\nProcessing: {proto_file_path.name}")
        click.echo(f"  Command: {' '.join(cmd)}")

        try:
            # It's good practice to capture output and check return code
            process = subprocess.run(cmd, capture_output=True, text=True, check=False) # check=False to handle errors manually
            
            if process.stdout:
                click.echo(f"  protoc stdout:\n{process.stdout}")
            if process.stderr:
                # grpc_tools.protoc often prints to stderr even on success (e.g., warnings or informational)
                # We should only treat it as an error if returncode is non-zero.
                click.echo(f"  protoc stderr:\n{process.stderr}")

            if process.returncode == 0:
                click.secho(f"  Successfully generated stubs for {proto_file_path.name}", fg="green")
                generated_files_count +=1 # Assuming one .proto file generates stubs
            else:
                click.secho(f"  Error generating stubs for {proto_file_path.name}. Return code: {process.returncode}", fg="red")
                error_count += 1
                # stderr already printed if any
        except FileNotFoundError:
            click.secho("Error: grpc_tools.protoc not found. Is grpcio-tools installed?", fg="red")
            # No point in continuing if protoc is not found
            sys.exit(1) 
        except Exception as e:
            click.secho(f"  An unexpected error occurred while processing {proto_file_path.name}: {e}", fg="red")
            error_count += 1
            
    click.echo("\n--- Sync Stubs Summary ---")
    if generated_files_count > 0 :
         click.secho(f"Successfully processed/generated stubs for {generated_files_count} .proto file(s).", fg="green")
    if error_count > 0:
        click.secho(f"Encountered errors for {error_count} .proto file(s).", fg="red")
        sys.exit(1)
    elif generated_files_count == 0 and not proto_files: # Should have been caught earlier
        click.echo("No .proto files were processed.")
    elif generated_files_count == 0 and proto_files : # No new stubs generated, but files were processed (e.g. no changes)
        click.echo("Processed .proto files, but no new stubs were generated (files may be up-to-date or empty).")


# Register all commands with the main CLI group
main_cli.add_command(bump_version)
main_cli.add_command(health)
main_cli.add_command(inspect)
main_cli.add_command(validate_manifest)
main_cli.add_command(list_plugins)
main_cli.add_command(project_dev_cli) # Add the project-dev group
main_cli.add_command(add_cli) # Add the new add group


# --- Create Command ---
@main_cli.command()
@click.argument("project_name", required=True, type=str)
@click.option(
    "--directory",
    default=None,
    type=click.Path(file_okay=False, dir_okay=True, writable=True, resolve_path=True),
    help="Directory to create the project in. Defaults to a new folder in the current directory."
)
@click.option(
    "--khora-env",
    default=None,
    type=str,
    help="Khora environment to use for scaffolding (e.g., 'default', 'minimal')."
)
@click.option(
    "--json-output",
    is_flag=True,
    help="Output project creation status in JSON format."
)
def create(project_name: str, directory: Optional[str], khora_env: Optional[str], json_output: bool):
    """Create a new Khora project scaffold."""
    try:
        if project_name == ".":
            # If project_name is '.', the project is created in the current directory
            # or the specified --directory.
            if directory:
                final_project_path = pathlib.Path(directory).resolve()
            else:
                final_project_path = pathlib.Path.cwd()
            # PyScaffold will use the name from pyproject.toml or raise an error if not found/inferable
            # The 'project_name' variable for display/logging purposes remains '.'
            if not json_output:
                click.echo(f"Creating Khora project in current directory: {final_project_path}")
        elif directory:
            # If directory is provided, project_name will be a subdirectory within it
            final_project_path = pathlib.Path(directory).resolve() / project_name
            if not json_output:
                click.echo(f"Creating Khora project: {project_name} in {final_project_path}")
        else:
            # If no directory, project_name will be a subdirectory in the current working directory
            final_project_path = pathlib.Path.cwd() / project_name
            if not json_output:
                click.echo(f"Creating Khora project: {project_name} in {final_project_path}")


        # Instantiate all relevant Khora extensions
        core_ext = CoreExtension()
        docker_ext = DockerExtension()
        precommit_ext = PrecommitExtension()
        fastapi_ext = FastApiScaffoldExtension()

        # Prepare a base opts dictionary that will be used by all Khora extensions.
        # PyScaffold's fill_missing_opts will later convert this to a Namespace if needed.
        # The key is to ensure that when each extension's `activate` is called,
        # its `self.opts` contains the necessary flags and shared data like `khora_parsed_config`.
        
        # Base options for all Khora extensions
        # This dict will be expanded and passed to create_project,
        # and PyScaffold will ensure each extension instance gets these opts.
        common_khora_opts = {
            core_ext.name: True,      # khora_core = True
            docker_ext.name: True,    # khora_docker = True
            precommit_ext.name: True, # khora_precommit = True
            fastapi_ext.name: True,   # fastapi_scaffold = True
        }
        if khora_env:
            common_khora_opts['khora_env'] = khora_env

        # Determine actual_project_name_for_pyscaffold
        actual_project_name_for_pyscaffold = None
        if project_name == ".":
            # Try to read from pyproject.toml in final_project_path (which is CWD)
            try:
                toml_path = final_project_path / "pyproject.toml"
                if toml_path.exists():
                    import tomlkit
                    with open(toml_path, "r") as f:
                        toml_data = tomlkit.load(f)
                    actual_project_name_for_pyscaffold = toml_data.get("project", {}).get("name")
                    if not actual_project_name_for_pyscaffold:
                        error_message = "Could not determine project name from pyproject.toml when creating in current directory."
                        if json_output:
                            click.echo(json.dumps({"status": "error", "error_type": "configuration_error", "message": error_message, "project_path": str(final_project_path)}, indent=2))
                        else:
                            click.secho(f"Error: {error_message}", fg="red", err=True)
                        sys.exit(1)
                else:
                    error_message = "pyproject.toml not found in current directory when attempting to create project with '.'."
                    if json_output:
                        click.echo(json.dumps({"status": "error", "error_type": "file_not_found", "message": error_message, "project_path": str(final_project_path)}, indent=2))
                    else:
                        click.secho(f"Error: {error_message}", fg="red", err=True)
                    sys.exit(1)
            except Exception as e:
                error_message = f"Error reading project name from pyproject.toml: {e}"
                if json_output:
                    click.echo(json.dumps({"status": "error", "error_type": "file_read_error", "message": error_message, "project_path": str(final_project_path)}, indent=2))
                else:
                    click.secho(error_message, fg="red", err=True)
                sys.exit(1)
        else:
            actual_project_name_for_pyscaffold = project_name

        import logging
        import argparse # Required for Namespace

        logger = logging.getLogger(__name__)
        
        # Construct the full opts dictionary that PyScaffold would create
        # This includes project_path, name, and all common_khora_opts (activation flags, khora_env)
        # These are the attributes extensions will expect on `self.opts`
        complete_opts_dict = {
            "project_path": final_project_path,
            "name": actual_project_name_for_pyscaffold,
            "config": NO_CONFIG, # PyScaffold adds this
            "force": True,
            "tox": False,
            "travis": False,
            **common_khora_opts 
        }
        
        # Create a Namespace object from this dictionary
        opts_for_extensions = argparse.Namespace(**complete_opts_dict)

        # Manually set this opts object on each Khora extension instance
        core_ext.opts = opts_for_extensions
        docker_ext.opts = opts_for_extensions
        precommit_ext.opts = opts_for_extensions
        fastapi_ext.opts = opts_for_extensions
        
        logger.info(f"cli.commands.create: Manually set .opts on extension instances with: {opts_for_extensions}")

        # Prepare arguments for PyScaffold's create_project.
        # PyScaffold will still receive these kwargs and build its own internal opts.
        # The key is that our extension instances now *already have* a compatible opts object.
        pyscaffold_kwargs = {
            "project_path": final_project_path, # Redundant with opts_for_extensions but required by create_project signature
            "name": actual_project_name_for_pyscaffold, # Same as above
            "extensions": [core_ext, docker_ext, precommit_ext, fastapi_ext], 
            "config": NO_CONFIG,
            "force": True, 
            "tox": False,  
            "travis": False, 
            **common_khora_opts # Spread all other flags
        }

        logger.info(f"Calling pyscaffold.api.create_project with kwargs: {pyscaffold_kwargs}")
        create_project(**pyscaffold_kwargs)

        if json_output:
            result_data = {
                "status": "success",
                "project_name": project_name,
                "project_name": actual_project_name_for_pyscaffold if project_name == "." else project_name, # Use actual name if '.'
                "project_path": str(final_project_path), # Changed from project_dir to project_path for consistency
                "environment": khora_env,
                "message": f"Khora project {actual_project_name_for_pyscaffold if project_name == '.' else project_name} created successfully in {final_project_path}"
            }
            click.echo(json.dumps(result_data, indent=2))
        else:
            click.echo(f"✅ Khora project {project_name} created successfully!")
            click.echo(f"📂 Project directory: {final_project_path}")
            if khora_env:
                click.echo(f"🌍 Environment: {khora_env}")
            click.echo(f"📝 Check the README.md file in {final_project_path} for next steps.")
        sys.exit(0) # Re-added to see if it helps CliRunner capture output correctly

    except ImportError as e:
        # This specific error might occur if pyscaffold or other critical deps are missing
        error_message = f"Failed to import required modules: {str(e)}"
        if json_output:
            click.echo(json.dumps({
                "status": "error", "error_type": "import_error",
                "message": error_message,
                "suggestion": "Make sure all dependencies like PyScaffold are installed correctly."
            }, indent=2))
        else:
            click.secho(f"Error: {error_message}", fg="red", err=True) # Use secho for consistency
            click.secho("Suggestion: Make sure all dependencies like PyScaffold are installed correctly.", fg="yellow", err=True)
        sys.exit(1)

    except Exception as e:
        # Catch-all for other errors during project creation
        error_message = f"Failed to create project: {str(e)}"
        # Attempt to determine project path even in case of early failure for JSON output
        # This might be before final_project_path is robustly defined if error is very early.
        # For now, assume final_project_path might be available or fallback.
        path_for_json_error = str(final_project_path) if 'final_project_path' in locals() else project_name

        if json_output:
            click.echo(json.dumps({
                "status": "error",
                "error_type": "create_error",
                "message": error_message,
                "project_path": path_for_json_error
            }, indent=2))
        else:
            click.secho(f"Error: {error_message}", fg="red", err=True)
        sys.exit(1)

main_cli.add_command(create) # Register the new create command

```

## khora-kernel/src/khora_kernel/extensions/core/extension.py  
`28831 bytes`  ·  `ba80084`  
```python
"""
Core extension for Khora Kernel.

This extension handles the core functionality of Khora, including manifest parsing,
environment layering, and context.yaml generation for AI agent consumption.
"""

import argparse
import logging
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import yaml

from pyscaffold.actions import Action, ActionParams, ScaffoldOpts, Structure
from pyscaffold.extensions import Extension
from pyscaffold.operations import no_overwrite

# Import Khora-specific error types
from khora_kernel.sdk.errors import (
    KhoraError,
    KhoraExtensionError,
    KhoraContextError,
    KhoraTemplateError,
)

# manifest.py provides KhoraManifestConfig for parsing and validation.
from .manifest import (
    KhoraManifestConfig,
    KhoraManifestNotFoundError,
    KhoraManifestInvalidError,
)

logger = logging.getLogger(__name__)

# Constants for context generation
SCHEMA_VERSION = "0.1.0"


class CoreExtension(Extension):
    """
    PyScaffold extension to handle Khora-specific project scaffolding.
    """

    persist = True  # Keep the extension active for subsequent actions
    # The name of the command line option, without the leading --
    # e.g. --khora-core becomes "khora-core"
    # PyScaffold will also make sure this is a valid Python identifier
    # by replacing "-" with "_"
    name = "khora_core"  # This will be used as --khora-core

    def augment_cli(self, parser: argparse.ArgumentParser):
        """Add a CLI option for this extension"""
        parser.add_argument(
            self.flag,  # self.flag is derived from self.name
            dest=self.name,  # Will be stored in opts.khora_core
            action="store_true",
            default=False,
            help="Activate Khora core scaffolding enhancements",
        )

        # Add environment option for manifest layering
        parser.add_argument(
            "--khora-env",
            dest="khora_env",
            type=str,
            default=None,
            help="Specify environment for manifest layering (e.g., 'dev', 'prod')",
        )

        return self

    def activate(self, actions: List[Action]) -> List[Action]:
        """
        Activate extension rules. See :obj:`pyscaffold.actions`.

        This method is called by PyScaffold to activate the extension. It:
        1. Parses the Khora manifest from pyproject.toml
        2. Handles environment-specific configuration layering
        3. Registers actions for context.yaml generation

        Args:
            actions: List of PyScaffold actions to extend

        Returns:
            Extended list of actions

        Raises:
            KhoraExtensionError: If there's a critical error during activation
        """
        # PyScaffold populates `self.opts` with both general scaffold options
        # and extension-specific options before calling `activate`.

        # Log all of self.opts at the beginning of activate
        if hasattr(self, 'opts') and self.opts is not None:
            logger.info(f"CoreExtension.activate: self.opts found. Type: {type(self.opts)}. Content: {self.opts}")
            # Attempt to get specific attributes needed early
            activation_flag = getattr(self.opts, self.name, False)
            project_path_val = getattr(self.opts, 'project_path', None)
            logger.info(f"CoreExtension.activate: self.opts.{self.name} = {activation_flag}, self.opts.project_path = {project_path_val}")
        else:
            logger.error("CRITICAL: self.opts attribute not found or is None on CoreExtension instance when activate() was called.")
            # This is a fatal issue for the extension's logic.
            # We cannot proceed without opts.
            return actions # Exit early

        # Check if the extension was activated.
        # PyScaffold sets opts.<extension_name> (e.g., opts.khora_core) to True if activated by CLI.
        # For programmatic activation (like in `khora create`), this flag should also be set on opts.
        original_activation_status = getattr(self.opts, self.name, False) # self.opts must exist here
        logger.info(f"Debug: Original activation check: self.opts.{self.name} is {original_activation_status}")
        if not original_activation_status:
            logger.info(f"CoreExtension not activating because '{self.name}' is not True in self.opts (value: {original_activation_status}).")
            return actions # Not activated
        # logger.warning("DEBUG: Forcing CoreExtension activation by bypassing the activation check.") # Reverted forced activation

        logger.info("Activating Khora Core Extension...")

        # --- Step 1: Parse the Khora manifest from pyproject.toml ---
        # Use project_path from PyScaffold's opts (e.g., self.opts.project_path)
        project_path_for_manifest = getattr(self.opts, 'project_path', None) # self.opts must exist here
        
        if not isinstance(project_path_for_manifest, Path):
             # If project_path is a string, convert it to Path
            if isinstance(project_path_for_manifest, str):
                project_path_for_manifest = Path(project_path_for_manifest)
            else: # Log error and exit if it's neither Path nor str
                logger.error(
                    "Project path (getattr(self.opts, 'project_path', None)) is not a Path object or string. Cannot parse Khora manifest."
                )
                # No self.opts['khora_parsed_config'] if self.opts is not a dict
                setattr(self.opts, 'khora_parsed_config', None) 
                return actions

        # Get the environment from CLI options if provided (e.g., self.opts.khora_env)
        env = getattr(self.opts, 'khora_env', None) # Use getattr for Namespace
        if env:
            logger.info(f"Using environment '{env}' for manifest layering")

        khora_config = None # Initialize to None
        try:
            # Use the environment-aware method to load the manifest
            khora_config = KhoraManifestConfig.from_project_toml_with_env(
                project_path_for_manifest, env=env
            )

            # Log the active environment if any
            env_status = (
                f" with '{khora_config.active_environment}' environment"
                if khora_config and khora_config.active_environment
                else ""
            )
            logger.info(
                f"Successfully parsed Khora manifest from {project_path_for_manifest / 'pyproject.toml'}{env_status}"
            )
            if khora_config:
                 logger.debug(f"Manifest contents: {khora_config.model_dump(mode='json')}")

            # Logging for Scenario B, Step 1: Verify khora_config and project_path in activate()
            logger.info(f"CoreExtension.activate: project_path_for_manifest being used = {project_path_for_manifest}")
            khora_config_dump = khora_config.model_dump_json(indent=2) if khora_config else "None"
            logger.info(f"CoreExtension.activate: khora_config parsed = {khora_config_dump}")
            
        except KhoraManifestNotFoundError as e:
            logger.warning(
                f"pyproject.toml or [tool.khora] section not found in {project_path_for_manifest}. "
                f"Khora manifest not parsed: {str(e)}"
            )
            if hasattr(e, 'suggestion') and e.suggestion:
                logger.info(f"Suggestion: {e.suggestion}")
            # khora_config remains None
        except KhoraManifestInvalidError as e:
            logger.error(
                f"Invalid Khora manifest in {project_path_for_manifest / 'pyproject.toml'}: {str(e)}"
            )
            if hasattr(e, 'errors') and e.errors:
                for err in e.errors:
                    logger.error(f"  - {err}")
            if hasattr(e, 'suggestion') and e.suggestion:
                logger.info(f"Suggestion: {e.suggestion}")
            # khora_config remains None
        except Exception as e:
            logger.error(
                f"Unexpected error parsing Khora manifest from {project_path_for_manifest / 'pyproject.toml'}: {e}"
            )
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            # khora_config remains None
        
        # Store the parsed config (or None) on self.opts for other actions/extensions to use.
        # Use a distinct attribute name to avoid potential clashes.
        setattr(self.opts, 'khora_parsed_config', khora_config) # Use setattr for Namespace

        # --- Step 2: Register action to generate .khora/context.yaml ---
        try:
            actions = self.register(
                actions, self._generate_khora_context_yaml, after="define_structure"
            )
            logger.info(
                "Khora Core Extension activated and context generation registered."
            )
        except Exception as e:
            error_msg = f"Failed to register context generation action: {e}"
            logger.error(error_msg)
            logger.debug(f"Error traceback: {traceback.format_exc()}")
            # This is a more critical error that affects the core functionality
            raise KhoraExtensionError(error_msg, extension_name="khora_core")
        return actions

    def _generate_kg_summary(self, project_path: Path) -> dict:
        """
        Generate the knowledge graph summary for context.yaml.

        This method checks for kg/concepts.json and kg/rules.json files,
        and if they exist, calculates summary information for them.

        Args:
            project_path: Path to the project root

        Returns:
            Dictionary with KG summary information
        """
        try:
            concepts_file = project_path / "kg" / "concepts.json"
            rules_file = project_path / "kg" / "rules.json"

            # Default values
            kg_summary = {
                "concepts_hash": None,
                "rules_hash": None,
                "relationships_hash": None,
                "concept_count": 0,
                "rule_count": 0,
                "relationship_count": 0,
                "relationship_types": [],
                "source_dir": "kg",
                "last_updated": None,
            }

            # Process concepts file if it exists
            if concepts_file.exists():
                try:
                    import json
                    from hashlib import sha1

                    concepts_data = json.loads(
                        concepts_file.read_text(encoding="utf-8")
                    )
                    concepts = concepts_data.get("concepts", [])

                    kg_summary["concept_count"] = len(concepts)
                    kg_summary["concepts_hash"] = sha1(
                        json.dumps(concepts, sort_keys=True).encode()
                    ).hexdigest()
                    kg_summary["last_updated"] = concepts_data.get("generated_at")

                    logger.info(f"Found {len(concepts)} concepts in {concepts_file}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error processing concepts.json - invalid JSON: {e}")
                    return "Error generating knowledge graph summary"
                except Exception as e:
                    logger.error(f"Error processing concepts.json: {e}")
                    return "Error generating knowledge graph summary"

            # Process rules file if it exists
            if rules_file.exists():
                try:
                    import json
                    from hashlib import sha1

                    rules_data = json.loads(rules_file.read_text(encoding="utf-8"))
                    rules = rules_data.get("rules", [])

                    kg_summary["rule_count"] = len(rules)
                    kg_summary["rules_hash"] = sha1(
                        json.dumps(rules, sort_keys=True).encode()
                    ).hexdigest()

                    # Use rules last_updated if no concepts or if rules are newer
                    rules_updated = rules_data.get("generated_at")
                    if rules_updated and (
                        not kg_summary["last_updated"]
                        or rules_updated > kg_summary["last_updated"]
                    ):
                        kg_summary["last_updated"] = rules_updated

                    logger.info(f"Found {len(rules)} rules in {rules_file}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error processing rules.json - invalid JSON: {e}")
                    return "Error generating knowledge graph summary"
                except Exception as e:
                    logger.error(f"Error processing rules.json: {e}")
                    return "Error generating knowledge graph summary"

            # Process relationships file if it exists
            relationships_file = project_path / "kg" / "relationships.json"
            if relationships_file.exists():
                try:
                    import json
                    from hashlib import sha1

                    relationships_data = json.loads(
                        relationships_file.read_text(encoding="utf-8")
                    )
                    relationships = relationships_data.get("relationships", [])

                    kg_summary["relationship_count"] = len(relationships)
                    kg_summary["relationships_hash"] = sha1(
                        json.dumps(relationships, sort_keys=True).encode()
                    ).hexdigest()

                    # Extract unique relationship types
                    if relationships:
                        relation_types = set()
                        for rel in relationships:
                            if "relation_type" in rel:
                                relation_types.add(rel["relation_type"])
                        kg_summary["relationship_types"] = sorted(list(relation_types))

                    # Use relationships last_updated if it's newer than concepts and rules
                    relationships_updated = relationships_data.get("generated_at")
                    if relationships_updated and (
                        not kg_summary["last_updated"]
                        or relationships_updated > kg_summary["last_updated"]
                    ):
                        kg_summary["last_updated"] = relationships_updated

                    logger.info(
                        f"Found {len(relationships)} relationships in {relationships_file}"
                    )
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Error processing relationships.json - invalid JSON: {e}"
                    )
                    return "Error generating knowledge graph summary"
                except Exception as e:
                    logger.error(f"Error processing relationships.json: {e}")
                    return "Error generating knowledge graph summary"

            # If we found either concepts or rules, return the summary
            if kg_summary["concept_count"] > 0 or kg_summary["rule_count"] > 0:
                return kg_summary

            # If KG files don't exist yet (or are empty), use the data from opts if available
            concepts = []
            rules = []
            relationships = []

            # Check if self.opts is available
            if hasattr(self, "opts") and self.opts:
                concepts = getattr(self.opts, "kg_concepts", []) # Use getattr
                rules = getattr(self.opts, "kg_rules", [])       # Use getattr
                relationships = getattr(self.opts, "kg_relationships", []) # Use getattr

                # Get relationship summary if available
                rel_summary = getattr(self.opts, "kg_relationship_summary", {}) # Use getattr
                if rel_summary: # rel_summary is a dict, so .get() is fine here
                    kg_summary["relationship_count"] = rel_summary.get("count", 0)
                    kg_summary["relationship_types"] = rel_summary.get("types", [])

            if concepts or rules or relationships:
                import json
                from hashlib import sha1
                from datetime import datetime, timezone

                kg_summary["concept_count"] = len(concepts)
                if concepts:
                    concept_dicts = [c.to_dict() for c in concepts]
                    kg_summary["concepts_hash"] = sha1(
                        json.dumps(concept_dicts, sort_keys=True).encode()
                    ).hexdigest()

                kg_summary["rule_count"] = len(rules)
                if rules:
                    rule_dicts = [r.to_dict() for r in rules]
                    kg_summary["rules_hash"] = sha1(
                        json.dumps(rule_dicts, sort_keys=True).encode()
                    ).hexdigest()

                kg_summary["relationship_count"] = len(relationships)
                if relationships:
                    relationship_dicts = [r.to_dict() for r in relationships]
                    kg_summary["relationships_hash"] = sha1(
                        json.dumps(relationship_dicts, sort_keys=True).encode()
                    ).hexdigest()

                    # Extract relationship types if not already provided in summary
                    if not kg_summary["relationship_types"] and relationships:
                        relation_types = set()
                        for rel in relationships:
                            relation_types.add(rel.relation_type)
                        kg_summary["relationship_types"] = sorted(list(relation_types))

                kg_summary["last_updated"] = datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                )

                logger.info(
                    f"Using {len(concepts)} concepts, {len(rules)} rules, and "
                    f"{len(relationships)} relationships from extraction results"
                )
                return kg_summary

            # If no KG data found at all, return a simple placeholder
            return "No knowledge graph data available"

        except Exception as e:
            logger.error(f"Error generating KG summary: {e}")
            return "Error generating knowledge graph summary"

    def _generate_khora_context_yaml(
        self, struct: Structure, opts: ScaffoldOpts
    ) -> ActionParams:
        """
        Generates the .khora/context.yaml file based on the parsed manifest
        and kernel information.

        Args:
            struct: PyScaffold structure to update
            opts: PyScaffold options

        Returns:
            Updated structure and options

        Raises:
            KhoraContextError: If there's a critical error in context generation
        """
        logger.info("Generating .khora/context.yaml...")

        # Logging for Scenario B, Step 3: Verify self.opts in _generate_khora_context_yaml
        # Retrieve the parsed config and project path from opts.
        # opts can be a Namespace (during activate) or a dict (during action execution by PyScaffold).
        if isinstance(opts, dict):
            khora_config: Optional[KhoraManifestConfig] = opts.get('khora_parsed_config')
            current_project_path: Optional[Path] = opts.get('project_path')
            activated_khora_env: Optional[str] = opts.get('khora_env')
            project_name_from_main_opts = opts.get('name')
            component_info = opts.get("component_info", {})
        else: # Assume Namespace or similar object
            khora_config: Optional[KhoraManifestConfig] = getattr(opts, 'khora_parsed_config', None)
            current_project_path: Optional[Path] = getattr(opts, 'project_path', None)
            activated_khora_env: Optional[str] = getattr(opts, 'khora_env', None)
            project_name_from_main_opts = getattr(opts, 'name', None)
            component_info = getattr(opts, "component_info", {})

        # Ensure current_project_path is a Path object
        if not isinstance(current_project_path, Path):
            if isinstance(current_project_path, str):
                current_project_path = Path(current_project_path)
            else:
                error_msg = "CoreExtension: opts.project_path is not a Path object or string. Cannot generate context.yaml."
                logger.error(error_msg)
                logger.error(f"CoreExtension._generate_khora_context_yaml: opts state = {opts}")
                return struct, opts # Critical error
        
        if not project_name_from_main_opts: # Fallback if name wasn't in opts
             project_name_from_main_opts = current_project_path.name


        logger.info(f"CoreExtension._generate_khora_context_yaml: khora_parsed_config from opts = {khora_config.model_dump_json(indent=2) if khora_config else 'None'}")
        logger.info(f"CoreExtension._generate_khora_context_yaml: current_project_path from opts = {current_project_path}")


        if not current_project_path: # Should have been caught by the Path type check, but as a safeguard
            error_msg = "CoreExtension: project_path (from opts) is None. Cannot generate context.yaml."
            logger.error(error_msg)
            return struct, opts # Critical error, stop processing by this action

        # Use the 'name' from PyScaffold's opts, which is the official project name.
        # project_name_from_main_opts is already derived above.


        if not khora_config:
            logger.warning(
                f"Khora manifest config (khora_parsed_config) not found or failed to parse for project {project_name_from_main_opts}. "
                "Generating .khora/context.yaml with minimal/default information."
            )
            # Fallback values if manifest is missing or invalid
            project_description = "N/A (Khora manifest not found or invalid)"
            project_paths_data = {}
        else:
            project_description = str(khora_config.project_description) if khora_config.project_description is not None else "N/A"
            project_paths_data = (
                khora_config.paths.model_dump(mode="json") if khora_config.paths else {}
            )

        # Read kernel version
        try:
            version_file_path = (
                Path(__file__).resolve().parent.parent.parent / "_internal" / "VERSION"
            )
            kernel_version = version_file_path.read_text(encoding="utf-8").strip()
        except OSError as e:
            logger.error(f"Failed to read kernel VERSION file: {e}")
            kernel_version = "UNKNOWN"
        except Exception as e:
            logger.error(f"Unexpected error reading VERSION file: {e}")
            kernel_version = "ERROR"

        schema_version = "0.1.0"  # For MVK
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # component_info is already derived above based on opts type

        # Build the context data dictionary
        try:
            # Extract templates info if available
            templates_data = {}
            if khora_config and hasattr(khora_config, 'templates') and khora_config.templates:
                try:
                    if hasattr(khora_config.templates, "model_dump"):
                        templates_data = khora_config.templates.model_dump(mode="json")
                    elif isinstance(khora_config.templates, dict):
                        import json
                        templates_data = json.loads(json.dumps(khora_config.templates))
                    else:
                        logger.warning(f"Unexpected type for khora_config.templates: {type(khora_config.templates)}. Attempting direct use or empty.")
                        templates_data = khora_config.templates if isinstance(khora_config.templates, (dict, list)) else {}
                    logger.debug(f"Found template data: {templates_data}")
                except Exception as e:
                    logger.error(f"Failed to extract and process template information: {e}")
                    templates_data = {"error": f"Failed to process template data: {str(e)}"}

            # Prepare the manifest part for context.yaml
            manifest_for_context = {}
            if khora_config:
                # KhoraManifestConfig itself represents the [tool.khora] section.
                # We need to ensure active_environment is correctly set here if an env was applied.
                dumped_manifest = khora_config.model_dump(mode="json")
                if activated_khora_env and dumped_manifest.get("active_environment") is None:
                    # If KhoraManifestConfig didn't set active_environment, but an env was used, set it now.
                    dumped_manifest["active_environment"] = activated_khora_env
                manifest_for_context = {"tool": {"khora": dumped_manifest}}
            else:
                manifest_for_context = {"tool": {"khora": {"error": "Khora manifest not parsed or invalid"}}}

            context_data = {
                "kernel_version": kernel_version,
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "project": {
                    "name": str(project_name_from_main_opts),
                    "description": project_description,
                    "paths": project_paths_data,
                    "templates": templates_data, # This was already here
                },
                "manifest": manifest_for_context, # Add the manifest structure
                "knowledge_graph_summary": self._generate_kg_summary(current_project_path),
                "components": component_info,
            }

            # Add/Update environment information based on activated_khora_env from opts
            if activated_khora_env:
                context_data["environment"] = {
                    "name": activated_khora_env,
                    "applied": True, # Assume applied if env was passed and processed
                    "description": f"Configuration using '{activated_khora_env}' environment overrides",
                }
            # If khora_config.active_environment was correctly set by KhoraManifestConfig,
            # it would also be present in context_data["manifest"]["tool"]["khora"]["active_environment"]
        except Exception as e:
            error_msg = f"Failed to build context data: {e}"
            logger.error(error_msg)
            logger.debug(f"Error details: {traceback.format_exc()}")
            raise KhoraContextError(error_msg)

        try:
            # Use sort_keys=False to maintain insertion order if desired, though not critical for YAML
            # Dumper options can be added if specific formatting is needed (e.g., default_flow_style)
            context_yaml_content = yaml.safe_dump(context_data, sort_keys=False, indent=2)
            logger.debug(
                f"Generated context.yaml content:\n{context_yaml_content.strip()}"
            )
        except Exception as e:
            error_msg = f"Failed to serialize context.yaml data to YAML: {e}"
            logger.error(error_msg)
            logger.debug(f"Error details: {traceback.format_exc()}")

            # Create a placeholder or error content if YAML generation fails
            context_yaml_content = (
                f"# Error generating context.yaml content: {e}\n"
                f"# Generated at: {datetime.now(timezone.utc).isoformat()}\n"
                f"# Raw data: {context_data}\n"
                f"# This error indicates a problem with YAML serialization, not with your project configuration.\n"
                f"# Please report this issue to the Khora maintainers."
            )

        khora_files: Structure = {
            # PyScaffold will create .khora directory if it doesn't exist
            # when merging this structure.
            ".khora": {
                "context.yaml": (
                    context_yaml_content,
                    no_overwrite(),
                )  # no_overwrite is a sensible default
            }
        }

        # Ensure .khora directory and context.yaml are created
        # The merge operation with ensure_existence (default for files) handles this.
        # We can also explicitly use ensure_existence if there are concerns.
        # struct = ensure_existence(struct, opts) # Usually done by PyScaffold before custom actions like this one.

        logger.info(
            f"Merging .khora/context.yaml into project structure for {project_name_from_main_opts}"
        )
        struct.update(khora_files)  # Use dict.update() to merge
        return struct, opts

```

## khora-kernel/src/khora_kernel/extensions/core/manifest.py  
`14084 bytes`  ·  `3f19ab1`  
```python
"""
Parses and validates the [tool.khora] section of a pyproject.toml file.
"""

import tomllib  # Requires Python 3.11+
from pathlib import Path
from typing import Any, Dict, Optional, Union, List

from pydantic import (
    BaseModel,
    Field,
    FilePath,
    HttpUrl,
    ValidationError,
    DirectoryPath,
    # field_validator, # Will use model_validator instead for cross-field
    model_validator,  # Added for Pydantic V2 style model validation
    # constr, # Will be replaced by Field constraints
    PositiveInt,
    # FieldValidationInfo, # May not be needed with model_validator
)


# Utility functions
def deep_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge override dict into base dict.

    Args:
        base: Base dictionary that will be updated
        override: Dictionary with values to override or extend base

    Returns:
        A new dictionary with merged values from both inputs
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # If both values are dictionaries, merge them recursively
            result[key] = deep_merge_dicts(result[key], value)
        else:
            # Otherwise, simply override the value
            result[key] = value
    return result


# Custom Exceptions
class KhoraManifestError(Exception):
    """Base exception for Khora manifest errors."""


class KhoraManifestNotFoundError(KhoraManifestError):
    """Raised when pyproject.toml or [tool.khora] section is not found."""


class KhoraManifestInvalidError(KhoraManifestError):
    """Raised when the Khora manifest has validation errors."""

    def __init__(self, errors: Any):
        self.errors = errors
        super().__init__(f"Invalid Khora manifest: {errors}")


# Pydantic Models for [tool.khora]
class KhoraTemplateConfig(BaseModel):
    paths: List[str] = Field(default_factory=list)
    engine: Optional[str] = None
    overrides: Dict[str, Any] = Field(default_factory=dict)

class KhoraPathsConfig(BaseModel):
    api_dir: Optional[Path] = None
    docs_dir: Optional[Path] = Path("docs")


class KhoraFeaturesConfig(BaseModel):
    fastapi: bool = False
    docker: bool = False
    ci_github_actions: bool = False
    # Phase 2 features
    database: str = "none"  # Options: "postgres", "sqlite", "none"
    broker: str = "none"  # Options: "redis", "none"
    security_gates: bool = False
    kg: bool = False  # Knowledge Graph feature
    precommit: bool = False  # Precommit hooks feature
    # Phase 3 features
    playwright: bool = False  # UI testing with Playwright
    terraform: bool = False  # Terraform IaC scaffolding
    observability: bool = False  # Observability stack in docker-compose


class KhoraPortsConfig(BaseModel):
    http: PositiveInt = 8000


class KhoraDockerPluginConfig(BaseModel):
    api_service_name: str = "api"


# Forward declaration for KhoraPluginsConfig if GitHubIssuesManagerConfig is defined below it,
# or ensure GitHubIssuesManagerConfig is imported/defined before KhoraPluginsConfig.
# For this case, we will import it.
from khora_kernel.extensions.github_issues_manager.config import GitHubIssuesManagerConfig


class KhoraPluginsConfig(BaseModel):
    docker: KhoraDockerPluginConfig = Field(default_factory=KhoraDockerPluginConfig)
    github_issues_manager: Optional[GitHubIssuesManagerConfig] = Field(
        default=None, description="Configuration for the GitHub Issues Manager plugin."
    )


class KhoraManifestConfig(BaseModel):
    """
    Represents the [tool.khora] section in pyproject.toml.
    """

    project_name: str = Field(..., min_length=1, description="The name of the project.")
    project_description: Optional[str] = Field(
        None, description="A short description of the project."
    )
    python_version: str = Field(
        pattern=r"^\d+\.\d+$",
        description="Python version for the project, e.g., '3.10'.",
    )

    paths: KhoraPathsConfig = Field(default_factory=KhoraPathsConfig)
    features: KhoraFeaturesConfig = Field(default_factory=KhoraFeaturesConfig)
    ports: KhoraPortsConfig = Field(default_factory=KhoraPortsConfig)
    plugins_config: KhoraPluginsConfig = Field(default_factory=KhoraPluginsConfig)
    templates: Optional[KhoraTemplateConfig] = Field(default=None) # Added templates field
    settings: Dict[str, Any] = Field(default_factory=dict) # Added settings field

    # Environment-specific configuration active during this config's creation
    active_environment: Optional[str] = Field(
        None,
        description="The active environment used when generating this configuration.",
    )

    @model_validator(mode="after")
    def validate_api_dir_based_on_fastapi_feature(cls, data: Any) -> Any:
        if isinstance(
            data, KhoraManifestConfig
        ):  # Ensure we operate on the model instance
            if data.features.fastapi and data.paths.api_dir is None:
                raise ValueError(
                    "'paths.api_dir' must be specified when 'features.fastapi' is true."
                )
        return data

    @classmethod
    def from_project_toml(
        cls, project_dir: Union[str, Path] = "."
    ) -> "KhoraManifestConfig":
        """
        Loads and parses the Khora manifest configuration from the pyproject.toml
        file in the given project directory.

        Args:
            project_dir: The root directory of the project. Defaults to current dir.

        Returns:
            An instance of KhoraManifestConfig.

        Raises:
            KhoraManifestNotFoundError: If pyproject.toml or [tool.khora] is missing.
            KhoraManifestInvalidError: If the manifest data is invalid.
        """
        return cls.from_project_toml_with_env(project_dir, env=None)

    @classmethod
    def from_project_toml_with_env(
        cls, project_dir: Union[str, Path] = ".", env: Optional[str] = None
    ) -> "KhoraManifestConfig":
        """
        Loads and parses the Khora manifest configuration from the pyproject.toml
        file in the given project directory, with optional environment-specific overrides.

        Args:
            project_dir: The root directory of the project. Defaults to current dir.
            env: The environment name to load overrides from (e.g., 'dev', 'prod').
                 If None, only the base configuration is loaded.

        Returns:
            An instance of KhoraManifestConfig with environment overrides applied if specified.

        Raises:
            KhoraManifestNotFoundError: If pyproject.toml or [tool.khora] is missing.
            KhoraManifestInvalidError: If the manifest data is invalid.
        """
        pyproject_path = Path(project_dir) / "pyproject.toml"

        if not pyproject_path.is_file():
            raise KhoraManifestNotFoundError(
                f"pyproject.toml not found in {project_dir}"
            )

        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            # Wrap the TOMLDecodeError in a structure similar to Pydantic's validation errors
            # for consistency in how KhoraManifestInvalidError.errors is structured.
            error_detail = {
                "type": "toml_decode_error",
                "loc": ("pyproject.toml",),  # General location
                "msg": str(e),
                "input": pyproject_path.read_text(),  # Include file content for context if possible
            }
            raise KhoraManifestInvalidError([error_detail])

        khora_config_data = data.get("tool", {}).get("khora")
        if khora_config_data is None:
            raise KhoraManifestNotFoundError(
                "[tool.khora] section not found in pyproject.toml"
            )

        try:
            # Handle project_name from [project] section if not in [tool.khora]
            if (
                "project_name" not in khora_config_data
                and "project" in data
                and "name" in data["project"]
            ):
                # If not in [tool.khora] but present in [project], use that.
                # This is a common pattern.
                khora_config_data["project_name"] = data["project"]["name"]

            # Create a copy of the base config data
            base_config_data = dict(khora_config_data)

            # Apply environment-specific overrides if specified
            if env is not None:
                # Get environment-specific section from "environments" sub-table
                env_specific_configs = khora_config_data.get("environments", {})
                env_section = env_specific_configs.get(env)
                
                if env_section:
                    # Deep merge environment config into base config
                    # base_config_data already contains the full [tool.khora]
                    # env_section contains only the overrides for the specific environment
                    merged_config_data = deep_merge_dicts(base_config_data, env_section)
                    
                    # Remove the "environments" table itself from the merged data
                    # as it's not part of the KhoraManifestConfig model fields directly at the root
                    if "environments" in merged_config_data:
                        del merged_config_data["environments"]
                    
                    # Set the active environment
                    merged_config_data["active_environment"] = env
                    return cls(**merged_config_data)
                else:
                    # Environment specified but not found - use base config but mark active_environment as None
                    # and remove "environments" table if it exists in base_config_data
                    if "environments" in base_config_data:
                        del base_config_data["environments"]
                    base_config_data["active_environment"] = None # Explicitly set for clarity
                    return cls(**base_config_data)

            # If no environment 'env' was specified, process base_config_data
            # Remove "environments" table if it exists, as it's not a direct field
            if "environments" in base_config_data:
                del base_config_data["environments"]
            # active_environment will be None by Pydantic default or if explicitly set above
            return cls(**base_config_data)
        except ValidationError as e:
            raise KhoraManifestInvalidError(e.errors())
        except (
            TypeError
        ) as e:  # Catches issues like missing required fields not caught by ValidationError directly
            raise KhoraManifestInvalidError(
                f"Missing or malformed fields in [tool.khora]: {e}"
            )


if __name__ == "__main__":
    # Example usage (for testing purposes)
    # Create a dummy pyproject.toml for testing
    dummy_toml_content = """
[project]
name = "my-test-project"
version = "0.1.0"
description = "A test project."

[tool.khora]
project_name = "MyKhoraTestProject" # Explicitly defined for Khora
project_description = "This is a Khora-managed test project."
python_version = "3.11"

[tool.khora.paths]
api_dir = "src/my_test_project/api"
docs_dir = "docs"

[tool.khora.features]
fastapi = true
docker = true
ci_github_actions = false

[tool.khora.ports]
http = 8080

[tool.khora.plugins_config.docker]
api_service_name = "test_api_service"
"""
    dummy_pyproject_path = Path("dummy_pyproject.toml")
    with open(dummy_pyproject_path, "w") as f:
        f.write(dummy_toml_content)

    print(f"Attempting to load from: {dummy_pyproject_path.resolve()}")
    try:
        config = KhoraManifestConfig.from_project_toml(
            project_dir="."
        )  # Reading from where dummy is
        print("\\nSuccessfully parsed manifest:")
        print(config.model_dump_json(indent=2))

        # Test conditional validation: FastAPI enabled but no api_dir
        faulty_toml_content_no_api_dir = """
[project]
name = "faulty-project"
[tool.khora]
project_name = "FaultyProject"
python_version = "3.9"
[tool.khora.features]
fastapi = true
# api_dir is missing
"""
        faulty_pyproject_path = Path("faulty_pyproject.toml")
        with open(faulty_pyproject_path, "w") as f:
            f.write(faulty_toml_content_no_api_dir)
        print(
            f"\\nAttempting to load faulty manifest (missing api_dir): {faulty_pyproject_path.resolve()}"
        )
        try:
            KhoraManifestConfig.from_project_toml(
                project_dir="."
            )  # Reading from where faulty is
        except KhoraManifestInvalidError as e:
            print(f"Caught expected error for missing api_dir: {e.errors}")

        # Test missing mandatory field (e.g. python_version)
        faulty_toml_missing_py_version = """
[project]
name = "faulty-project-py"
[tool.khora]
project_name = "FaultyProjectPy"
# python_version is missing
"""
        faulty_pyproject_path_py = Path("faulty_pyproject_py.toml")
        with open(faulty_pyproject_path_py, "w") as f:
            f.write(faulty_toml_missing_py_version)

        print(
            f"\\nAttempting to load faulty manifest (missing python_version): {faulty_pyproject_path_py.resolve()}"
        )
        try:
            KhoraManifestConfig.from_project_toml(
                project_dir="."
            )  # Reading from where faulty is
        except KhoraManifestInvalidError as e:
            print(f"Caught expected error for missing python_version: {e.errors}")

    except KhoraManifestError as e:
        print(f"Error parsing manifest: {e}")
    finally:
        # Clean up dummy files
        if dummy_pyproject_path.exists():
            dummy_pyproject_path.unlink()
        if faulty_pyproject_path.exists():
            faulty_pyproject_path.unlink()
        if faulty_pyproject_path_py.exists():
            faulty_pyproject_path_py.unlink()

```

## khora-kernel/src/khora_kernel/extensions/docker/extension.py  
`11489 bytes`  ·  `24d57b9`  
```python
import argparse
import logging
from pathlib import Path

from pyscaffold.actions import Action, ActionParams, ScaffoldOpts, Structure
from pyscaffold.extensions import Extension
from pyscaffold.operations import no_overwrite
from pyscaffold.templates import get_template

_logger = logging.getLogger(__name__)


class DockerExtension(Extension):
    """Generates a docker-compose.yml file for the project."""

    name = "khora_docker"  # kebab-case for the CLI flag

    def augment_cli(self, parser: argparse.ArgumentParser):
        """Add a CLI option for this extension"""
        parser.add_argument(
            self.flag,  # self.flag is derived from self.name
            dest=self.name,
            action="store_true",
            default=False,
            help="Add Docker containerization to the project",
        )
        return self

    def activate(self, actions: list[Action]) -> list[Action]:
        """Activate extension rules. See :obj:`pyscaffold.actions.Action`."""

        # Ensure self.opts exists before trying to access attributes
        if not hasattr(self, 'opts') or self.opts is None:
            _logger.error(f"DockerExtension: self.opts not set when activate() called. Skipping activation.")
            return actions

        # Check if the extension was activated via CLI flag or programmatically
        if not getattr(self.opts, self.name, False): # Use getattr for Namespace
            _logger.info(f"DockerExtension not activating because '{self.name}' is not True in self.opts.")
            return actions
        
        _logger.info("Activating Khora Docker Extension...")

        actions = self.register(
            actions, add_docker_compose_file, after="define_structure"
        )
        return actions


def add_docker_compose_file(struct: Structure, opts: ScaffoldOpts) -> ActionParams:
    """Add the docker-compose.yml file to the project structure.

    Args:
        struct: project representation as (possibly) nested :obj:`dict`.
        opts: given options, see :obj:`create_project` for an example.

    Returns:
        Project structure and options
    """
    # Get the Pydantic model from opts, which CoreExtension stores as 'khora_parsed_config'
    # opts can be a Namespace or a dict.
    if isinstance(opts, dict):
        khora_config = opts.get("khora_parsed_config")
    else:
        khora_config = getattr(opts, "khora_parsed_config", None)

    if not khora_config:
        _logger.warning(
            "Khora manifest config (khora_parsed_config) not found in opts. Skipping docker-compose.yml generation."
        )
        return struct, opts

    # Check if the docker feature is enabled
    if not getattr(khora_config.features, "docker", False):
        _logger.info(
            "Khora Docker feature not enabled. Skipping docker-compose.yml generation."
        )
        return struct, opts

    # Get paths and other config from khora_config
    api_dir = getattr(
        khora_config.paths, "api_dir", "api"
    )  # Default to 'api' if not specified
    http_port = getattr(khora_config.ports, "http", 8000)  # Default to 8000

    # Get Docker-specific config
    docker_config = getattr(khora_config.plugins_config, "docker", {})
    api_service_name = getattr(
        docker_config, "api_service_name", "api"
    )  # Default to 'api'

    # Get database, broker and observability features
    database = getattr(khora_config.features, "database", "none")
    broker = getattr(khora_config.features, "broker", "none")
    observability = getattr(khora_config.features, "observability", False)

    # Prepare environment variables and service dependencies for the API service
    api_env_vars = ""
    api_depends_on = ""
    depends_list = []  # Track dependencies

    # Prepare PostgreSQL or SQLite configuration
    postgres_service = ""
    volumes = ""

    if database == "postgres":
        # Add PostgreSQL service
        postgres_service = """postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app_db
    ports:
      - "5432:5432"
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5"""

        # Add volume for PostgreSQL
        volumes = "volumes:\n  db-data:"

        # Add dependency for API service
        depends_list.append("postgres")

        # Add DATABASE_URL environment variable
        api_env_vars += """environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/app_db"""

    elif database == "sqlite":
        # For SQLite, add a volume and mount point
        volumes = "volumes:\n  db-data:"

        # Updating mounts for API service
        api_env_vars += """environment:
      DATABASE_URL: sqlite:////app/data/local.db
    volumes:
      - ./${api_dir}:/app/${api_dir}
      - db-data:/app/data"""

    # Prepare Redis broker configuration
    redis_service = ""

    if broker == "redis":
        # Add Redis service
        redis_service = """redis:
    image: redis:7
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5"""

        # Add dependency for API service
        depends_list.append("redis")

        # Add REDIS_URL environment variable
        if api_env_vars:
            # If environment block already exists, just add the variable
            api_env_vars = api_env_vars.replace(
                "environment:", "environment:\n      REDIS_URL: redis://redis:6379/0"
            )
        else:
            # Otherwise, create the environment block
            api_env_vars += """environment:
      REDIS_URL: redis://redis:6379/0"""

    # Prepare observability stack configuration
    otel_collector_service = ""
    prometheus_service = ""
    grafana_service = ""

    if observability:
        # Add OpenTelemetry Collector service
        otel_collector_service = """otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "4317"]
      interval: 10s
      timeout: 5s
      retries: 5"""

        # Add Prometheus service
        prometheus_service = """prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    healthcheck:
      test: ["CMD", "wget", "-q", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
      interval: 10s
      timeout: 5s
      retries: 5
    depends_on:
      - otel-collector"""

        # Add Grafana service
        grafana_service = """grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus"""

        # Add dependencies for API service
        depends_list.append("otel-collector")

        # Add OTEL environment variables
        if api_env_vars:
            # If environment block already exists, just add the variables
            otel_vars = """
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: ${api_service_name}
      OTEL_TRACES_EXPORTER: otlp
      OTEL_METRICS_EXPORTER: otlp
      OTEL_LOGS_EXPORTER: otlp"""
            api_env_vars = api_env_vars.replace(
                "environment:", f"environment:{otel_vars}"
            )
        else:
            # Otherwise, create the environment block with OTEL variables
            api_env_vars += """environment:
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: ${api_service_name}
      OTEL_TRACES_EXPORTER: otlp
      OTEL_METRICS_EXPORTER: otlp
      OTEL_LOGS_EXPORTER: otlp"""

        # Add volumes for Prometheus and Grafana data
        if volumes:
            # If volumes section already exists, add to it
            volumes += "\n  prometheus-data:\n  grafana-data:"
        else:
            # Otherwise, create the volumes section
            volumes = "volumes:\n  prometheus-data:\n  grafana-data:"

    # Build depends_on section if we have dependencies
    if depends_list:
        api_depends_on = "depends_on:\n"
        for dep in depends_list:
            api_depends_on += f"      - {dep}\n"

    # Template for docker-compose.yml
    docker_compose_template = get_template(
        "docker_compose_yml", relative_to="khora_kernel.extensions.docker"
    )

    # Get the project name from khora_config or fall back to opts['name']
    project_name = getattr(khora_config, "project_name", None)
    if not project_name:
        project_name = getattr(opts, "name", "khora-project") if not isinstance(opts, dict) else opts.get("name", "khora-project")
        _logger.info(f"Using project name from PyScaffold opts: {project_name}")

    docker_compose_content = docker_compose_template.substitute(
        api_dir=api_dir,
        http_port=http_port,
        api_service_name=api_service_name,
        project_name=project_name,  # Use the project name we got from config or opts
        api_env_vars=api_env_vars,
        api_depends_on=api_depends_on,
        postgres_service=postgres_service,
        redis_service=redis_service,
        otel_collector_service=otel_collector_service,
        prometheus_service=prometheus_service,
        grafana_service=grafana_service,
        volumes=volumes,
    )

    # Add the docker-compose.yml to the root of the project
    struct["docker-compose.yml"] = (docker_compose_content, no_overwrite())

    _logger.info(
        f"Generated docker-compose.yml for service '{api_service_name}' in '{api_dir}' on port {http_port}."
    )

    # Generate observability config files if the feature is enabled
    if observability:
        # Generate Prometheus config
        prometheus_config = """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']
        
  - job_name: 'api'
    static_configs:
      - targets: ['${api_service_name}:${http_port}/metrics']
"""
        struct["prometheus.yml"] = (prometheus_config, no_overwrite())

        # Generate OpenTelemetry Collector config
        otel_collector_config = """
receivers:
  otlp:
    protocols:
      grpc:
      http:

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
    namespace: "${project_name}"
    
  logging:
    loglevel: info
    
  otlp:
    endpoint: "jaeger:4317"
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging, otlp]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging, prometheus]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging]
"""
        struct["otel-collector-config.yaml"] = (otel_collector_config, no_overwrite())

        _logger.info("Generated observability configuration files.")

    return struct, opts

```

## khora-kernel/src/khora_kernel/extensions/fastapi_scaffold/extension.py  
`15942 bytes`  ·  `ef97e0b`  
```python
"""
FastAPI Scaffolding Extension for Khora Kernel.

This extension generates a basic FastAPI application structure if requested
in the [tool.khora.features] section of the target project's pyproject.toml.
It also contributes API component information for context.yaml enrichment.
"""

import argparse
import ast
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import os

from pyscaffold.actions import Action, ActionParams, ScaffoldOpts, Structure
from pyscaffold.extensions import Extension
from pyscaffold.operations import no_overwrite  # 'define' was unused

# The ensure_parent_dir_exists function doesn't exist in PyScaffold
from pyscaffold.templates import get_template

# Assuming khora manifest parsing logic is available.
# This might need to be adjusted based on where MVK-CORE-01 placed it.
# For now, let's assume a utility function or class exists.
# from khora_kernel.manifest import KhoraManifestParser # Placeholder

LOG = logging.getLogger(__name__)

DEFAULT_API_DIR = "api"
# PyScaffold's get_template function automatically adds ".template" to the filename,
# so we need to specify just the base name without ".template"
MAIN_PY_TEMPLATE = get_template(
    "main_py", relative_to="khora_kernel.extensions.fastapi_scaffold.templates"
)
REQUIREMENTS_TXT_TEMPLATE = get_template(
    "requirements_txt", relative_to="khora_kernel.extensions.fastapi_scaffold.templates"
)
DOCKERFILE_TEMPLATE = get_template(
    "dockerfile_j2", relative_to="khora_kernel.extensions.fastapi_scaffold.templates"
)


def analyze_fastapi_endpoints(code_str: str) -> List[Dict[str, Any]]:
    """
    Analyze FastAPI code using AST to extract endpoint information.

    Args:
        code_str: String containing the FastAPI application code

    Returns:
        List of dictionaries containing endpoint information
    """
    endpoints = []

    try:
        # Parse the code into an AST
        tree = ast.parse(code_str)

        # Find decorated functions that might be FastAPI endpoints
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    # Check if decorator is an app method call (e.g., @app.get)
                    if (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Attribute)
                        and isinstance(decorator.func.value, ast.Name)
                        and decorator.func.value.id == "app"
                    ):

                        http_method = (
                            decorator.func.attr.lower()
                        )  # get, post, put, etc.

                        # Get path from the first argument if available
                        path = "/"
                        if decorator.args:
                            # Try to get the string value - use ast.Constant instead of ast.Str (Python 3.8+)
                            if isinstance(
                                decorator.args[0], ast.Constant
                            ) and isinstance(decorator.args[0].value, str):
                                path = decorator.args[0].value
                            # Fallback for older Python versions
                            elif isinstance(decorator.args[0], ast.Str):
                                path = decorator.args[0].s

                        # Extract other metadata from decorator keywords
                        tags = []
                        summary = None
                        description = None

                        for keyword in decorator.keywords:
                            if keyword.arg == "tags" and isinstance(
                                keyword.value, ast.List
                            ):
                                for elt in keyword.value.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(
                                        elt.value, str
                                    ):
                                        tags.append(elt.value)
                                    # Fallback for older Python versions
                                    elif isinstance(elt, ast.Str):
                                        tags.append(elt.s)
                            elif keyword.arg == "summary":
                                if isinstance(
                                    keyword.value, ast.Constant
                                ) and isinstance(keyword.value.value, str):
                                    summary = keyword.value.value
                                # Fallback for older Python versions
                                elif isinstance(keyword.value, ast.Str):
                                    summary = keyword.value.s

                        # Try to get docstring for description
                        if ast.get_docstring(node):
                            description = ast.get_docstring(node)

                        endpoint_info = {
                            "path": path,
                            "method": http_method,
                            "name": node.name,
                            "tags": tags,
                            "summary": summary,
                            "description": description,
                        }

                        endpoints.append(endpoint_info)

        return endpoints
    except Exception as e:
        LOG.error(f"Error analyzing FastAPI endpoints: {e}")
        return []


def extract_fastapi_components(
    template_content: str | object, opts: ScaffoldOpts
) -> Dict[str, Any]:
    """
    Extract FastAPI component information from template content and format for context.yaml.

    Args:
        template_content: String containing the FastAPI template content or a Template object
        opts: ScaffoldOpts containing configuration information

    Returns:
        Dictionary containing FastAPI component information
    """
    # Process template to get actual code that will be generated
    # Handle both string and Template objects
    if hasattr(template_content, "template"):
        # It's a Template object
        code_str = template_content.template
    elif isinstance(template_content, str):
        code_str = template_content
    else:
        # If we can't determine what it is, return a basic structure
        return {"type": "fastapi", "api_info": {"endpoints_count": 0, "endpoints": []}}

    # Replace template variables with placeholder values for AST parsing
    # This is a basic implementation; might need more sophisticated template processing
    code_str = code_str.replace("{{ opts.project_path.name }}", "ProjectName")
    code_str = code_str.replace("{{ opts.version }}", "0.1.0")
    code_str = code_str.replace("{{ opts.description }}", "API Description")

    # Extract endpoints
    endpoints = analyze_fastapi_endpoints(code_str)

    # Format components for context.yaml
    fastapi_components = {
        "type": "fastapi",
        "api_info": {"endpoints_count": len(endpoints), "endpoints": endpoints},
    }

    return fastapi_components


def fastapi_context_contribution(struct: Structure, opts: ScaffoldOpts) -> ActionParams:
    """
    Action to contribute FastAPI component information to opts for context.yaml generation.
    """
    if isinstance(opts, dict):
        khora_config = opts.get("khora_parsed_config")
    else:
        khora_config = getattr(opts, "khora_parsed_config", None)

    if not khora_config or not getattr(khora_config.features, "fastapi", False):
        # FastAPI not enabled, nothing to contribute
        return struct, opts

    LOG.info("Extracting FastAPI component information for context enrichment...")

    # Get template content
    template_content = MAIN_PY_TEMPLATE

    # Extract component information
    fastapi_components = extract_fastapi_components(template_content, opts)

    # Store in opts for core extension to use
    if not hasattr(opts, "component_info") or getattr(opts, "component_info", None) is None:
        setattr(opts, "component_info", {})

    # Add FastAPI components to component_info
    # Ensure component_info is a dict before trying to set a key
    if isinstance(getattr(opts, "component_info", None), dict):
        getattr(opts, "component_info")["fastapi"] = fastapi_components
    else:
        # This case should ideally not happen if the above setattr worked
        # or if component_info was already a dict.
        # For safety, re-initialize if it's not a dict.
        setattr(opts, "component_info", {"fastapi": fastapi_components})

    LOG.info(
        f"Added FastAPI component information: {len(fastapi_components['api_info']['endpoints'])} endpoints"
    )

    return struct, opts


def fastapi_generate_api_structure(
    struct: Structure, opts: ScaffoldOpts
) -> ActionParams:
    """
    Action to generate the FastAPI app structure.
    This function will be called via PyScaffold's action system.
    """
    # Get the Pydantic model from opts
    if isinstance(opts, dict):
        khora_config = opts.get("khora_parsed_config")
        project_path_from_opts = opts.get("project_path")
    else:
        khora_config = getattr(opts, "khora_parsed_config", None)
        project_path_from_opts = getattr(opts, "project_path", None)


    if not khora_config:
        LOG.warning("Khora manifest config (khora_parsed_config) not found in opts. Skipping FastAPI scaffolding.")
        return struct, opts

    # Check if the FastAPI feature is enabled
    if not getattr(khora_config.features, "fastapi", False):
        LOG.info(
            "FastAPI feature not enabled in [tool.khora.features]. Skipping scaffolding."
        )
        return struct, opts

    # Get API directory from paths
    api_dir_name = getattr(khora_config.paths, "api_dir", DEFAULT_API_DIR)
    
    # Ensure project_path_from_opts is a Path object before using it
    if not isinstance(project_path_from_opts, Path):
        if isinstance(project_path_from_opts, str):
            project_path_from_opts = Path(project_path_from_opts)
        else:
            LOG.error(f"FastAPI extension: project_path in opts is not a Path or string ({type(project_path_from_opts)}). Cannot determine API directory.")
            return struct, opts # Cannot proceed

    api_dir = project_path_from_opts / api_dir_name

    LOG.info(f"Generating FastAPI structure in {api_dir}...")

    # Define the files to be created
    files: Structure = {
        str(api_dir / "main.py"): (
            MAIN_PY_TEMPLATE,
            no_overwrite(),
        ),
        str(api_dir / "requirements.txt"): (
            REQUIREMENTS_TXT_TEMPLATE,
            no_overwrite(),
        ),
        str(api_dir / "Dockerfile"): (
            DOCKERFILE_TEMPLATE,  # Jinja2 template
            no_overwrite(),
        ),
    }

    # PyScaffold automatically creates parent directories when merging structures,
    # so we don't need to manually create them

    # Merge with existing structure
    struct = {**struct, **files}

    # --- Port Conflict Resolution ---
    DEFAULT_FASTAPI_PORT = 8000
    selected_port = DEFAULT_FASTAPI_PORT
    
    used_ports = set()
    if hasattr(khora_config, "plugins_config") and khora_config.plugins_config:
        # Example: Check a hypothetical docker extension's service configurations
        # This assumes a structure like: khora_config.plugins_config.docker.services = [{"name": "s1", "port": 8000}, ...]
        # This part is speculative and depends on how other extensions expose port info.
        docker_plugin_config = getattr(khora_config.plugins_config, "docker", None)
        if docker_plugin_config and hasattr(docker_plugin_config, "services") and isinstance(docker_plugin_config.services, list):
            for service_conf in docker_plugin_config.services:
                if isinstance(service_conf, dict) and "port" in service_conf and isinstance(service_conf["port"], int):
                    used_ports.add(service_conf["port"])
                # If Pydantic models are used for service_conf:
                elif hasattr(service_conf, "port") and isinstance(service_conf.port, int):
                     used_ports.add(service_conf.port)

    initial_port_check = selected_port
    while selected_port in used_ports:
        LOG.debug(f"Port {selected_port} is already in use by another configured service. Trying next port.")
        selected_port += 1
        if selected_port > initial_port_check + 100: # Avoid infinite loop
            LOG.warning(f"Could not find an available port after 100 attempts from base {initial_port_check}. Using {selected_port} with potential conflict.")
            break
            
    if selected_port != DEFAULT_FASTAPI_PORT:
        LOG.info(
            f"FastAPI default port {DEFAULT_FASTAPI_PORT} conflicts with other services. "
            f"Adjusted FastAPI service port to {selected_port}."
        )
    
    opts["fastapi_port"] = selected_port
    # --- End Port Conflict Resolution ---

    # Add other variables for Jinja2 template rendering
    docker_config = getattr(getattr(khora_config, "plugins_config", {}), "docker", {})
    
    if isinstance(opts, dict):
        opts["fastapi_port"] = selected_port
        opts["docker_api_service_name"] = getattr(docker_config, "api_service_name", "api")
        opts["api_dir_name"] = api_dir_name
    else:
        setattr(opts, "fastapi_port", selected_port)
        setattr(opts, "docker_api_service_name", getattr(docker_config, "api_service_name", "api"))
        setattr(opts, "api_dir_name", api_dir_name)

    return struct, opts


class FastApiScaffoldExtension(Extension):
    """Generates a basic FastAPI application structure."""

    name = "fastapi_scaffold"  # Name used to activate the extension

    def augment_cli(self, parser: argparse.ArgumentParser):
        """Add a CLI option for this extension"""
        parser.add_argument(
            self.flag,  # self.flag is derived from self.name
            dest=self.name,
            action="store_true",
            default=False,
            help="Activate FastAPI scaffolding for the project",
        )
        return self

    def activate(self, actions: List[Action]) -> List[Action]:
        """
        Activate extension. See :obj:`pyscaffold.extensions.Extension.activate`.
        """
        # Ensure self.opts exists before trying to access attributes
        if not hasattr(self, 'opts') or self.opts is None:
            LOG.error(f"FastApiScaffoldExtension: self.opts not set when activate() called. Skipping activation.")
            return actions

        # Check if the extension was activated via CLI flag or programmatically
        if not getattr(self.opts, self.name, False): # Use getattr for Namespace
            LOG.info(f"FastApiScaffoldExtension not activating because '{self.name}' is not True in self.opts.")
            return actions
        
        LOG.info("Activating Khora FastAPI Scaffold Extension...")

        # Register our action to generate the FastAPI structure
        actions = self.register(
            actions,
            fastapi_generate_api_structure,
            after="define_structure",
        )

        # Register the action to contribute component information to context.yaml
        # This should run before the core extension's context generation
        actions = self.register(
            actions,
            fastapi_context_contribution,
            before="_generate_khora_context_yaml",
        )

        LOG.info("FastAPI Scaffold Extension activated with context enrichment.")
        return actions

    # We might need a `requires` method if we depend on another extension
    # to parse the khora manifest first.
    # def requires(self) -> List[str]:
    #     return ["khora_core"] # Example if core extension handles manifest parsing

```

## khora-kernel/src/khora_kernel/extensions/precommit/extension.py  
`9038 bytes`  ·  `4d1bfd4`  
```python
"""
Pre-commit extension for Khora Kernel.
"""

import argparse
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Any

from pyscaffold.actions import Action, ActionParams, ScaffoldOpts, Structure
from pyscaffold.extensions import Extension
from pyscaffold.operations import no_overwrite

logger = logging.getLogger(__name__)


class PrecommitExtension(Extension):
    """
    PyScaffold extension to generate pre-commit configuration.
    This includes standard Python linting hooks and custom Khora hooks.
    """

    name = "khora_precommit"  # This will be --khora-precommit in the CLI

    def augment_cli(self, parser: argparse.ArgumentParser):
        """Add a CLI option for this extension."""
        parser.add_argument(
            self.flag,
            dest=self.name,
            action="store_true",
            default=False,
            help="Add pre-commit configuration to the project",
        )
        return self

    def activate(self, actions: List[Action]) -> List[Action]:
        """Activate extension rules."""
        # Ensure self.opts exists before trying to access attributes
        if not hasattr(self, 'opts') or self.opts is None:
            logger.error(f"PrecommitExtension: self.opts not set when activate() called. Skipping activation.")
            return actions

        if not getattr(self.opts, self.name, False): # Use getattr for Namespace
            logger.info(f"PrecommitExtension not activating because '{self.name}' is not True in self.opts.")
            return actions

        logger.info("Activating Khora Pre-commit Extension...")

        # Register action to generate pre-commit config
        actions = self.register(actions, add_precommit_config, after="define_structure")

        return actions


def add_precommit_config(struct: Structure, opts: ScaffoldOpts) -> ActionParams:
    """
    Add pre-commit configuration to the project structure.

    Args:
        struct: Project representation as (possibly) nested dict.
        opts: Given options.

    Returns:
        Updated project structure and options.
    """
    # Get the Pydantic model from opts, which CoreExtension stores as 'khora_parsed_config'
    # opts can be a Namespace or a dict.
    if isinstance(opts, dict):
        khora_config = opts.get("khora_parsed_config")
    else:
        khora_config = getattr(opts, "khora_parsed_config", None)

    if not khora_config:
        logger.warning(
            "Khora manifest config (khora_parsed_config) not found in opts. Attempting to load directly."
        )
        try:
            from ..core.manifest import KhoraManifestConfig
            project_path_val = getattr(opts, "project_path", Path(".")) if not isinstance(opts, dict) else opts.get("project_path", Path("."))
            if isinstance(project_path_val, str): project_path_val = Path(project_path_val)

            active_env_val = getattr(opts, "khora_env", None) if not isinstance(opts, dict) else opts.get("khora_env")
            
            khora_config = KhoraManifestConfig.from_project_toml_with_env(project_path_val, env=active_env_val)
            
            # Store it back to opts
            if isinstance(opts, dict):
                opts["khora_parsed_config"] = khora_config
            else:
                setattr(opts, "khora_parsed_config", khora_config)
            logger.info("Successfully loaded and stored khora_parsed_config in fallback.")
        except Exception as e:
            logger.error(f"Fallback: Failed to load Khora manifest config directly: {e}. Skipping pre-commit config.")
            return struct, opts

    # Check if the pre-commit feature is enabled
    if not getattr(khora_config.features, "precommit", False):
        logger.info(
            "Khora Pre-commit feature not enabled. Skipping pre-commit config generation."
        )
        return struct, opts

    # Check if security gates are enabled
    security_gates_enabled = getattr(khora_config.features, "security_gates", False)
    logger.info(f"Security gates enabled: {security_gates_enabled}")

    # Check if knowledge graph is enabled
    kg_enabled = getattr(khora_config.features, "kg", False)
    logger.info(f"KG enabled: {kg_enabled}")

    # Start with standard Python hooks
    precommit_config = {
        "repos": [
            {
                "repo": "https://github.com/astral-sh/ruff-pre-commit",
                "rev": "v0.1.5",
                "hooks": [{"id": "ruff", "args": ["--fix"]}, {"id": "ruff-format"}],
            },
            {
                "repo": "https://github.com/pre-commit/pre-commit-hooks",
                "rev": "v4.4.0",
                "hooks": [
                    {"id": "trailing-whitespace"},
                    {"id": "end-of-file-fixer"},
                    {"id": "check-yaml"},
                    {"id": "debug-statements"},
                    {"id": "check-toml"},
                ],
            },
        ]
    }

    # Add security hooks if enabled
    if security_gates_enabled:
        precommit_config["repos"].append(
            {
                "repo": "https://github.com/PyCQA/bandit",
                "rev": "1.7.5",
                "hooks": [
                    {"id": "bandit", "args": ["-x", "./tests", "-c", "pyproject.toml"]}
                ],
            }
        )

        precommit_config["repos"].append(
            {
                "repo": "https://github.com/trufflesecurity/trufflehog",
                "rev": "v3.63.0",
                "hooks": [
                    {
                        "id": "trufflehog",
                        "name": "TruffleHog OSS",
                        "entry": "trufflehog filesystem --no-verification .",
                        "language": "system",
                        "pass_filenames": False,
                    }
                ],
            }
        )

    # Add knowledge graph hook if enabled
    if kg_enabled:
        project_name = getattr(opts, "project_name", "khora_project") # Use getattr for Namespace

        precommit_config["repos"].append(
            {
                "repo": "local",
                "hooks": [
                    {
                        "id": "khora-knowledge-graph",
                        "name": "Khora Knowledge Graph Extractor",
                        "entry": "python -m khora_kernel.extensions.kg.kg_precommit",
                        "language": "python",
                        "files": r"\.md$",
                        "pass_filenames": True,
                    }
                ],
            }
        )

    # Add gRPC sync-stubs hook if gRPC feature is enabled
    # Assume khora_config.features.grpc indicates gRPC usage.
    # Paths for proto_dir and stubs_out_dir could also come from khora_config.paths
    # For MVP, let's use conventional defaults if not specified.
    grpc_enabled = getattr(khora_config.features, "grpc", False)
    if grpc_enabled:
        logger.info("gRPC feature enabled. Adding khora sync-stubs pre-commit hook.")
        # Determine proto_dir and stubs_out_dir
        # These could be configurable via khora_config.paths or a specific grpc config section
        # Using defaults for now as an example.
        proto_dir_path = getattr(khora_config.paths, "proto_dir", "protos")
        stubs_out_dir_path = getattr(khora_config.paths, "stubs_out_dir", "src/grpc_stubs") # Example path

        precommit_config["repos"].append(
            {
                "repo": "local",
                "hooks": [
                    {
                        "id": "khora-sync-grpc-stubs",
                        "name": "Khora Sync gRPC Stubs",
                        "entry": f"khora sync-stubs --proto-dir {proto_dir_path} --stubs-out-dir {stubs_out_dir_path}",
                        "language": "system", # Assumes 'khora' is in PATH
                        "types": ["protobuf"], # This type might work for .proto files
                        "files": r"\.proto$", # Regex to match .proto files
                        "pass_filenames": False, # Command doesn't need filenames passed
                        # "stages": ["commit"], # Default, but can be explicit
                    }
                ],
            }
        )


    # Convert to YAML
    try:
        precommit_yaml = yaml.dump(precommit_config, sort_keys=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to serialize pre-commit config to YAML: {e}")
        precommit_yaml = (
            f"# Error generating pre-commit config: {e}\n"
            f"# Raw data: {precommit_config}"
        )

    # Add .pre-commit-config.yaml to the root of the project
    struct[".pre-commit-config.yaml"] = (precommit_yaml, no_overwrite())

    # For testing - also add a directly overwritable version
    struct[".pre-commit-config-direct.yaml"] = (precommit_yaml, lambda *_: None)

    logger.info(
        "Generated .pre-commit-config.yaml with standard hooks and custom Khora hooks."
    )

    return struct, opts

```

## khora-kernel/tests/e2e/conftest.py  
`19327 bytes`  ·  `73e06d5`  
```python
import pytest
import pathlib
import tomlkit
import yaml
import json
import jsonschema # For context.yaml schema validation
import shutil # For copying files
from click.testing import CliRunner

# E2E Test Fixtures for Khora Kernel

@pytest.fixture
def isolated_e2e_project(tmp_path_factory):
    """
    Creates an isolated temporary directory for an E2E test project.
    """
    project_dir = tmp_path_factory.mktemp("e2e_project_")
    return project_dir

@pytest.fixture
def khora_cli_runner() -> CliRunner:
    """
    Provides a Click CliRunner instance for invoking Khora CLI commands.
    """
    return CliRunner()

# Manifest Fixtures (Python Dictionaries for [tool.khora] section)

@pytest.fixture
def minimal_khora_manifest_config() -> dict:
    return {
        "project_name": "MyMinimalApp",
        "python_version": "3.12"
    }

@pytest.fixture
def fastapi_docker_khora_manifest_config() -> dict:
    return {
        "project_name": "MyWebApp",
        "python_version": "3.12",
        "project_description": "A cool web application.",
        "features": {
            "fastapi": True,
            "docker": True,
            "ci_github_actions": True,
            "documentation": True
        },
        "paths": {"api_dir": "service_api", "docs_dir": "documentation_files"},
        "ports": {"http": 8080},
        "plugins_config": {
            "docs": {"docs_type": "mkdocs"}
        }
    }

@pytest.fixture
def env_layering_khora_manifest_config() -> dict:
    return {
        "project_name": "LayeredApp",
        "python_version": "3.12",
        "features": {"fastapi": True, "docker": False, "kg": False}, # Explicitly set kg to false for base
        "paths": {"api_dir": "api_base"},
        "ports": {"http": 8000},
        "env": {
            "dev": {
                "project_description": "Dev environment for LayeredApp",
                "features": {"docker": True, "kg": True}, # Docker true and kg true in dev
                "paths": {"api_dir": "api_dev_specific"},
                "ports": {"http": 9001}
            },
            "prod": {
                "project_description": "Prod environment for LayeredApp",
                "ports": {"http": 9002}
                # Prod uses base features (docker=false, kg=false) and base paths (api_base)
            }
        }
    }

@pytest.fixture
def template_customization_khora_manifest_config() -> dict:
    return {
        "project_name": "CustomTemplateApp",
        "python_version": "3.12",
        "features": {"fastapi": True},
        "paths": {"api_dir": "app_api"},
        "templates": {
            "fastapi_scaffold.main_py": "custom_templates/my_fastapi_main.py.template"
        }
    }

@pytest.fixture
def custom_main_py_template_content() -> str:
    return """# This is a custom main.py for {{ project_name }}
from fastapi import FastAPI
app = FastAPI(title="{{ project_name }} - Custom Edition")
@app.get("/custom_hello")
async def custom_hello():
    return {"message": "Hello from custom template!"}
"""

# Helper Functions

def create_manifest_in_project(project_dir: pathlib.Path, khora_tool_config: dict, project_section_name: str = None):
    """
    Creates a pyproject.toml file in project_dir with [project] and [tool.khora] sections.
    """
    if project_section_name is None:
        project_section_name = project_dir.name

    pyproject_data = {
        "project": {
            "name": project_section_name,
            "version": "0.1.0",
            "description": khora_tool_config.get("project_description", f"Test project for {project_section_name}")
        },
        "tool": {
            "khora": khora_tool_config
        }
    }
    pyproject_file_path = project_dir / "pyproject.toml"
    pyproject_file_path.write_text(tomlkit.dumps(pyproject_data))
    return pyproject_file_path

# Determine Khora Kernel project root once (e.g., based on conftest.py location)
# This assumes conftest.py is in khora-kernel/tests/e2e/ and schema is at khora-kernel/src/khora_kernel/...
KHORA_KERNEL_ROOT = pathlib.Path(__file__).parent.parent.parent
CONTEXT_SCHEMA_PATH = KHORA_KERNEL_ROOT / "src/khora_kernel/extensions/core/context_schema.json"

def validate_context_yaml_schema(context_yaml_path: pathlib.Path) -> dict:
    """
    Validates the given context.yaml file against the Khora Kernel's core context_schema.json.
    Returns the parsed context_data if valid.
    """
    assert context_yaml_path.exists(), f"context.yaml not found at {context_yaml_path}"
    assert CONTEXT_SCHEMA_PATH.exists(), f"Context schema not found at {CONTEXT_SCHEMA_PATH}"

    with open(context_yaml_path, 'r') as f_ctx, open(CONTEXT_SCHEMA_PATH, 'r') as f_sch:
        context_data = yaml.safe_load(f_ctx)
        schema_data = json.load(f_sch) # Schema is JSON

        jsonschema.validate(instance=context_data, schema=schema_data)
    return context_data

# Fixtures for scaffolded projects to be used by utility tests

@pytest.fixture(scope="function") # Use function scope to ensure a fresh project for each test
def scaffolded_minimal_project(tmp_path: pathlib.Path, khora_cli_runner: CliRunner, minimal_khora_manifest_config: dict) -> pathlib.Path:
    """
    Creates a minimal project using `khora create .` and returns its path.
    """
    actual_project_name = minimal_khora_manifest_config['project_name']
    # This is the directory where the final, usable scaffolded project will reside.
    project_dir_for_fixture_output = tmp_path / actual_project_name
    project_dir_for_fixture_output.mkdir(parents=True, exist_ok=True)

    # Use isolated_filesystem without temp_dir to get a pristine temporary CWD
    with khora_cli_runner.isolated_filesystem() as isolated_dir_str:
        isolated_path = pathlib.Path(isolated_dir_str) # This is the pristine CWD

        # Create pyproject.toml in this pristine CWD (isolated_path)
        # The [project].name in this pyproject.toml must be actual_project_name.
        create_manifest_in_project(isolated_path, minimal_khora_manifest_config, project_section_name=actual_project_name)
        assert (isolated_path / "pyproject.toml").exists(), \
            f"pyproject.toml not created in isolated_path for {actual_project_name}"
        
        from khora_kernel.cli.commands import main_cli # Local import
        # `khora create .` will run in isolated_path.
        # Khora's `create` command logic for `.` should find pyproject.toml in CWD (isolated_path)
        # and use its `[project].name` (actual_project_name) for PyScaffold's `name` opt.
        # PyScaffold will then scaffold in-place within isolated_path because CWD's name
        # (a random temp name) won't match actual_project_name, so it creates a subdir actual_project_name.
        # This is not what we want for `khora create .`.
        # The `khora create .` command itself needs to handle this.
        # For the fixture, the goal is to have the *output* of `khora create .`
        # (which should be a directory named actual_project_name) copied to project_dir_for_fixture_output.

        # Let's assume `khora create .` correctly scaffolds into a directory named `actual_project_name`
        # *inside* `isolated_path` if `isolated_path` itself is not already named `actual_project_name`.
        # Or, if `isolated_path` *is* named `actual_project_name` (which we can't easily do with default isolated_filesystem),
        # it scaffolds directly into `isolated_path`.

        # The current `khora create .` logic:
        # If project_name is ".", final_project_path = CWD.
        # It then reads pyproject.toml from CWD.
        # It passes project_path=CWD and name=name_from_toml to PyScaffold.
        # If CWD.name == name_from_toml, PyScaffold scaffolds in place.
        # If CWD.name != name_from_toml, PyScaffold creates subdir name_from_toml.

        # To make it scaffold in place within isolated_path, isolated_path would need to be renamed to actual_project_name.
        # This is complex with isolated_filesystem.

        # Alternative: `khora create actual_project_name` inside `isolated_path`.
        # This would create `isolated_path / actual_project_name`.
        
        # Let's stick to `khora create .` and ensure the CWD for it is correctly prepared.
        # The `temp_dir` approach for isolated_filesystem was the right idea, but `khora create .`
        # seems to make its own subdir.

        # Reverting to the strategy of creating a correctly named temp_scaffold_dir
        # and using that as temp_dir for isolated_filesystem.
        # This was the state before the last `pytest` run that still failed for `create` tests.
        # The issue might be subtle.

        # Let's simplify: the fixture should run `khora create actual_project_name`
        # inside a generic temp dir, then return the path to `actual_project_name`.
        
        generic_temp_dir_for_creation = tmp_path / f"creation_space_for_{actual_project_name}"
        generic_temp_dir_for_creation.mkdir(exist_ok=True)

        # We need to provide the manifest to `khora create actual_project_name`.
        # `khora create <name>` does not automatically look for pyproject.toml in CWD to get config.
        # It expects to create a new project.
        # The `CoreExtension` will load the manifest from the target project path *after* PyScaffold
        # creates the basic structure if a pyproject.toml with [tool.khora] is placed there by PyScaffold.
        # This is tricky.

        # The most robust way for fixtures:
        # 1. Create a pristine isolated_path.
        # 2. Inside isolated_path, create the pyproject.toml with the desired config.
        # 3. Run `khora create .` (which operates in isolated_path).
        #    This should correctly scaffold *within* isolated_path because PyScaffold's `name`
        #    will be derived from the pyproject.toml, and `project_path` will be isolated_path.
        #    If isolated_path.name != project_name_from_toml, PyScaffold creates a subdir.
        #    This is the problem. PyScaffold needs project_path.name == name.
        
        # The fix is to ensure the directory `khora create .` runs in, IS named `actual_project_name`.
        # So, the `temp_dir` for `isolated_filesystem` must be `tmp_path / actual_project_name`.
        # And the `pyproject.toml` must be placed inside it.

        # This is what was in `conftest.py` that led to the `create` tests failing with
        # "pyproject.toml not found" because `khora create .` made an inner temp dir.

        # Let's re-read `khora create .` logic carefully.
        # If `project_name == "."`: `final_project_path = Path.cwd()`.
        # `actual_project_name_for_pyscaffold` is read from `final_project_path / "pyproject.toml"`.
        # `pyscaffold_kwargs` gets `project_path: final_project_path`, `name: actual_project_name_for_pyscaffold`.
        # If `final_project_path.name == actual_project_name_for_pyscaffold`, PyScaffold works in-place.
        # This is the condition we need.

        # So, for the fixture:
        # 1. `fixture_context_dir = tmp_path / actual_project_name`
        # 2. `fixture_context_dir.mkdir()`
        # 3. `create_manifest_in_project(fixture_context_dir, config, project_section_name=actual_project_name)`
        # 4. `with runner.isolated_filesystem(temp_dir=fixture_context_dir): invoke create .`
        # 5. The result is already in `fixture_context_dir`. Return `fixture_context_dir`.
        # This is what was just tried for `test_e2e_journey1_create.py` and failed.

        # The debug output for `test_e2e_journey1_create` showed:
        # CWD for invoke was: /.../MyMinimalApp
        # Contents: pyproject.toml, tmpXXXXX
        # Result output: Creating Khora project in current directory: /.../MyMinimalApp/tmpXXXXX
        # Error: pyproject.toml not found... (presumably looking in /.../MyMinimalApp/tmpXXXXX)

        # This means `khora create .` itself, when its CWD is `MyMinimalApp` (containing `pyproject.toml` with name `MyMinimalApp`),
        # is *still* delegating to PyScaffold in a way that PyScaffold creates a nested temp dir.
        # This points to an issue in how `khora create .` calls `pyscaffold.api.create_project`.
        # Specifically, `pyscaffold_kwargs["project_path"]` is `final_project_path` (e.g. `MyMinimalApp`)
        # and `pyscaffold_kwargs["name"]` is also `MyMinimalApp`.
        # PyScaffold with `force=True` should overwrite/use this directory. Why does it make a temp sub-folder?

        # Is it possible `pyscaffold.api.create_project` with `force=True` behaves differently if the target dir is not empty?
        # (it contains pyproject.toml).
        # The `CoreExtension` is also in play.

        # Let's try the original guide's fixture logic:
        # - `project_dir = tmp_path / "scaffolded_minimal"` (a generic name for the fixture's output dir)
        # - `with khora_cli_runner.isolated_filesystem() as isolated_dir_str:` (pristine temp)
        #   - `isolated_path = Path(isolated_dir_str)`
        #   - `create_manifest_in_project(isolated_path, config, project_section_name=actual_project_name)`
        #   - `invoke main_cli, ['create', '.']` (runs in `isolated_path`)
        #     This will create `isolated_path / actual_project_name` if PyScaffold works as expected.
        #   - `shutil.copytree(isolated_path / actual_project_name, project_dir, dirs_exist_ok=True)`
        # This seems more robust if `khora create .` inside `isolated_path` (random name) correctly creates
        # a subdirectory named `actual_project_name`.

        project_dir_for_output = tmp_path / f"scaffolded_{actual_project_name}" # e.g. scaffolded_MyMinimalApp
        project_dir_for_output.mkdir(parents=True, exist_ok=True)

        with khora_cli_runner.isolated_filesystem() as isolated_dir_str: # Pristine temp dir
            isolated_path = pathlib.Path(isolated_dir_str)
            
            # Create the initial pyproject.toml inside the pristine isolated_path
            # The [project].name here is crucial for PyScaffold's behavior.
            create_manifest_in_project(isolated_path, minimal_khora_manifest_config, project_section_name=actual_project_name)
            
            from khora_kernel.cli.commands import main_cli
            # `khora create .` runs in isolated_path.
            # It reads pyproject.toml from isolated_path. Gets `name = actual_project_name`.
            # It calls PyScaffold with `project_path=isolated_path`, `name=actual_project_name`.
            # Since isolated_path.name (random) != actual_project_name, PyScaffold will create
            # a subdirectory `isolated_path / actual_project_name`.
            result = khora_cli_runner.invoke(main_cli, ['create', '.'], catch_exceptions=False)
            
            if result.exit_code != 0:
                # Print debug info if khora create fails
                print(f"DEBUG (fixture: scaffolded_minimal_project): khora create . failed in {isolated_path}")
                print(f"DEBUG (fixture: scaffolded_minimal_project): Contents of {isolated_path}:")
                for item in isolated_path.rglob('*'): print(f"  - {item.relative_to(isolated_path)}")
                print(f"DEBUG (fixture: scaffolded_minimal_project): Result output: {result.output}")

            assert result.exit_code == 0, f"khora create failed in fixture's isolated env for {actual_project_name}: {result.output}"
            
            # When `khora create .` is run in isolated_path (which contains pyproject.toml with [project].name = actual_project_name),
            # and force=True, PyScaffold scaffolds directly into isolated_path.
            source_scaffold_path = isolated_path
            
            assert source_scaffold_path.is_dir(), \
                f"Expected scaffolded project directly in {source_scaffold_path}, but it's not a directory."
            assert (source_scaffold_path / "pyproject.toml").exists(), \
                f"pyproject.toml missing in scaffolded source {source_scaffold_path}"
            assert (source_scaffold_path / ".khora" / "context.yaml").exists(), \
                f"context.yaml missing in scaffolded source {source_scaffold_path}"

            # Copy from isolated_path (which is the fully scaffolded project root) to the fixture's output directory
            if project_dir_for_output.exists():
                shutil.rmtree(project_dir_for_output) # Clean target
            shutil.copytree(source_scaffold_path, project_dir_for_output, dirs_exist_ok=False) # Ensure fresh copy
                    
        return project_dir_for_output

@pytest.fixture(scope="function")
def scaffolded_fastapi_docker_project(tmp_path: pathlib.Path, khora_cli_runner: CliRunner, fastapi_docker_khora_manifest_config: dict) -> pathlib.Path:
    """
    Creates a FastAPI+Docker project using `khora create .` and returns its path.
    """
    actual_project_name = fastapi_docker_khora_manifest_config['project_name']
    project_dir_for_output = tmp_path / f"scaffolded_{actual_project_name}"
    project_dir_for_output.mkdir(parents=True, exist_ok=True)

    with khora_cli_runner.isolated_filesystem() as isolated_dir_str: # Pristine temp dir
        isolated_path = pathlib.Path(isolated_dir_str)
        
        create_manifest_in_project(isolated_path, fastapi_docker_khora_manifest_config, project_section_name=actual_project_name)
        
        from khora_kernel.cli.commands import main_cli
        result = khora_cli_runner.invoke(main_cli, ['create', '.'], catch_exceptions=False)

        if result.exit_code != 0:
            print(f"DEBUG (fixture: scaffolded_fastapi_docker_project): khora create . failed in {isolated_path}")
            print(f"DEBUG (fixture: scaffolded_fastapi_docker_project): Contents of {isolated_path}:")
            for item in isolated_path.rglob('*'): print(f"  - {item.relative_to(isolated_path)}")
            print(f"DEBUG (fixture: scaffolded_fastapi_docker_project): Result output: {result.output}")

        assert result.exit_code == 0, f"khora create failed in fixture's isolated env for {actual_project_name}: {result.output}"
        
        # When `khora create .` is run in isolated_path (which contains pyproject.toml with [project].name = actual_project_name),
        # and force=True, PyScaffold scaffolds directly into isolated_path.
        source_scaffold_path = isolated_path
        
        assert source_scaffold_path.is_dir(), \
            f"Expected scaffolded project directly in {source_scaffold_path}, but it's not a directory."
        assert (source_scaffold_path / "pyproject.toml").exists(), \
            f"pyproject.toml missing in scaffolded source {source_scaffold_path}"
        assert (source_scaffold_path / "docker-compose.yml").exists(), \
            f"docker-compose.yml missing in scaffolded source {source_scaffold_path}" # This will be specific to this fixture
        assert (source_scaffold_path / ".khora" / "context.yaml").exists(), \
            f"context.yaml missing in scaffolded source {source_scaffold_path}"

        if project_dir_for_output.exists():
            shutil.rmtree(project_dir_for_output)
        shutil.copytree(source_scaffold_path, project_dir_for_output, dirs_exist_ok=False)
                
    return project_dir_for_output

```

## khora-kernel/tests/e2e/test_e2e_journey1_create.py  
`16595 bytes`  ·  `111ad01`  
```python
import pytest
import pathlib
import tomlkit
import yaml
import json
import jsonschema
import shutil # For copying files
from click.testing import CliRunner

from khora_kernel.cli.commands import main_cli

from .conftest import (
    khora_cli_runner,
    create_manifest_in_project,
    validate_context_yaml_schema,
    minimal_khora_manifest_config,
    fastapi_docker_khora_manifest_config,
    env_layering_khora_manifest_config,
    template_customization_khora_manifest_config,
    custom_main_py_template_content
)

# Helper functions for assertions
def _assert_common_project_files(project_dir: pathlib.Path, project_name_in_src: str):
    assert (project_dir / ".gitignore").exists(), ".gitignore not found"
    assert (project_dir / "README.rst").exists(), "README.rst not found" # Changed from .md to .rst
    assert (project_dir / "pyproject.toml").exists(), "pyproject.toml not found"
    assert (project_dir / "src").is_dir(), "src directory not found"
    assert (project_dir / "src" / project_name_in_src).is_dir(), f"src/{project_name_in_src} directory not found"
    assert (project_dir / "src" / project_name_in_src / "__init__.py").exists(), f"src/{project_name_in_src}/__init__.py not found"
    assert (project_dir / "tests").is_dir(), "tests directory not found"
    assert (project_dir / ".khora").is_dir(), ".khora directory not found"
    assert (project_dir / ".khora" / "context.yaml").exists(), ".khora/context.yaml not found"

def _assert_context_yaml_basics(context_data: dict, expected_project_name: str, expected_python_version: str, expected_env: str = None):
    assert context_data['project']['name'] == expected_project_name, "Context: project.name mismatch"
    assert context_data['project']['python_version'] == expected_python_version, "Context: project.python_version mismatch"
    if expected_env:
        assert context_data['active_environment'] == expected_env, "Context: active_environment mismatch"
    else:
        assert context_data.get('active_environment') is None, "Context: active_environment should be None"

# Scenario-specific assertion functions
def check_minimal_scenario_assertions(project_dir: pathlib.Path, manifest_dict: dict, khora_env_override: str):
    project_name_in_src = manifest_dict['project_name'].lower().replace('-', '_').replace(' ', '_')
    _assert_common_project_files(project_dir, project_name_in_src)
    
    readme_content = (project_dir / "README.rst").read_text() # Changed from .md to .rst
    assert manifest_dict['project_name'] in readme_content, "Project name not in README.rst"

    # Assuming precommit is a default feature, check for its config file
    assert (project_dir / ".pre-commit-config.yaml").exists(), ".pre-commit-config.yaml not found (assuming default feature)"

    context_data = validate_context_yaml_schema(project_dir / ".khora" / "context.yaml")
    _assert_context_yaml_basics(context_data, manifest_dict['project_name'], manifest_dict['python_version'])

    assert context_data['features'].get('fastapi', False) is False, "Context: FastAPI feature should be False"
    assert context_data['features'].get('docker', False) is False, "Context: Docker feature should be False"
    assert context_data['features'].get('precommit', False) is True, "Context: Precommit feature should be True (default)"


def check_fastapi_docker_scenario_assertions(project_dir: pathlib.Path, manifest_dict: dict, khora_env_override: str):
    project_name_in_src = manifest_dict['project_name'].lower().replace('-', '_').replace(' ', '_')
    _assert_common_project_files(project_dir, project_name_in_src)

    api_dir = project_dir / manifest_dict['paths']['api_dir']
    docs_dir = project_dir / manifest_dict['paths']['docs_dir']

    assert api_dir.is_dir(), f"{api_dir} not found"
    assert (api_dir / "main.py").exists(), f"{api_dir}/main.py not found"
    assert (api_dir / "Dockerfile").exists(), f"{api_dir}/Dockerfile not found"
    assert (project_dir / "docker-compose.yml").exists(), "docker-compose.yml not found"
    assert (project_dir / ".github" / "workflows" / "ci.yml").exists(), ".github/workflows/ci.yml not found"

    assert docs_dir.is_dir(), f"{docs_dir} not found"
    assert (docs_dir / "mkdocs.yml").exists(), f"{docs_dir}/mkdocs.yml not found" # Based on plugins_config

    readme_content = (project_dir / "README.rst").read_text() # Changed from .md to .rst
    assert manifest_dict['project_name'] in readme_content, "Project name not in README.rst"

    dockerfile_content = (api_dir / "Dockerfile").read_text()
    assert f"FROM python:{manifest_dict['python_version']}" in dockerfile_content, "Python version not in Dockerfile"
    assert "uv pip install" in dockerfile_content, "uv pip install not in Dockerfile"

    docker_compose_content = yaml.safe_load((project_dir / "docker-compose.yml").read_text())
    # Example check, actual service name might vary based on Khora's generation logic
    # This assumes service name is derived from project_name
    expected_image_name_part = project_dir.name.lower()
    assert any(expected_image_name_part in service_def.get('image', '') for service_def in docker_compose_content.get('services', {}).values()), "Expected image name not in docker-compose.yml"


    context_data = validate_context_yaml_schema(project_dir / ".khora" / "context.yaml")
    _assert_context_yaml_basics(context_data, manifest_dict['project_name'], manifest_dict['python_version'])

    assert context_data['features']['fastapi'] is True, "Context: FastAPI feature incorrect"
    assert context_data['features']['docker'] is True, "Context: Docker feature incorrect"
    assert context_data['features']['ci_github_actions'] is True, "Context: CI GitHub Actions feature incorrect"
    assert context_data['project']['paths']['api_dir'] == manifest_dict['paths']['api_dir'], "Context: api_dir path incorrect"
    assert context_data['project']['ports']['http'] == manifest_dict['ports']['http'], "Context: http port incorrect"
    assert 'fastapi' in context_data['components'], "Context: 'fastapi' component missing"


def check_env_layering_dev_scenario_assertions(project_dir: pathlib.Path, manifest_dict: dict, khora_env_override: str):
    project_name_in_src = manifest_dict['project_name'].lower().replace('-', '_').replace(' ', '_')
    _assert_common_project_files(project_dir, project_name_in_src)

    dev_env_config = manifest_dict['env']['dev']

    api_dir = project_dir / dev_env_config['paths']['api_dir']
    assert api_dir.is_dir(), f"Dev specific api_dir {api_dir} not found"
    assert (project_dir / "docker-compose.yml").exists(), "docker-compose.yml should exist for dev env"

    context_data = validate_context_yaml_schema(project_dir / ".khora" / "context.yaml")
    _assert_context_yaml_basics(context_data, manifest_dict['project_name'], manifest_dict['python_version'], expected_env="dev")

    assert context_data['project']['description'] == dev_env_config['project_description'], "Context: Dev description mismatch"
    assert context_data['features']['docker'] is True, "Context: Docker feature should be True for dev"
    assert context_data['features']['kg'] is True, "Context: KG feature should be True for dev" # As per guide example
    assert context_data['project']['paths']['api_dir'] == dev_env_config['paths']['api_dir'], "Context: Dev api_dir mismatch"
    assert context_data['project']['ports']['http'] == dev_env_config['ports']['http'], "Context: Dev http port mismatch"


def check_env_layering_prod_scenario_assertions(project_dir: pathlib.Path, manifest_dict: dict, khora_env_override: str):
    project_name_in_src = manifest_dict['project_name'].lower().replace('-', '_').replace(' ', '_')
    _assert_common_project_files(project_dir, project_name_in_src)

    prod_env_config = manifest_dict['env']['prod']
    base_api_dir = project_dir / manifest_dict['paths']['api_dir'] # Prod uses base api_dir

    assert base_api_dir.is_dir(), f"Base api_dir {base_api_dir} not found for prod"
    assert not (project_dir / "docker-compose.yml").exists(), "docker-compose.yml should NOT exist for prod env (base docker is false)"

    context_data = validate_context_yaml_schema(project_dir / ".khora" / "context.yaml")
    _assert_context_yaml_basics(context_data, manifest_dict['project_name'], manifest_dict['python_version'], expected_env="prod")

    assert context_data['project']['description'] == prod_env_config['project_description'], "Context: Prod description mismatch"
    assert context_data['features']['docker'] is False, "Context: Docker feature should be False for prod"
    assert context_data['features']['kg'] is False, "Context: KG feature should be False for prod (base is false)"
    assert context_data['project']['paths']['api_dir'] == manifest_dict['paths']['api_dir'], "Context: Prod api_dir (base) mismatch"
    assert context_data['project']['ports']['http'] == prod_env_config['ports']['http'], "Context: Prod http port mismatch"


def check_template_customization_scenario_assertions(project_dir: pathlib.Path, manifest_dict: dict, khora_env_override: str):
    project_name_in_src = manifest_dict['project_name'].lower().replace('-', '_').replace(' ', '_')
    _assert_common_project_files(project_dir, project_name_in_src)

    api_dir = project_dir / manifest_dict['paths']['api_dir']
    custom_main_py = api_dir / "main.py"

    assert custom_main_py.exists(), f"{custom_main_py} not found"

    main_py_content = custom_main_py.read_text()
    assert f"# This is a custom main.py for {manifest_dict['project_name']}" in main_py_content, "Custom template header not in main.py"
    assert f"app = FastAPI(title=\"{manifest_dict['project_name']} - Custom Edition\")" in main_py_content, "Custom template title not in main.py"

    context_data = validate_context_yaml_schema(project_dir / ".khora" / "context.yaml")
    _assert_context_yaml_basics(context_data, manifest_dict['project_name'], manifest_dict['python_version'])

    assert context_data['project']['templates']['fastapi_scaffold.main_py'] == manifest_dict['templates']['fastapi_scaffold.main_py'], "Context: Template path mismatch"


@pytest.mark.parametrize(
    "scenario_name, khora_manifest_fixture_name, khora_env_override, checks_function_name",
    [
        ("minimal", "minimal_khora_manifest_config", None, "check_minimal_scenario_assertions"),
        ("fastapi_docker", "fastapi_docker_khora_manifest_config", None, "check_fastapi_docker_scenario_assertions"),
        ("env_layering_dev", "env_layering_khora_manifest_config", "dev", "check_env_layering_dev_scenario_assertions"),
        ("env_layering_prod", "env_layering_khora_manifest_config", "prod", "check_env_layering_prod_scenario_assertions"),
        ("template_customization", "template_customization_khora_manifest_config", None, "check_template_customization_scenario_assertions"),
    ]
)
def test_khora_create_scenarios(
    khora_cli_runner: CliRunner,
    tmp_path: pathlib.Path,
    request, # To get fixtures by name
    scenario_name: str,
    khora_manifest_fixture_name: str,
    khora_env_override: str,
    checks_function_name: str
):
    khora_manifest_dict = request.getfixturevalue(khora_manifest_fixture_name)

    # The actual project name that will be used in pyproject.toml's [project].name
    # This name is also used by PyScaffold to determine the package name.
    actual_project_name_for_toml = khora_manifest_dict['project_name']

    # This is the directory where final assertions will be made.
    # Its name must match the project name for consistency with fixture outputs.
    project_dir_for_assertions = tmp_path / actual_project_name_for_toml
    project_dir_for_assertions.mkdir(parents=True, exist_ok=True)

    cli_args = ['create', '.']
    if khora_env_override:
        cli_args.extend(['--khora-env', khora_env_override])

    # Use isolated_filesystem without temp_dir to get a pristine temporary CWD
    with khora_cli_runner.isolated_filesystem() as isolated_dir_str:
        isolated_path = pathlib.Path(isolated_dir_str)

        # Create pyproject.toml directly in this pristine isolated_path (CWD).
        # The [project].name in this pyproject.toml must match the name of isolated_path
        # for PyScaffold to scaffold in-place. We achieve this by renaming isolated_path.
        # However, Click's isolated_filesystem doesn't allow renaming its managed temp dir easily.
        # Instead, we ensure the [project].name in the pyproject.toml we create *inside* isolated_path
        # is what khora create . expects (which is derived from the directory name if it's a new project,
        # or from an existing pyproject.toml if scaffolding in place).
        # For `khora create .`, it expects to find a pyproject.toml and use its [project].name.
        
        # So, we create a pyproject.toml inside isolated_path with the correct project_name.
        create_manifest_in_project(isolated_path, khora_manifest_dict, project_section_name=actual_project_name_for_toml)
        assert (isolated_path / "pyproject.toml").exists(), \
            f"pyproject.toml not created in isolated_path: {isolated_path}"

        # Handle template customization: files are placed relative to isolated_path.
        if scenario_name == "template_customization":
            template_file_relative_path_str = khora_manifest_dict['templates']['fastapi_scaffold.main_py']
            custom_template_full_path = isolated_path / template_file_relative_path_str
            custom_template_full_path.parent.mkdir(parents=True, exist_ok=True)
            custom_template_full_path.write_text(request.getfixturevalue("custom_main_py_template_content"))
            assert custom_template_full_path.exists(), \
                f"Custom template file not created at {custom_template_full_path}"

        # `khora create .` will run in isolated_path, which now contains the correctly named pyproject.toml.
        result = khora_cli_runner.invoke(main_cli, cli_args, catch_exceptions=False)
        
        # Debug output if create fails
        if result.exit_code != 0:
            print(f"DEBUG: khora create failed for scenario '{scenario_name}' inside isolated_filesystem.")
            print(f"DEBUG: Isolated CWD for invoke was: {isolated_path}")
            print(f"DEBUG: Contents of {isolated_path} (listing up to 5 levels deep):")
            def print_dir_contents(base_path, current_path, level=0, max_level=5):
                if level > max_level: return
                try:
                    for item in current_path.iterdir():
                        print(f"  {'  ' * level}- {item.relative_to(base_path)}")
                        if item.is_dir(): print_dir_contents(base_path, item, level + 1, max_level)
                except Exception as e: print(f"  {'  ' * level}- Error listing {current_path}: {e}")
            print_dir_contents(isolated_path, isolated_path)
            print(f"DEBUG: CLI arguments: {cli_args}")
            print(f"DEBUG: Result output: {result.output}")
            if result.exception:
                import traceback
                print(f"DEBUG: Exception: {result.exception}")
                traceback.print_exception(type(result.exception), result.exception, result.exc_info[2])

        assert result.exit_code == 0, \
            f"khora create failed for scenario '{scenario_name}' in isolated_filesystem: {result.output}\nException: {result.exception}"

        # PyScaffold, when force=True and project_name in pyproject.toml differs from isolated_path.name,
        # scaffolds directly into isolated_path.
        # So, isolated_path itself is the root of the scaffolded project.
        scaffolded_project_root_in_isolated = isolated_path

        assert scaffolded_project_root_in_isolated.is_dir(), \
            f"Scaffolded project root {scaffolded_project_root_in_isolated} (i.e. isolated_path itself) is not a directory. " \
            f"Contents: {[str(p.relative_to(isolated_path)) for p in isolated_path.rglob('*')]}"

        # Copy scaffolded contents from isolated_path to project_dir_for_assertions
        # Ensure project_dir_for_assertions is clean before copying
        if project_dir_for_assertions.exists():
            shutil.rmtree(project_dir_for_assertions)
        shutil.copytree(scaffolded_project_root_in_isolated, project_dir_for_assertions, dirs_exist_ok=False)

    # Assertions are made on project_dir_for_assertions.
    assertion_function_to_call = globals()[checks_function_name] 
    assertion_function_to_call(project_dir_for_assertions, khora_manifest_dict, khora_env_override)

```

## khora-kernel/tests/e2e/test_e2e_journey1_utilities.py  
`10578 bytes`  ·  `d8b9c96`  
```python
import pytest
import pathlib
import json
import tomlkit
import shutil # Added for file copying
from click.testing import CliRunner
from unittest.mock import patch

from khora_kernel.cli.commands import main_cli
# PluginInfo is not explicitly defined, mock will use dicts
from .conftest import (
    khora_cli_runner,
    scaffolded_minimal_project,
    scaffolded_fastapi_docker_project,
    # We might need validate_context_yaml_schema if we inspect context.yaml directly
    # but for CLI utilities, we primarily check their output.
)

def test_utilities_on_minimal_project(
    khora_cli_runner: CliRunner, 
    scaffolded_minimal_project: pathlib.Path
):
    project_fixture_path = scaffolded_minimal_project # Renamed for clarity

    # Test khora validate-manifest
    with khora_cli_runner.isolated_filesystem() as isolated_dir_str:
        isolated_path = pathlib.Path(isolated_dir_str)
        shutil.copy(project_fixture_path / "pyproject.toml", isolated_path / "pyproject.toml")
        # validate-manifest might also need .khora/context.yaml if it performs deep validation
        if (project_fixture_path / ".khora").exists():
             shutil.copytree(project_fixture_path / ".khora", isolated_path / ".khora", dirs_exist_ok=True)

        result_validate = khora_cli_runner.invoke(main_cli, ['validate-manifest', '--json-output'], catch_exceptions=False)
    assert result_validate.exit_code == 0, f"validate-manifest failed: {result_validate.output}"
    try:
        validate_output = json.loads(result_validate.output)
        assert validate_output.get("valid") is True, f"validate-manifest 'valid' field not True. Output: {result_validate.output}"
        assert "manifest" in validate_output, f"validate-manifest missing 'manifest' key. Output: {result_validate.output}"
    except json.JSONDecodeError:
        pytest.fail(f"validate-manifest output is not valid JSON: {result_validate.output}")

    # Test khora health
    with khora_cli_runner.isolated_filesystem() as isolated_dir_str:
        isolated_path = pathlib.Path(isolated_dir_str)
        shutil.copy(project_fixture_path / "pyproject.toml", isolated_path / "pyproject.toml")
        if (project_fixture_path / ".khora").exists():
            shutil.copytree(project_fixture_path / ".khora", isolated_path / ".khora", dirs_exist_ok=True)

        result_health = khora_cli_runner.invoke(main_cli, ['health', '--json-output'], catch_exceptions=False)
    assert result_health.exit_code == 0, f"health failed: {result_health.output}"
    try:
        health_output = json.loads(result_health.output)
        assert health_output["status"] == "success", "health status not success"
        assert health_output["data"]["project_name"] == "MyMinimalApp" # From minimal_khora_manifest_config
        assert health_output["data"]["overall_health"] == "Healthy"
        # Add more specific checks for minimal project health if necessary
    except json.JSONDecodeError:
        pytest.fail(f"health output is not valid JSON: {result_health.output}")

    # Test khora inspect --json-output
    with khora_cli_runner.isolated_filesystem() as isolated_dir_str:
        isolated_path = pathlib.Path(isolated_dir_str)
        shutil.copy(project_fixture_path / "pyproject.toml", isolated_path / "pyproject.toml")
        if (project_fixture_path / ".khora").exists():
            shutil.copytree(project_fixture_path / ".khora", isolated_path / ".khora", dirs_exist_ok=True)

        result_inspect = khora_cli_runner.invoke(main_cli, ['inspect', '--json-output'], catch_exceptions=False)
    assert result_inspect.exit_code == 0, f"inspect failed: {result_inspect.output}"
    try:
        inspect_output = json.loads(result_inspect.output)
        assert inspect_output["status"] == "success", "inspect status not success"
        assert "project_name" in inspect_output["data"]
        assert inspect_output["data"]["project_name"] == "MyMinimalApp"
        assert "khora_version" in inspect_output["data"] # Assuming inspect includes this
        assert "features" in inspect_output["data"]
        assert inspect_output["data"]["features"].get("fastapi") is False # Minimal project
    except json.JSONDecodeError:
        pytest.fail(f"inspect output is not valid JSON: {result_inspect.output}")


def test_health_on_broken_fastapi_project(
    khora_cli_runner: CliRunner, 
    scaffolded_fastapi_docker_project: pathlib.Path
):
    project_fixture_path = scaffolded_fastapi_docker_project # Renamed for clarity
    
    # Path to the original docker-compose.yml in the fixture
    docker_compose_file_original = project_fixture_path / "docker-compose.yml"
    assert docker_compose_file_original.exists(), "Pre-check: docker-compose.yml should exist in fixture"

    with khora_cli_runner.isolated_filesystem() as isolated_dir_str:
        isolated_path = pathlib.Path(isolated_dir_str)
        
        # Copy pyproject.toml and .khora context
        shutil.copy(project_fixture_path / "pyproject.toml", isolated_path / "pyproject.toml")
        if (project_fixture_path / ".khora").exists():
            shutil.copytree(project_fixture_path / ".khora", isolated_path / ".khora", dirs_exist_ok=True)
        
        # DO NOT copy docker-compose.yml to simulate the broken state in the isolated environment
        # The health check should run against the state in isolated_path

        result_health_broken = khora_cli_runner.invoke(main_cli, ['health', '--json-output'], catch_exceptions=False)
    
    # Health command should still exit 0 but report issues in JSON
    assert result_health_broken.exit_code == 0, f"health on broken project failed cli execution: {result_health_broken.output}"
    try:
        health_broken_output = json.loads(result_health_broken.output)
        assert health_broken_output["status"] == "success", "health on broken project status not success (cli should succeed)"
        assert health_broken_output["data"]["overall_health"] == "IssuesFound", "health on broken project should report IssuesFound"
        
        # Check for a specific error message related to the missing docker-compose.yml
        # This depends on the exact error message format from the health command
        found_docker_compose_error = False
        for check in health_broken_output["data"].get("checks", []):
            if "docker-compose.yml" in check.get("message", "") and check.get("status") == "Error":
                found_docker_compose_error = True
                break
        assert found_docker_compose_error, "Specific error for missing docker-compose.yml not found in health output"

    except json.JSONDecodeError:
        pytest.fail(f"health output on broken project is not valid JSON: {result_health_broken.output}")


def test_bump_version_on_scaffolded_project(
    khora_cli_runner: CliRunner,
    scaffolded_minimal_project: pathlib.Path
):
    project_fixture_path = scaffolded_minimal_project # Renamed for clarity
    new_version = "1.2.3"
    changelog_entry_header = f"## [{new_version}]"

    # Prepare an initial CHANGELOG.md in the fixture path if it doesn't exist,
    # so it can be copied to the isolated environment.
    changelog_fixture_file = project_fixture_path / "CHANGELOG.md"
    if not changelog_fixture_file.exists():
        changelog_fixture_file.write_text("# Changelog\n\n## [0.1.0] - Initial release\n")

    with khora_cli_runner.isolated_filesystem() as isolated_dir_str:
        isolated_path = pathlib.Path(isolated_dir_str)

        # Copy necessary files to the isolated environment
        shutil.copy(project_fixture_path / "pyproject.toml", isolated_path / "pyproject.toml")
        shutil.copy(changelog_fixture_file, isolated_path / "CHANGELOG.md")

        result_bump = khora_cli_runner.invoke(
            main_cli,
            ['bump-version', '--new', new_version, '--changelog'],
            catch_exceptions=False # Command runs in isolated_path
        )

        assert result_bump.exit_code == 0, f"bump-version failed: {result_bump.output}"

        # Verify pyproject.toml was updated in the isolated directory
        pyproject_isolated_path = isolated_path / "pyproject.toml"
        assert pyproject_isolated_path.exists()
        pyproject_content_isolated = tomlkit.parse(pyproject_isolated_path.read_text())
        assert pyproject_content_isolated["project"]["version"] == new_version, "Version not updated in isolated pyproject.toml"

        # Verify CHANGELOG.md was updated in the isolated directory
        changelog_isolated_path = isolated_path / "CHANGELOG.md"
        assert changelog_isolated_path.exists()
        changelog_content_isolated = changelog_isolated_path.read_text()
        assert changelog_entry_header in changelog_content_isolated, \
            f"New version header not found in isolated CHANGELOG.md:\n{changelog_content_isolated}"


@patch('khora_kernel.cli.plugin_commands.find_installed_plugins')
def test_list_plugins_e2e(
    mock_find_plugins,
    khora_cli_runner: CliRunner,
    scaffolded_minimal_project: pathlib.Path # Used for isolated_filesystem context
):
    project_fixture_path = scaffolded_minimal_project # Context for running the command

    # Mock the return value of find_installed_plugins
    mock_plugins = [
        {"name": "TestPluginA", "version": "1.0", "path": "path/to/plugin_a", "error": None, "type": "core", "entry_point": "plugin_a"},
        {"name": "TestPluginB", "version": "0.5", "path": "path/to/plugin_b", "error": "Load Error", "type": "user", "entry_point": "plugin_b"},
    ]
    mock_find_plugins.return_value = mock_plugins

    # list-plugins doesn't strictly need a project context unless plugins are discovered from pyproject.toml
    # For this test with mocked find_installed_plugins, an empty isolated directory is fine.
    with khora_cli_runner.isolated_filesystem() as isolated_dir_str: # No temp_dir, uses fresh temp
        # No files need to be copied for list-plugins with mocked discovery
        result_list_plugins = khora_cli_runner.invoke(main_cli, ['list-plugins'], catch_exceptions=False)
    
    assert result_list_plugins.exit_code == 0, f"list-plugins failed: {result_list_plugins.output}"
    
    output = result_list_plugins.output
    assert "TestPluginA (v1.0)" in output
    assert "TestPluginB (v0.5)" in output # Name and version are printed
    assert "user" not in output # Type is NOT printed in non-verbose
    assert "Load Error" not in output # Error is NOT printed in non-verbose
    # If JSON output for plugins is required, a separate command or option would be needed.

```