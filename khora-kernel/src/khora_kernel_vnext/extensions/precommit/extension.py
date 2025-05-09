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
        if not self.opts.get(self.name):
            return actions
            
        logger.info("Activating Khora Pre-commit Extension...")
        
        # Register action to generate pre-commit config
        actions = self.register(
            actions, add_precommit_config, after="define_structure"
        )
        
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
    # Get the Pydantic model from opts
    khora_config = opts.get("khora_config")
    
    if not khora_config:
        try:
            # Try to load it directly from pyproject.toml if not in opts
            from ..core.manifest import KhoraManifestConfig
            project_path = opts.get("project_path", ".")
            logger.warning(f"Khora config not found in opts. Attempting to load from {project_path}/pyproject.toml")
            khora_config = KhoraManifestConfig.from_project_toml(project_path)
            opts["khora_config"] = khora_config  # Store it for future use
        except Exception as e:
            logger.error(f"Failed to load Khora config from pyproject.toml: {e}")
            return struct, opts
        
    # Check if the pre-commit feature is enabled
    if not getattr(khora_config.features, "precommit", False):
        logger.info("Khora Pre-commit feature not enabled. Skipping pre-commit config generation.")
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
                "hooks": [
                    {"id": "ruff", "args": ["--fix"]},
                    {"id": "ruff-format"}
                ]
            },
            {
                "repo": "https://github.com/pre-commit/pre-commit-hooks",
                "rev": "v4.4.0",
                "hooks": [
                    {"id": "trailing-whitespace"},
                    {"id": "end-of-file-fixer"},
                    {"id": "check-yaml"},
                    {"id": "debug-statements"},
                    {"id": "check-toml"}
                ]
            }
        ]
    }
    
    # Add security hooks if enabled
    if security_gates_enabled:
        precommit_config["repos"].append({
            "repo": "https://github.com/PyCQA/bandit",
            "rev": "1.7.5",
            "hooks": [
                {
                    "id": "bandit",
                    "args": ["-x", "./tests", "-c", "pyproject.toml"]
                }
            ]
        })
        
        precommit_config["repos"].append({
            "repo": "https://github.com/trufflesecurity/trufflehog",
            "rev": "v3.63.0",
            "hooks": [
                {
                    "id": "trufflehog",
                    "name": "TruffleHog OSS",
                    "entry": "trufflehog filesystem --no-verification .",
                    "language": "system",
                    "pass_filenames": False
                }
            ]
        })
    
    # Add knowledge graph hook if enabled
    if kg_enabled:
        project_name = opts.get("project_name")
        if not project_name:
            project_name = "khora_project"  # Default fallback
        
        precommit_config["repos"].append({
            "repo": "local",
            "hooks": [
                {
                    "id": "khora-knowledge-graph",
                    "name": "Khora Knowledge Graph Extractor",
                    "entry": "python -m khora_kernel_vnext.extensions.kg.kg_precommit",
                    "language": "python",
                    "files": r"\.md$",
                    "pass_filenames": True
                }
            ]
        })
    
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
    
    logger.info("Generated .pre-commit-config.yaml with standard hooks and custom Khora hooks.")
    
    return struct, opts
