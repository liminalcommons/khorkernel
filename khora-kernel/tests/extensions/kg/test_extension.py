"""
Tests for the Knowledge Graph extension.
"""

import json
import os
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from khora_kernel_vnext.extensions.kg.extension import (
    KGExtension, 
    KGEntry, 
    RelationshipEntry,
    ValidationResult,
    extract_concepts_and_rules,
    scan_markdown_files,
    generate_kg_files,
    extract_and_generate_kg_files,
    validate_source_links
)


def test_kg_entry():
    """Test KGEntry class."""
    # Create a KG entry
    entry = KGEntry("TestConcept", "Description of test concept", "docs/test.md", 10)
    
    # Check properties
    assert entry.name == "TestConcept"
    assert entry.description == "Description of test concept"
    assert entry.source_file == "docs/test.md"
    assert entry.line_number == 10
    
    # Check to_dict method
    entry_dict = entry.to_dict()
    assert entry_dict["name"] == "TestConcept"
    assert entry_dict["description"] == "Description of test concept"
    assert entry_dict["source"]["file"] == "docs/test.md"
    assert entry_dict["source"]["line"] == 10
    
    # Check equality
    entry2 = KGEntry("TestConcept", "Description of test concept", "docs/other.md", 20)
    assert entry == entry2  # Different source/line but same name/description should be equal
    
    # Check inequality
    entry3 = KGEntry("OtherConcept", "Description of test concept", "docs/test.md", 10)
    assert entry != entry3


def test_relationship_entry():
    """Test RelationshipEntry class."""
    # Create a relationship entry
    entry = RelationshipEntry(
        "SourceConcept", 
        "TargetConcept", 
        "Contains", 
        "Description of relationship", 
        "docs/test.md", 
        10
    )
    
    # Check properties
    assert entry.source_concept == "SourceConcept"
    assert entry.target_concept == "TargetConcept"
    assert entry.relation_type == "Contains"
    assert entry.description == "Description of relationship"
    assert entry.source_file == "docs/test.md"
    assert entry.line_number == 10
    
    # Check to_dict method
    entry_dict = entry.to_dict()
    assert entry_dict["source_concept"] == "SourceConcept"
    assert entry_dict["target_concept"] == "TargetConcept"
    assert entry_dict["relation_type"] == "Contains"
    assert entry_dict["description"] == "Description of relationship"
    assert entry_dict["source"]["file"] == "docs/test.md"
    assert entry_dict["source"]["line"] == 10
    
    # Check equality
    entry2 = RelationshipEntry(
        "SourceConcept", 
        "TargetConcept", 
        "Contains", 
        "Description of relationship", 
        "docs/other.md", 
        20
    )
    assert entry == entry2  # Different source/line but same core data should be equal
    
    # Check inequality
    entry3 = RelationshipEntry(
        "SourceConcept", 
        "DifferentTarget", 
        "Contains", 
        "Description of relationship", 
        "docs/test.md", 
        10
    )
    assert entry != entry3


def test_extract_concepts_and_rules():
    """Test extracting concepts, rules, and relationships from markdown text."""
    markdown = """
# Test Markdown

Some text describing various things.

[concept:TestConcept] - This is a test concept that describes something important.

More text in between.

[rule:TestRule] - This is a test rule that defines some behavior.

More paragraphs could go here.

[concept:AnotherConcept] - This is another concept.
It can span multiple lines.

[rule:BadlyFormatted]-No space after hyphen but should still work.

[rel:TestConcept->AnotherConcept:Contains] - TestConcept contains AnotherConcept.

[rel:AnotherConcept->TestConcept:DependsOn] - AnotherConcept depends on TestConcept.
    """
    
    concepts, rules, relationships = extract_concepts_and_rules(markdown, "test.md")
    
    # Check concepts
    assert len(concepts) == 2
    assert concepts[0].name == "TestConcept"
    assert concepts[0].description == "This is a test concept that describes something important."
    assert concepts[1].name == "AnotherConcept"
    assert concepts[1].description == "This is another concept.\nIt can span multiple lines."
    
    # Check rules
    assert len(rules) == 2
    assert rules[0].name == "TestRule"
    assert rules[0].description == "This is a test rule that defines some behavior."
    assert rules[1].name == "BadlyFormatted"
    assert rules[1].description == "No space after hyphen but should still work."
    
    # Check relationships
    assert len(relationships) == 2
    assert relationships[0].source_concept == "TestConcept"
    assert relationships[0].target_concept == "AnotherConcept"
    assert relationships[0].relation_type == "Contains"
    assert relationships[0].description == "TestConcept contains AnotherConcept."
    
    assert relationships[1].source_concept == "AnotherConcept"
    assert relationships[1].target_concept == "TestConcept"
    assert relationships[1].relation_type == "DependsOn"
    assert relationships[1].description == "AnotherConcept depends on TestConcept."


