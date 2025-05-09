"""
Knowledge Graph (KG) extension for Khora Kernel.

This extension extracts knowledge graph concepts, rules, and relationships from markdown files
and generates kg/concepts.json, kg/rules.json, and kg/relationships.json files.

## Markdown Syntax

The KG extension recognizes the following syntax in markdown files:

1. Concepts: `[concept:ConceptName] - Description of the concept`
   - ConceptName should be CamelCase
   - Description can span multiple lines

2. Rules: `[rule:RuleName] - Description of the rule`
   - RuleName should be CamelCase
   - Description can span multiple lines

3. Relationships: `[rel:SourceConcept->TargetConcept:RelationType] - Description of the relationship`
   - SourceConcept is the name of the concept where the relationship originates
   - TargetConcept is the name of the concept where the relationship ends
   - RelationType describes the type of relationship (e.g., "Contains", "DependsOn", "Extends")
   - All names should be CamelCase
   - Description can span multiple lines

## Generated Files

The extension generates three JSON files in the project's `kg/` directory:

1. `concepts.json`: Contains all extracted concepts with their descriptions and source locations
2. `rules.json`: Contains all extracted rules with their descriptions and source locations
3. `relationships.json`: Contains all extracted relationships with their descriptions and source locations

These files are used by the core extension to generate the knowledge graph summary in context.yaml.
"""
import argparse
import logging
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union, NamedTuple

from pyscaffold.actions import Action, ActionParams, ScaffoldOpts, Structure
from pyscaffold.extensions import Extension
from pyscaffold.operations import no_overwrite

# Set up logging
logger = logging.getLogger(__name__)

# Regular expressions for extracting concepts, rules, and relationships
CONCEPT_PATTERN = r"\[concept:([a-zA-Z0-9]*)\]\s*[-–]\s*(.*?)(?=\n\n|\n\[|\Z)"
RULE_PATTERN = r"\[rule:([a-zA-Z0-9]*)\]\s*[-–]\s*(.*?)(?=\n\n|\n\[|\Z)"
RELATIONSHIP_PATTERN = r"\[rel:([a-zA-Z0-9]*)->([a-zA-Z0-9]*):([a-zA-Z0-9]*)\]\s*[-–]\s*(.*?)(?=\n\n|\n\[|\Z)"

class KGEntry:
    """Represents a Knowledge Graph entry (concept or rule)."""
    
    def __init__(self, name: str, description: str, source_file: str = "", line_number: int = 0):
        self.name = name
        self.description = description
        self.source_file = source_file
        self.line_number = line_number
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "source": {
                "file": self.source_file,
                "line": self.line_number
            }
        }
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, KGEntry):
            return False
        return (
            self.name == other.name and 
            self.description == other.description
        )
    
    def __hash__(self) -> int:
        return hash((self.name, self.description))


