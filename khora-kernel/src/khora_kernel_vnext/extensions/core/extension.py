"""
Core extension for Khora Kernel.
"""
import argparse
import logging
from typing import List
from datetime import datetime, timezone # Added for timestamp
from pathlib import Path # Added for VERSION file path
import yaml # Added for YAML generation

from pyscaffold.actions import Action, ActionParams, ScaffoldOpts, Structure
from pyscaffold.extensions import Extension
from pyscaffold.operations import no_overwrite
# from pyscaffold.structure import merge_structure # Removed this import

# manifest.py provides KhoraManifestConfig for parsing and validation.
from .manifest import (
    KhoraManifestConfig,
    KhoraManifestNotFoundError,
    KhoraManifestInvalidError,
)

logger = logging.getLogger(__name__)


class CoreExtension(Extension):
    """
    PyScaffold extension to handle Khora-specific project scaffolding.
    """

    persist = True  # Keep the extension active for subsequent actions
    # The name of the command line option, without the leading --
    # e.g. --khora-core becomes "khora-core"
    # PyScaffold will also make sure this is a valid Python identifier
    # by replacing "-" with "_"
    name = "khora_core" # This will be used as --khora-core

    def augment_cli(self, parser: argparse.ArgumentParser):
        """Add a CLI option for this extension"""
        parser.add_argument(
            self.flag, # self.flag is derived from self.name
            dest=self.name, # Will be stored in opts.khora_core
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
        """Activate extension rules. See :obj:`pyscaffold.actions`."""

        # We need to check if our flag was set
        # (e.g. if the user used --khora-core)
        # `self.opts` is the parsed CLI arguments
        if not self.opts.get(self.name): # self.opts.khora_core
            return actions

        logger.info("Activating Khora Core Extension...")

        # --- Step 1: Parse the Khora manifest from pyproject.toml ---
        # Assuming the pyproject.toml is in the root of the project being created
        # PyScaffold's opts should contain the project path where pyproject.toml is located.
        project_path = self.opts.get("project_path")
        if not project_path:
            logger.error("Project path not found in PyScaffold options. Cannot parse Khora manifest.")
            self.opts["khora_config"] = None # Indicate failure or absence of config
            return actions # Potentially stop further processing by this extension

        # Get the environment from CLI options if provided
        env = self.opts.get("khora_env")
        if env:
            logger.info(f"Using environment '{env}' for manifest layering")
        
        try:
            # Use the environment-aware method to load the manifest
            khora_config = KhoraManifestConfig.from_project_toml_with_env(project_path, env=env)
            
            # Log the active environment if any
            env_status = f" with '{khora_config.active_environment}' environment" if khora_config.active_environment else ""
            logger.info(
                f"Successfully parsed Khora manifest from {project_path / 'pyproject.toml'}{env_status}: "
                f"{khora_config.model_dump(mode='json')}" # Use model_dump for Pydantic models
            )
            
            # Store the parsed config in opts for other actions/extensions to use
            self.opts["khora_config"] = khora_config
        except KhoraManifestNotFoundError:
            logger.warning(
                f"pyproject.toml or [tool.khora] section not found in {project_path}. "
                "Khora manifest not parsed."
            )
            self.opts["khora_config"] = None
        except KhoraManifestInvalidError as e:
            logger.error(
                f"Invalid Khora manifest in {project_path / 'pyproject.toml'}: {e.errors}"
            )
            self.opts["khora_config"] = None
        except Exception as e:
            logger.error(
                f"Unexpected error parsing Khora manifest from {project_path / 'pyproject.toml'}: {e}"
            )
            self.opts["khora_config"] = None
            # If manifest parsing fails, we might not want to proceed with context generation
            # or generate a context file indicating the issue. For now, let's assume
            # if khora_config is None, _generate_khora_context_yaml will handle it.

        # --- Step 2: Register action to generate .khora/context.yaml ---
        # This fulfills MVK-CORE-03
        actions = self.register(
            actions, self._generate_khora_context_yaml, after="define_structure"
        )

        logger.info("Khora Core Extension activated and context generation registered.")
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
                "last_updated": None
            }
            
            # Process concepts file if it exists
            if concepts_file.exists():
                try:
                    import json
                    from hashlib import sha1
                    
                    concepts_data = json.loads(concepts_file.read_text(encoding="utf-8"))
                    concepts = concepts_data.get("concepts", [])
                    
                    kg_summary["concept_count"] = len(concepts)
                    kg_summary["concepts_hash"] = sha1(json.dumps(concepts, sort_keys=True).encode()).hexdigest()
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
                    kg_summary["rules_hash"] = sha1(json.dumps(rules, sort_keys=True).encode()).hexdigest()
                    
                    # Use rules last_updated if no concepts or if rules are newer
                    rules_updated = rules_data.get("generated_at")
                    if rules_updated and (not kg_summary["last_updated"] or rules_updated > kg_summary["last_updated"]):
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
                    
                    relationships_data = json.loads(relationships_file.read_text(encoding="utf-8"))
                    relationships = relationships_data.get("relationships", [])
                    
                    kg_summary["relationship_count"] = len(relationships)
                    kg_summary["relationships_hash"] = sha1(json.dumps(relationships, sort_keys=True).encode()).hexdigest()
                    
                    # Extract unique relationship types
                    if relationships:
                        relation_types = set()
                        for rel in relationships:
                            if "relation_type" in rel:
                                relation_types.add(rel["relation_type"])
                        kg_summary["relationship_types"] = sorted(list(relation_types))
                    
                    # Use relationships last_updated if it's newer than concepts and rules
                    relationships_updated = relationships_data.get("generated_at")
                    if relationships_updated and (not kg_summary["last_updated"] or relationships_updated > kg_summary["last_updated"]):
                        kg_summary["last_updated"] = relationships_updated
                    
                    logger.info(f"Found {len(relationships)} relationships in {relationships_file}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error processing relationships.json - invalid JSON: {e}")
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
            if hasattr(self, 'opts') and self.opts:
                concepts = self.opts.get("kg_concepts", [])
                rules = self.opts.get("kg_rules", [])
                relationships = self.opts.get("kg_relationships", [])
                
                # Get relationship summary if available
                rel_summary = self.opts.get("kg_relationship_summary", {})
                if rel_summary:
                    kg_summary["relationship_count"] = rel_summary.get("count", 0)
                    kg_summary["relationship_types"] = rel_summary.get("types", [])
            
            if concepts or rules or relationships:
                import json
                from hashlib import sha1
                from datetime import datetime, timezone
                
                kg_summary["concept_count"] = len(concepts)
                if concepts:
                    concept_dicts = [c.to_dict() for c in concepts]
                    kg_summary["concepts_hash"] = sha1(json.dumps(concept_dicts, sort_keys=True).encode()).hexdigest()
                
                kg_summary["rule_count"] = len(rules)
                if rules:
                    rule_dicts = [r.to_dict() for r in rules]
                    kg_summary["rules_hash"] = sha1(json.dumps(rule_dicts, sort_keys=True).encode()).hexdigest()
                
                kg_summary["relationship_count"] = len(relationships)
                if relationships:
                    relationship_dicts = [r.to_dict() for r in relationships]
                    kg_summary["relationships_hash"] = sha1(json.dumps(relationship_dicts, sort_keys=True).encode()).hexdigest()
                    
                    # Extract relationship types if not already provided in summary
                    if not kg_summary["relationship_types"] and relationships:
                        relation_types = set()
                        for rel in relationships:
                            relation_types.add(rel.relation_type)
                        kg_summary["relationship_types"] = sorted(list(relation_types))
                
                kg_summary["last_updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                
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
        """
        logger.info("Attempting to generate .khora/context.yaml...")

        khora_config: KhoraManifestConfig = opts.get("khora_config")
        project_path: Path = opts.get("project_path")

        if not project_path:
            logger.error("Project path not available in opts. Cannot determine project name for context.yaml.")
            # Potentially create a context.yaml with an error or skip
            return struct, opts
        
        project_name = project_path.name

        if not khora_config:
            logger.warning(
                "Khora manifest config not found or failed to parse. "
                "Generating .khora/context.yaml with minimal/default information."
            )
            # Fallback values if manifest is missing or invalid
            project_description = "N/A (Khora manifest not found or invalid)"
            project_paths_data = {}
        else:
            project_description = khora_config.project_description
            project_paths_data = khora_config.paths.model_dump(mode='json') if khora_config.paths else {}

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

        # Get component info from opts if available
        component_info = opts.get("component_info", {})
        
        context_data = {
            "kernel_version": kernel_version,
            "schema_version": schema_version,
            "generated_at": generated_at,
            "project": {
                "name": project_name,
                "description": project_description,
                "paths": project_paths_data,
            },
            "knowledge_graph_summary": self._generate_kg_summary(project_path),
            "components": component_info,
        }
        
        # Add environment information if available
        if khora_config and khora_config.active_environment:
            context_data["environment"] = {
                "name": khora_config.active_environment,
                "applied": True,
                "description": f"Configuration using '{khora_config.active_environment}' environment overrides"
            }

        try:
            # Use sort_keys=False to maintain insertion order if desired, though not critical for YAML
            # Dumper options can be added if specific formatting is needed (e.g., default_flow_style)
            context_yaml_content = yaml.dump(context_data, sort_keys=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to serialize context.yaml data to YAML: {e}")
            # Create a placeholder or error content if YAML generation fails
            context_yaml_content = (
                f"# Error generating context.yaml content: {e}\n"
                f"# Raw data: {context_data}"
            )
        
        logger.info(f"Generated context.yaml content:\n{context_yaml_content.strip()}")

        khora_files: Structure = {
            # PyScaffold will create .khora directory if it doesn't exist
            # when merging this structure.
            ".khora": {
                "context.yaml": (context_yaml_content, no_overwrite()) # no_overwrite is a sensible default
            }
        }
        
        # Ensure .khora directory and context.yaml are created
        # The merge operation with ensure_existence (default for files) handles this.
        # We can also explicitly use ensure_existence if there are concerns.
        # struct = ensure_existence(struct, opts) # Usually done by PyScaffold before custom actions like this one.

        logger.info(f"Merging .khora/context.yaml into project structure for {project_name}")
        struct.update(khora_files) # Use dict.update() to merge
        return struct, opts