def test_extract_concepts_and_rules_validation():
    """Test validation of concept, rule, and relationship names."""
    # Non-CamelCase concept/rule/relationship should trigger warning but still get extracted
    markdown = """
[concept:lowercase] - This should trigger a warning for not being CamelCase.
[rule:ALLCAPS] - This is all caps, not CamelCase.
[rel:lowercase->OtherConcept:hasProperty] - This should trigger a warning for source.
[rel:Concept->lowercase:hasProperty] - This should trigger a warning for target.
[rel:Concept->OtherConcept:lowercase] - This should trigger a warning for relation type.
    """
    
    with patch("khora_kernel_vnext.extensions.kg.extension.logger") as mock_logger:
        concepts, rules, relationships = extract_concepts_and_rules(markdown, "test.md")
        
        # Check for warning logs (at least one warning expected)
        assert mock_logger.warning.call_count >= 1
        
        # Concepts/rules/relationships should still be extracted despite warnings
        assert len(concepts) == 1
        assert len(rules) == 1
        assert len(relationships) == 3
        assert concepts[0].name == "lowercase"
        assert rules[0].name == "ALLCAPS"
        
        # Check that relationships were extracted despite warnings
        rel_sources = [r.source_concept for r in relationships]
        rel_targets = [r.target_concept for r in relationships]
        rel_types = [r.relation_type for r in relationships]
        
        assert "lowercase" in rel_sources
        assert "lowercase" in rel_targets
        assert "lowercase" in rel_types


def test_extract_concepts_and_rules_empty_values():
    """Test handling of empty name or description."""
    markdown = """
    [concept:] - Missing name.
    [rule:ValidRule] - 
    [concept:MissingDesc] - 
    [rel:->TargetConcept:RelationType] - Missing source concept.
    [rel:SourceConcept->:RelationType] - Missing target concept.
    [rel:SourceConcept->TargetConcept:] - Missing relation type.
        """
    
    with patch("khora_kernel_vnext.extensions.kg.extension.logger") as mock_logger:
        concepts, rules, relationships = extract_concepts_and_rules(markdown, "test.md")
        
        # Check for warning logs about empty values
        assert mock_logger.warning.call_count >= 1
        
        # Valid entries should be extracted, invalid ones should be skipped
        # Current implementation: concepts with empty names are skipped, but rules with 
        # empty descriptions are still extracted (with empty description)
        assert len(concepts) == 0  # Both concepts have issues
        assert len(rules) == 1  # Rule is extracted even with empty description
        assert len(relationships) == 0  # All relationships have issues and should be skipped


@pytest.fixture
def sample_docs_dir():
    """Create a temporary docs directory with markdown files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir()
        
        # Create some markdown files with concepts, rules, and relationships
        file1 = docs_dir / "file1.md"
        file1.write_text("""
# File 1
[concept:ConceptOne] - First concept.
[rule:RuleOne] - First rule.
[rel:ConceptOne->ConceptTwo:References] - ConceptOne references ConceptTwo.
        """)
        
        file2 = docs_dir / "file2.md"
        file2.write_text("""
# File 2
[concept:ConceptTwo] - Second concept.
[rule:RuleTwo] - Second rule.
[rel:ConceptTwo->ConceptThree:Requires] - ConceptTwo requires ConceptThree.
        """)
        
        # A subdirectory with more files
        subdir = docs_dir / "subdir"
        subdir.mkdir()
        
        file3 = subdir / "file3.md"
        file3.write_text("""
