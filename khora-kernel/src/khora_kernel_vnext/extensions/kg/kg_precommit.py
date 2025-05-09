#!/usr/bin/env python
"""
Pre-commit hook for Knowledge Graph extraction.

This script is called by pre-commit when markdown files are modified,
and it updates the concepts.json and rules.json files.
"""
import json
import logging
import sys
from pathlib import Path
from typing import List

from .extension import extract_concepts_and_rules, generate_kg_files

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("khora-kg-precommit")


def main(md_files: List[str]) -> int:
    """
    Run KG extraction on the provided Markdown files.
    
    Args:
        md_files: List of Markdown file paths passed by pre-commit.
        
    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    try:
        project_root = Path.cwd()
        logger.info(f"Processing {len(md_files)} Markdown files in {project_root}")
        
        # We'll collect all concepts, rules, and relationships from all files
        all_concepts = []
        all_rules = []
        all_relationships = []
        
        for md_file in md_files:
            file_path = Path(md_file)
            if not file_path.exists() or not file_path.is_file():
                logger.warning(f"File not found or not a file: {md_file}")
                continue
                
            try:
                content = file_path.read_text(encoding="utf-8")
                rel_path = file_path.relative_to(project_root)
                
                file_concepts, file_rules, file_relationships = extract_concepts_and_rules(content, str(rel_path))
                
                all_concepts.extend(file_concepts)
                all_rules.extend(file_rules)
                all_relationships.extend(file_relationships)
                
                if file_concepts or file_rules or file_relationships:
                    logger.info(
                        f"Extracted {len(file_concepts)} concepts, {len(file_rules)} rules, "
                        f"and {len(file_relationships)} relationships from {rel_path}"
                    )
            except Exception as e:
                logger.error(f"Error processing {md_file}: {e}")
                continue
        
        # Now, load existing KG files (if any) to merge with new entries
        try:
            kg_dir = project_root / "kg"
            if kg_dir.exists():
                concepts_file = kg_dir / "concepts.json"
                rules_file = kg_dir / "rules.json"
                
                if concepts_file.exists():
                    try:
                        concepts_data = json.loads(concepts_file.read_text(encoding="utf-8"))
                        existing_concepts = concepts_data.get("concepts", [])
                        logger.info(f"Loaded {len(existing_concepts)} existing concepts")
                        
                        # Merge with existing concepts (more sophisticated merging could be implemented)
                        # For now, just overwrite
                    except Exception as e:
                        logger.error(f"Error loading existing concepts.json: {e}")
                
                if rules_file.exists():
                    try:
                        rules_data = json.loads(rules_file.read_text(encoding="utf-8"))
                        existing_rules = rules_data.get("rules", [])
                        logger.info(f"Loaded {len(existing_rules)} existing rules")
                        
                        # Merge with existing rules (more sophisticated merging could be implemented)
                        # For now, just overwrite
                    except Exception as e:
                        logger.error(f"Error loading existing rules.json: {e}")
        except Exception as e:
            logger.error(f"Error loading existing KG files: {e}")
        
        # Only update files if we found concepts, rules or relationships
        if all_concepts or all_rules or all_relationships:
            _, _, _ = generate_kg_files(project_root, all_concepts, all_rules, all_relationships)
            
            # Also update context.yaml with KG summary information
            try:
                from hashlib import sha1
                import yaml
                from datetime import datetime, timezone
                
                khora_dir = project_root / ".khora"
                context_file = khora_dir / "context.yaml"
                
                if khora_dir.exists() and context_file.exists():
                    context_data = yaml.safe_load(context_file.read_text(encoding="utf-8"))
                    
                    # Create or update knowledge_graph_summary section
                    kg_summary = {
                        "concepts_hash": sha1(json.dumps(all_concepts, sort_keys=True).encode()).hexdigest() if all_concepts else None,
                        "rules_hash": sha1(json.dumps(all_rules, sort_keys=True).encode()).hexdigest() if all_rules else None,
                        "relationships_hash": sha1(json.dumps(all_relationships, sort_keys=True).encode()).hexdigest() if all_relationships else None,
                        "concept_count": len(all_concepts),
                        "rule_count": len(all_rules),
                        "relationship_count": len(all_relationships),
                        "source_dir": "kg",
                        "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds")
                    }
                    
                    context_data["knowledge_graph_summary"] = kg_summary
                    
                    # Write updated context.yaml
                    with open(context_file, "w", encoding="utf-8") as f:
                        yaml.dump(context_data, f, sort_keys=False, indent=2)
                    
                    logger.info(f"Updated knowledge graph summary in {context_file}")
            except Exception as e:
                logger.error(f"Error updating context.yaml: {e}")
        
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    # Files are passed as arguments by pre-commit
    exit_code = main(sys.argv[1:])
    sys.exit(exit_code)