class RelationshipEntry:
    """Represents a relationship between two concepts in the Knowledge Graph."""
    
    def __init__(
        self, 
        source_concept: str, 
        target_concept: str, 
        relation_type: str,
        description: str, 
        source_file: str = "", 
        line_number: int = 0
    ):
        self.source_concept = source_concept
        self.target_concept = target_concept
        self.relation_type = relation_type
        self.description = description
        self.source_file = source_file
        self.line_number = line_number
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for JSON serialization."""
        return {
            "source_concept": self.source_concept,
            "target_concept": self.target_concept,
            "relation_type": self.relation_type,
            "description": self.description,
            "source": {
                "file": self.source_file,
                "line": self.line_number
            }
        }
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, RelationshipEntry):
            return False
        return (
            self.source_concept == other.source_concept and
            self.target_concept == other.target_concept and
            self.relation_type == other.relation_type and
            self.description == other.description
        )
    
    def __hash__(self) -> int:
        return hash((self.source_concept, self.target_concept, 
                     self.relation_type, self.description))


class KGExtension(Extension):
    """
    PyScaffold extension for Knowledge Graph extraction.
    
    This extension scans Markdown files for [concept:] and [rule:] tags and
    generates kg/concepts.json and kg/rules.json files.
    """
    
    name = "khora_kg"  # This will appear as --khora-kg in the command line
    
    def augment_cli(self, parser: argparse.ArgumentParser):
        """Add a CLI option for this extension."""
        parser.add_argument(
            self.flag,
            dest=self.name,
            action="store_true",
            default=False,
            help="Enable Knowledge Graph extraction from markdown files",
        )
        return self
    
    def activate(self, actions: List[Action]) -> List[Action]:
        """Activate extension rules."""
        if not self.opts.get(self.name):
            return actions
            
        logger.info("Activating Khora Knowledge Graph Extension...")
        
        # Register action to extract concepts and rules and generate JSON files
        actions = self.register(
            actions, extract_and_generate_kg_files, after="define_structure"
        )
        
        return actions


def extract_concepts_and_rules(
    markdown_content: str, file_path: str = ""
) -> Tuple[List[KGEntry], List[KGEntry], List[RelationshipEntry]]:
    """
    Extract concepts, rules, and relationships from markdown content.
    
    Args:
        markdown_content: The content of a markdown file.
        file_path: The path to the markdown file (for reference).
        
    Returns:
        A tuple containing lists of concept, rule, and relationship entries.
    """
    concepts = []
    rules = []
    relationships = []
    
    # Find all concept matches
    concept_matches = re.finditer(CONCEPT_PATTERN, markdown_content, re.DOTALL)
    for match in concept_matches:
        name = match.group(1)
        description = match.group(2).strip()
        
        # Calculate approximate line number (crude estimation)
        line_number = markdown_content[:match.start()].count('\n') + 1
        
        # Validate concept name and description
        if not name:
            logger.warning(
                f"Found empty concept name in {file_path}:{line_number}"
            )
            continue
            
        if not description:
            logger.warning(
                f"Found empty description for concept '{name}' in {file_path}:{line_number}"
            )
            continue
            
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
            logger.warning(
                f"Concept name '{name}' in {file_path}:{line_number} should be CamelCase"
            )
        
        concepts.append(KGEntry(name, description, file_path, line_number))
    
    # Find all rule matches
    rule_matches = re.finditer(RULE_PATTERN, markdown_content, re.DOTALL)
    for match in rule_matches:
        name = match.group(1)
        description = match.group(2).strip()
        
        # Calculate approximate line number
        line_number = markdown_content[:match.start()].count('\n') + 1
        
        # Validate rule name and description  
        if not name:
            logger.warning(
                f"Found empty rule name in {file_path}:{line_number}"
            )
            continue
            
        if not description:
            logger.warning(
                f"Found empty description for rule '{name}' in {file_path}:{line_number}"
            )
            continue
            
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
            logger.warning(
                f"Rule name '{name}' in {file_path}:{line_number} should be CamelCase"
            )
        
        rules.append(KGEntry(name, description, file_path, line_number))
    
    # Find all relationship matches
    relationship_matches = re.finditer(RELATIONSHIP_PATTERN, markdown_content, re.DOTALL)
    for match in relationship_matches:
        source_concept = match.group(1)
        target_concept = match.group(2)
        relation_type = match.group(3)
        description = match.group(4).strip()
        
        # Calculate approximate line number
        line_number = markdown_content[:match.start()].count('\n') + 1
        
        # Validate relationship components
        if not source_concept or not target_concept or not relation_type:
            if not source_concept:
                logger.warning(
                    f"Missing source concept in relationship in {file_path}:{line_number}"
                )
            if not target_concept:
                logger.warning(
                    f"Missing target concept in relationship in {file_path}:{line_number}"
                )
            if not relation_type:
                logger.warning(
                    f"Missing relation type in relationship in {file_path}:{line_number}"
                )
            continue
            
        # Validate that source and target are CamelCase
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', source_concept):
            logger.warning(
                f"Relationship source '{source_concept}' in {file_path}:{line_number} should be CamelCase"
            )
            
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', target_concept):
            logger.warning(
                f"Relationship target '{target_concept}' in {file_path}:{line_number} should be CamelCase"
            )
            
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', relation_type):
            logger.warning(
                f"Relationship type '{relation_type}' in {file_path}:{line_number} should be CamelCase"
            )
        
        relationships.append(RelationshipEntry(
            source_concept, target_concept, relation_type, description, file_path, line_number
        ))
    
    return concepts, rules, relationships


def scan_markdown_files(docs_dir: Path) -> Tuple[List[KGEntry], List[KGEntry], List[RelationshipEntry]]:
    """
    Scan all markdown files in the docs directory for concepts, rules, and relationships.
    
    Args:
        docs_dir: Path to the docs directory.
        
    Returns:
        A tuple containing lists of all concept, rule, and relationship entries.
    """
    all_concepts: List[KGEntry] = []
    all_rules: List[KGEntry] = []
    all_relationships: List[RelationshipEntry] = []
    seen_concepts: Set[str] = set()
    seen_rules: Set[str] = set()
    seen_relationships: Set[Tuple[str, str, str]] = set()  # (source, target, type)
    
    # Find all markdown files
    markdown_files = list(docs_dir.glob("**/*.md"))
    logger.info(f"Found {len(markdown_files)} markdown files in {docs_dir}")
    
    for md_file in markdown_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            rel_path = md_file.relative_to(docs_dir.parent)
            
            file_concepts, file_rules, file_relationships = extract_concepts_and_rules(content, str(rel_path))
            
            # Check for duplicates
            for concept in file_concepts:
                if concept.name in seen_concepts:
                    logger.warning(
                        f"Duplicate concept '{concept.name}' found in {rel_path}"
                    )
                seen_concepts.add(concept.name)
                all_concepts.append(concept)
                
            for rule in file_rules:
                if rule.name in seen_rules:
                    logger.warning(
                        f"Duplicate rule '{rule.name}' found in {rel_path}"
                    )
                seen_rules.add(rule.name)
                all_rules.append(rule)
                
            for relationship in file_relationships:
                rel_key = (relationship.source_concept, relationship.target_concept, relationship.relation_type)
                if rel_key in seen_relationships:
                    logger.warning(
                        f"Duplicate relationship '{relationship.source_concept}->{relationship.target_concept}:{relationship.relation_type}' found in {rel_path}"
                    )
                seen_relationships.add(rel_key)
                all_relationships.append(relationship)
                
        except Exception as e:
            logger.error(f"Error processing {md_file}: {e}")
    
    logger.info(f"Extracted {len(all_concepts)} concepts, {len(all_rules)} rules, and {len(all_relationships)} relationships")
    return all_concepts, all_rules, all_relationships


def generate_kg_files(
    project_dir: Path, 
    concepts: List[KGEntry], 
    rules: List[KGEntry],
    relationships: List[RelationshipEntry]
) -> Tuple[Path, Path, Path]:
    """
    Generate concepts.json, rules.json, and relationships.json files.
    
    Args:
        project_dir: The root directory of the project.
        concepts: List of extracted concept entries.
        rules: List of extracted rule entries.
        relationships: List of extracted relationship entries.
        
    Returns:
        A tuple containing the paths to the generated files.
    """
    # Create kg directory if it doesn't exist
    kg_dir = project_dir / "kg"
    kg_dir.mkdir(exist_ok=True)
    
    concepts_file = kg_dir / "concepts.json"
    rules_file = kg_dir / "rules.json"
    relationships_file = kg_dir / "relationships.json"
    
    # Create concepts.json
    concepts_data = {
        "version": "0.1.0",
        "generated_at": datetime.now().isoformat(),
        "concepts": [concept.to_dict() for concept in concepts]
    }
    
    with open(concepts_file, "w", encoding="utf-8") as f:
        json.dump(concepts_data, f, indent=2)
        
    # Create rules.json
    rules_data = {
        "version": "0.1.0",
        "generated_at": datetime.now().isoformat(),
        "rules": [rule.to_dict() for rule in rules]
    }
    
    with open(rules_file, "w", encoding="utf-8") as f:
        json.dump(rules_data, f, indent=2)
        
    # Create relationships.json
    relationships_data = {
        "version": "0.1.0",
        "generated_at": datetime.now().isoformat(),
        "relationships": [relationship.to_dict() for relationship in relationships]
    }
    
    with open(relationships_file, "w", encoding="utf-8") as f:
        json.dump(relationships_data, f, indent=2)
        
    logger.info(f"Generated {concepts_file} with {len(concepts)} concepts")
    logger.info(f"Generated {rules_file} with {len(rules)} rules")
    logger.info(f"Generated {relationships_file} with {len(relationships)} relationships")
    
    return concepts_file, rules_file, relationships_file


class ValidationResult(NamedTuple):
    """Result of a validation operation."""
    valid: bool
    warnings: List[str]
    error_count: int


def validate_source_links(
    entries: List[KGEntry], project_dir: Path
) -> ValidationResult:
    """
    Validate that source links in KG entries point to existing files.
    
    Args:
        entries: List of KG entries to validate
        project_dir: Root directory of the project
        
    Returns:
        ValidationResult with validation status and warnings
    """
    warnings = []
    error_count = 0
    
    for entry in entries:
        if not entry.source_file:
            continue  # Skip entries without source info
            
        # Resolve the source file path relative to the project root
        source_path = project_dir / entry.source_file
        
        if not source_path.exists():
            warning_msg = f"Source file '{entry.source_file}' for {entry.__class__.__name__[2:].lower()} '{entry.name}' does not exist"
            warnings.append(warning_msg)
            logger.warning(warning_msg)
            error_count += 1
    
    return ValidationResult(
        valid=(error_count == 0),
        warnings=warnings,
        error_count=error_count
    )


def extract_and_generate_kg_files(
    struct: Structure, opts: ScaffoldOpts
) -> ActionParams:
    """
    Extract KG entries from markdown files and generate JSON files.
    
    Args:
        struct: Project representation as a nested dict.
        opts: PyScaffold options.
        
    Returns:
        Updated project structure and options.
    """
    logger.info("Extracting Knowledge Graph entries from markdown files...")
    
    # Get the Khora configuration from opts
    khora_config = opts.get("khora_config")
    if not khora_config:
        logger.warning("Khora config not found. Skipping KG extraction.")
        return struct, opts
        
    # Get the docs directory from config
    docs_dir_str = getattr(khora_config.paths, "docs_dir", "docs")
    project_dir = Path(opts.get("project_path", "."))
    docs_dir = project_dir / docs_dir_str
    
    # Create the docs directory if it doesn't exist
    docs_dir.mkdir(exist_ok=True, parents=True)
    
    # Scan markdown files for concepts, rules, and relationships
    concepts, rules, relationships = scan_markdown_files(docs_dir)
    
    # Validate source links
    logger.info("Validating source links for KG entries...")
    concept_validation = validate_source_links(concepts, project_dir)
    rule_validation = validate_source_links(rules, project_dir)
    relationship_validation = validate_source_links(relationships, project_dir)
    
    # Store validation results in opts for health command or other extensions
    opts["kg_validation"] = {
        "concepts": concept_validation._asdict(),
        "rules": rule_validation._asdict(),
        "relationships": relationship_validation._asdict(),
        "total_errors": (
            concept_validation.error_count + 
            rule_validation.error_count + 
            relationship_validation.error_count
        ),
        "warnings": (
            concept_validation.warnings + 
            rule_validation.warnings + 
            relationship_validation.warnings
        )
    }
    
    # Generate JSON files
    if concepts or rules or relationships:
        concepts_file, rules_file, relationships_file = generate_kg_files(
            project_dir, concepts, rules, relationships
        )
        
        # Add kg schema file to structure
        kg_schema = {
            "version": "0.1.0",
            "concepts": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "source": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "line": {"type": "integer"}
                        }
                    }
                }
            },
            "rules": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "source": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "line": {"type": "integer"}
                        }
                    }
                }
            },
            "relationships": {
                "type": "object",
                "properties": {
                    "source_concept": {"type": "string"},
                    "target_concept": {"type": "string"},
                    "relation_type": {"type": "string"},
                    "description": {"type": "string"},
                    "source": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "line": {"type": "integer"}
                        }
                    }
                }
            }
        }
        
        kg_schema_content = json.dumps(kg_schema, indent=2)
        kg_dir = struct.setdefault("kg", {})
        kg_dir["kg_schema.json"] = (kg_schema_content, no_overwrite())
        
        # Store the concepts, rules, and relationships in opts for other extensions to use
        # (particularly the core extension for context.yaml)
        opts["kg_concepts"] = concepts
        opts["kg_rules"] = rules
        opts["kg_relationships"] = relationships
        
        # Add a summary of relationships for context.yaml
        if relationships:
            rel_summary = {
                "count": len(relationships),
                "types": list(set(rel.relation_type for rel in relationships))
            }
            opts["kg_relationship_summary"] = rel_summary
        
    return struct, opts


# Hook for running KG extraction during pre-commit
def precommit_kg_hook(project_dir: Union[str, Path]) -> Dict[str, Any]:
    """
    Define a pre-commit hook configuration for KG extraction.
    
    Args:
        project_dir: The root directory of the project.
        
    Returns:
        A dictionary with the hook configuration.
    """
    return {
        "id": "khora-knowledge-graph",
        "name": "Khora Knowledge Graph Extractor",
        "entry": "python -m khora_kernel_vnext.extensions.kg.kg_precommit",
        "language": "python",
        "files": r"\.md$",
        "pass_filenames": True,
    }