# File 3
[concept:ConceptThree] - Third concept.
[rule:RuleThree] - Third rule.
[rel:ConceptThree->ConceptOne:Extends] - ConceptThree extends ConceptOne.
        """)
        
        # A non-markdown file that should be ignored
        text_file = docs_dir / "ignore.txt"
        text_file.write_text("[concept:Ignored] - This should be ignored.")
        
        yield docs_dir


def test_scan_markdown_files(sample_docs_dir):
    """Test scanning markdown files for concepts, rules, and relationships."""
    concepts, rules, relationships = scan_markdown_files(sample_docs_dir)
    
    # We should have extracted 3 concepts, 3 rules, and 3 relationships from our 3 markdown files
    assert len(concepts) == 3
    assert len(rules) == 3
    assert len(relationships) == 3
    
    # Check concept names
    concept_names = {concept.name for concept in concepts}
    assert concept_names == {"ConceptOne", "ConceptTwo", "ConceptThree"}
    
    # Check rule names
    rule_names = {rule.name for rule in rules}
    assert rule_names == {"RuleOne", "RuleTwo", "RuleThree"}
    
    # Check relationship types
    relation_types = {rel.relation_type for rel in relationships}
    assert relation_types == {"References", "Requires", "Extends"}
    
    # Check relationship connections
    for rel in relationships:
        if rel.relation_type == "References":
            assert rel.source_concept == "ConceptOne"
            assert rel.target_concept == "ConceptTwo"
        elif rel.relation_type == "Requires":
            assert rel.source_concept == "ConceptTwo"
            assert rel.target_concept == "ConceptThree"
        elif rel.relation_type == "Extends":
            assert rel.source_concept == "ConceptThree"
            assert rel.target_concept == "ConceptOne"


def test_scan_markdown_files_duplicates(sample_docs_dir):
    """Test handling of duplicate concept/rule/relationship names."""
    # Add a file with duplicate concept, rule, and relationship
    dup_file = sample_docs_dir / "duplicate.md"
    dup_file.write_text("""
# Duplicate
[concept:ConceptOne] - Duplicate concept.
[rule:UniqueRule] - Not a duplicate.
[rel:ConceptOne->ConceptTwo:References] - Duplicate relationship.
    """)
    
    with patch("khora_kernel_vnext.extensions.kg.extension.logger") as mock_logger:
        concepts, rules, relationships = scan_markdown_files(sample_docs_dir)
        
        # Check for warning about duplicates
        assert mock_logger.warning.call_count >= 2  # At least for concept and relationship
        
        # All concepts, rules and relationships should be extracted (even duplicates)
        assert len(concepts) == 4
        assert len(rules) == 4
        assert len(relationships) == 4


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        yield project_dir


def test_generate_kg_files(temp_project_dir):
    """Test generation of KG JSON files including relationships."""
    # Create sample concepts, rules, and relationships
    concepts = [
        KGEntry("ConceptOne", "First concept", "file1.md", 10),
        KGEntry("ConceptTwo", "Second concept", "file2.md", 20)
    ]
    
    rules = [
        KGEntry("RuleOne", "First rule", "file1.md", 15),
        KGEntry("RuleTwo", "Second rule", "file2.md", 25)
    ]
    
    relationships = [
        RelationshipEntry("ConceptOne", "ConceptTwo", "Contains", "First contains second", "file1.md", 12),
        RelationshipEntry("ConceptTwo", "ConceptOne", "Extends", "Second extends first", "file2.md", 22)
    ]
    
    # Generate KG files
    concepts_file, rules_file, relationships_file = generate_kg_files(
        temp_project_dir, concepts, rules, relationships
    )
    
    # Check that the kg directory and files were created
    kg_dir = temp_project_dir / "kg"
    assert kg_dir.exists()
    assert concepts_file.exists()
    assert rules_file.exists()
    assert relationships_file.exists()
    
    # Check concepts.json content
    with open(concepts_file) as f:
        concepts_data = json.load(f)
        assert "version" in concepts_data
        assert "generated_at" in concepts_data
        assert "concepts" in concepts_data
        assert len(concepts_data["concepts"]) == 2
        assert concepts_data["concepts"][0]["name"] == "ConceptOne"
        assert concepts_data["concepts"][1]["name"] == "ConceptTwo"
    
    # Check rules.json content
    with open(rules_file) as f:
        rules_data = json.load(f)
        assert "version" in rules_data
        assert "generated_at" in rules_data
        assert "rules" in rules_data
        assert len(rules_data["rules"]) == 2
        assert rules_data["rules"][0]["name"] == "RuleOne"
        assert rules_data["rules"][1]["name"] == "RuleTwo"
        
    # Check relationships.json content
    with open(relationships_file) as f:
        rel_data = json.load(f)
        assert "version" in rel_data
        assert "generated_at" in rel_data
        assert "relationships" in rel_data
        assert len(rel_data["relationships"]) == 2
        
        # Check first relationship
        rel1 = rel_data["relationships"][0]
        assert rel1["source_concept"] == "ConceptOne"
        assert rel1["target_concept"] == "ConceptTwo"
        assert rel1["relation_type"] == "Contains"
        assert rel1["description"] == "First contains second"
        
        # Check second relationship
        rel2 = rel_data["relationships"][1]
        assert rel2["source_concept"] == "ConceptTwo"
        assert rel2["target_concept"] == "ConceptOne"
        assert rel2["relation_type"] == "Extends"
        assert rel2["description"] == "Second extends first"


def test_kg_extension_augment_cli():
    """Test KGExtension augment_cli method."""
    extension = KGExtension()
    parser = MagicMock()
    
    extension.augment_cli(parser)
    
    # Check that the flag was added to the parser
    parser.add_argument.assert_called_once()
    args, kwargs = parser.add_argument.call_args
    assert args[0] == "--khora-kg"
    assert kwargs["dest"] == "khora_kg"
    assert kwargs["action"] == "store_true"


def test_kg_extension_activate_disabled():
    """Test KGExtension activate method when disabled."""
    extension = KGExtension()
    extension.opts = {"khora_kg": False}
    actions = ["action1", "action2"]
    
    result = extension.activate(actions)
    
    # When disabled, the actions list should be returned unchanged
    assert result == actions


@patch("khora_kernel_vnext.extensions.kg.extension.extract_and_generate_kg_files")
def test_kg_extension_activate_enabled(mock_extract):
    """Test KGExtension activate method when enabled."""
    extension = KGExtension()
    extension.opts = {"khora_kg": True}
    
    # Create a mock actions list
    action1 = MagicMock(__name__="action1")
    action2 = MagicMock(__name__="define_structure")
    action3 = MagicMock(__name__="action3")
    actions = [action1, action2, action3]
    
    result = extension.activate(actions)
    
    # Should now have one more action
    assert len(result) == 4
    
    # Extract action should come after define_structure
    assert result[2] == mock_extract


def test_extract_and_generate_kg_files_no_config():
    """Test extract_and_generate_kg_files with no Khora config."""
    struct = {"src": {}, "tests": {}}
    opts = {}
    
    with patch("khora_kernel_vnext.extensions.kg.extension.logger") as mock_logger:
        result_struct, result_opts = extract_and_generate_kg_files(struct, opts)
        
        # Should log a warning about missing config
        mock_logger.warning.assert_called_once()
        
        # Struct and opts should be unchanged
        assert result_struct == struct
        assert result_opts == opts


def test_validate_source_links_valid():
    """Test validating source links when files exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create some files that the source links will reference
        (project_dir / "docs").mkdir()
        (project_dir / "docs" / "file1.md").touch()
        (project_dir / "docs" / "file2.md").touch()
        
        # Create KG entries with source links to the files
        entries = [
            KGEntry("Concept1", "Description", "docs/file1.md", 10),
            KGEntry("Concept2", "Description", "docs/file2.md", 20)
        ]
        
        # Validate the source links
        result = validate_source_links(entries, project_dir)
        
        # All files exist, so validation should pass
        assert result.valid is True
        assert result.error_count == 0
        assert len(result.warnings) == 0


def test_validate_source_links_invalid():
    """Test validating source links when files don't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create only one of the files
        (project_dir / "docs").mkdir()
        (project_dir / "docs" / "file1.md").touch()
        
        # Create KG entries with source links, one valid, one invalid
        entries = [
            KGEntry("Concept1", "Description", "docs/file1.md", 10),  # Valid
            KGEntry("Concept2", "Description", "docs/nonexistent.md", 20)  # Invalid
        ]
        
        # Validate the source links
        with patch("khora_kernel_vnext.extensions.kg.extension.logger") as mock_logger:
            result = validate_source_links(entries, project_dir)
            
            # Should have logged a warning
            assert mock_logger.warning.call_count >= 1
            
            # Validation should fail
            assert result.valid is False
            assert result.error_count == 1
            assert len(result.warnings) == 1
            assert "nonexistent.md" in result.warnings[0]


@patch("khora_kernel_vnext.extensions.kg.extension.scan_markdown_files")
@patch("khora_kernel_vnext.extensions.kg.extension.generate_kg_files")
@patch("khora_kernel_vnext.extensions.kg.extension.validate_source_links")
def test_extract_and_generate_kg_files_with_concepts(mock_validate, mock_generate, mock_scan):
    """Test extract_and_generate_kg_files with found concepts/rules/relationships."""
    struct = {"src": {}, "tests": {}}
    
    # Mock khora_config
    khora_config = MagicMock()
    khora_config.paths.docs_dir = "docs"
    opts = {
        "khora_config": khora_config,
        "project_path": "/tmp/project"
    }
    
    # Mock scan_markdown_files to return some concepts/rules/relationships
    mock_concepts = [KGEntry("TestConcept", "Test", "file.md", 1)]
    mock_rules = [KGEntry("TestRule", "Test", "file.md", 2)]
    mock_relationships = [
        RelationshipEntry("TestConcept", "OtherConcept", "References", "Test references other", "file.md", 3)
    ]
    mock_scan.return_value = (mock_concepts, mock_rules, mock_relationships)
    
    # Mock validate_source_links to return validation results
    valid_result = ValidationResult(valid=True, warnings=[], error_count=0)
    invalid_result = ValidationResult(valid=False, warnings=["Invalid source"], error_count=1)
    another_valid_result = ValidationResult(valid=True, warnings=[], error_count=0)
    mock_validate.side_effect = [valid_result, invalid_result, another_valid_result]
    
    # Mock generate_kg_files
    mock_files = (Path("/tmp/concepts.json"), Path("/tmp/rules.json"), Path("/tmp/relationships.json"))
    mock_generate.return_value = mock_files
    
    result_struct, result_opts = extract_and_generate_kg_files(struct, opts)
    
    # Validate that the validation results were stored in opts
    assert "kg_validation" in result_opts
    assert "concepts" in result_opts["kg_validation"]
    assert "rules" in result_opts["kg_validation"]
    assert "relationships" in result_opts["kg_validation"]
    assert "total_errors" in result_opts["kg_validation"]
    assert "warnings" in result_opts["kg_validation"]
    assert result_opts["kg_validation"]["total_errors"] == 1
    
    # Check that struct was modified to include kg_schema.json
    assert "kg" in result_struct
    assert "kg_schema.json" in result_struct["kg"]
    
    # Check that opts were updated with kg_concepts, kg_rules, and kg_relationships
    assert result_opts["kg_concepts"] == mock_concepts
    assert result_opts["kg_rules"] == mock_rules
    assert result_opts["kg_relationships"] == mock_relationships
    
    # Check that relationship summary was generated
    assert "kg_relationship_summary" in result_opts
    assert result_opts["kg_relationship_summary"]["count"] == 1
    assert result_opts["kg_relationship_summary"]["types"] == ["References"]


def test_precommit_hook_config():
    """Test the precommit_kg_hook function."""
    from khora_kernel_vnext.extensions.kg.extension import precommit_kg_hook
    
    project_dir = "/test/project"
    hook_config = precommit_kg_hook(project_dir)
    
    assert hook_config["id"] == "khora-knowledge-graph"
    assert "entry" in hook_config
    assert hook_config["language"] == "python"
    assert hook_config["files"].endswith("md$")
    assert hook_config["pass_filenames"] is True
