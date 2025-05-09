import pytest
import json
import tempfile
from pathlib import Path
import yaml
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from pyscaffold.actions import ScaffoldOpts, Structure
from pyscaffold.operations import no_overwrite

from khora_kernel_vnext.extensions.core.extension import CoreExtension
from khora_kernel_vnext.extensions.core.manifest import (
    KhoraManifestConfig,
    KhoraPathsConfig,
    KhoraFeaturesConfig,
    KhoraPortsConfig,
    KhoraPluginsConfig,
    KhoraDockerPluginConfig,
)

# Default version for mocking
MOCK_KERNEL_VERSION = "0.1.0-alpha" # Aligned with actual VERSION file

@pytest.fixture
def core_extension_instance() -> CoreExtension:
    """Returns a CoreExtension instance for testing."""
    # Opts are not strictly needed for direct method call if we pass them,
    # but extension might initialize some things based on opts.
    # For _generate_khora_context_yaml, opts are passed directly.
    return CoreExtension(name="khora_core")

@pytest.fixture
def mock_opts_base(tmp_path: Path) -> ScaffoldOpts:
    """Basic ScaffoldOpts mock."""
    opts = {
        "project_path": tmp_path / "TestProject",
        # other opts can be added if the method under test uses them
    }
    # PyScaffold opts can be a dict or an argparse.Namespace.
    # Let's simulate a dict-like object that also allows attribute access.
    # A simple dict is often enough if the code uses .get() or ['key']
    return opts

@pytest.fixture
def mock_khora_manifest_config() -> KhoraManifestConfig:
    """Returns a mock KhoraManifestConfig instance."""
    return KhoraManifestConfig(
        project_name="TestProject",
        project_description="A test project description.",
        python_version="3.11",
        paths=KhoraPathsConfig(api_dir=Path("api"), docs_dir=Path("docs")),
        features=KhoraFeaturesConfig(fastapi=True, docker=False, ci_github_actions=True),
        ports=KhoraPortsConfig(http=8080),
        plugins_config=KhoraPluginsConfig(
            docker=KhoraDockerPluginConfig(api_service_name="test_api")
        )
    )

class TestCoreExtensionGenerateKGSummary:
    """Tests for the _generate_kg_summary method added for Phase 2."""
    
    def test_generate_kg_summary_no_kg_files(self, core_extension_instance):
        """Test generating KG summary when no KG files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Set opts to empty - no concepts or rules in opts
            core_extension_instance.opts = {}
            
            summary = core_extension_instance._generate_kg_summary(project_path)
            
            # Should return placeholder string when no data is available
            assert summary == "No knowledge graph data available"
    
    def test_generate_kg_summary_from_files(self, core_extension_instance):
        """Test generating KG summary from existing KG files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create kg directory
            kg_dir = project_path / "kg"
            kg_dir.mkdir()
            
            # Create concepts.json
            concepts_file = kg_dir / "concepts.json"
            concepts_data = {
                "version": "0.1.0",
                "generated_at": "2025-05-08T00:00:00Z",
                "concepts": [
                    {
                        "name": "TestConcept",
                        "description": "Test concept description",
                        "source": {"file": "test.md", "line": 1}
                    }
                ]
            }
            concepts_file.write_text(json.dumps(concepts_data))
            
            # Create rules.json 
            rules_file = kg_dir / "rules.json"
            rules_data = {
                "version": "0.1.0",
                "generated_at": "2025-05-08T01:00:00Z", # Later than concepts
                "rules": [
                    {
                        "name": "TestRule",
                        "description": "Test rule description",
                        "source": {"file": "test.md", "line": 2}
                    },
                    {
                        "name": "AnotherRule",
                        "description": "Another rule description",
                        "source": {"file": "test.md", "line": 3}
                    }
                ]
            }
            rules_file.write_text(json.dumps(rules_data))
            
            # Empty opts
            core_extension_instance.opts = {}
            
            summary = core_extension_instance._generate_kg_summary(project_path)
            
            # Check summary content
            assert isinstance(summary, dict)
            assert summary["concept_count"] == 1
            assert summary["rule_count"] == 2
            assert summary["source_dir"] == "kg"
            assert summary["last_updated"] == "2025-05-08T01:00:00Z"  # Should take the later timestamp
            assert summary["concepts_hash"] is not None
            assert summary["rules_hash"] is not None
    
    def test_generate_kg_summary_from_opts(self, core_extension_instance):
        """Test generating KG summary from memory (opts) when files don't exist."""
        from khora_kernel_vnext.extensions.kg.extension import KGEntry
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create mock concepts and rules in opts
            concepts = [
                KGEntry("Concept1", "Description 1", "file1.md", 1),
                KGEntry("Concept2", "Description 2", "file2.md", 2)
            ]
            rules = [
                KGEntry("Rule1", "Rule description 1", "file1.md", 3)
            ]
            
            # Set opts
            core_extension_instance.opts = {
                "kg_concepts": concepts,
                "kg_rules": rules
            }
            
            summary = core_extension_instance._generate_kg_summary(project_path)
            
            # Check summary content
            assert isinstance(summary, dict)
            assert summary["concept_count"] == 2
            assert summary["rule_count"] == 1
            assert summary["concepts_hash"] is not None
            assert summary["rules_hash"] is not None
            assert summary["last_updated"] is not None
    
    def test_generate_kg_summary_error_handling(self, core_extension_instance):
        """Test error handling in KG summary generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create kg directory with invalid files
            kg_dir = project_path / "kg"
            kg_dir.mkdir()
            
            # Create invalid concepts.json
            concepts_file = kg_dir / "concepts.json"
            concepts_file.write_text("This is not valid JSON")
            
            # Empty opts
            core_extension_instance.opts = {}
            
            with patch("khora_kernel_vnext.extensions.core.extension.logger") as mock_logger:
                summary = core_extension_instance._generate_kg_summary(project_path)
                
                # Should log error
                assert mock_logger.error.call_count >= 1
                
                # Should return error message
                assert summary == "Error generating knowledge graph summary"


class TestCoreExtensionGenerateKhoraContextYaml:
    def test_generate_khora_context_yaml_happy_path(
        self,
        core_extension_instance: CoreExtension,
        mock_opts_base: ScaffoldOpts,
        mock_khora_manifest_config: KhoraManifestConfig,
        monkeypatch,
    ):
        # Mock reading of VERSION file
        def mock_read_text(encoding):
            return MOCK_KERNEL_VERSION
        
        mock_version_path = MagicMock(spec=Path)
        mock_version_path.read_text.side_effect = mock_read_text
        
        # Patch the Path object creation for the version file
        # This targets Path inside the extension module
        monkeypatch.setattr(
            "khora_kernel_vnext.extensions.core.extension.Path",
            lambda x: mock_version_path if str(x).endswith("_internal/VERSION") else Path(x)
        )

        mock_opts_base["khora_config"] = mock_khora_manifest_config
        initial_struct: Structure = {} # Start with an empty structure

        # Call the method directly
        final_struct, _ = core_extension_instance._generate_khora_context_yaml(
            initial_struct, mock_opts_base
        )

        assert ".khora" in final_struct
        assert "context.yaml" in final_struct[".khora"]
        
        content_tuple = final_struct[".khora"]["context.yaml"]
        assert isinstance(content_tuple, tuple)
        yaml_content_str = content_tuple[0]
        operation = content_tuple[1]

        assert operation.__name__ == "_no_overwrite" # Check function name

        data = yaml.safe_load(yaml_content_str)

        assert data["kernel_version"] == MOCK_KERNEL_VERSION
        assert data["schema_version"] == "0.1.0"
        assert "generated_at" in data
        # Validate timestamp format (basic check)
        try:
            datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("generated_at is not a valid ISO 8601 timestamp")

        assert data["project"]["name"] == "TestProject" # from opts.project_path.name
        assert data["project"]["description"] == "A test project description."
        assert data["project"]["paths"]["api_dir"] == "api" # Path objects are serialized as strings
        assert data["project"]["paths"]["docs_dir"] == "docs"
        # KG summary should be a string for this test (no KG files available)
        assert data["knowledge_graph_summary"] == "No knowledge graph data available"

    def test_generate_with_missing_khora_config(
        self,
        core_extension_instance: CoreExtension,
        mock_opts_base: ScaffoldOpts,
        monkeypatch,
    ):
        monkeypatch.setattr(
            "khora_kernel_vnext.extensions.core.extension.Path",
             lambda x: MagicMock(read_text=MagicMock(return_value=MOCK_KERNEL_VERSION)) if str(x).endswith("_internal/VERSION") else Path(x)
        )
        mock_opts_base["khora_config"] = None # Simulate manifest parsing failure
        initial_struct: Structure = {}

        final_struct, _ = core_extension_instance._generate_khora_context_yaml(
            initial_struct, mock_opts_base
        )
        
        data = yaml.safe_load(final_struct[".khora"]["context.yaml"][0])
        assert data["project"]["description"] == "N/A (Khora manifest not found or invalid)"
        assert data["project"]["paths"] == {}
        assert data["kernel_version"] == MOCK_KERNEL_VERSION # Still should get kernel version

    def test_generate_with_version_file_read_error(
        self,
        core_extension_instance: CoreExtension,
        mock_opts_base: ScaffoldOpts,
        mock_khora_manifest_config: KhoraManifestConfig,
    ):
        # Mock the specific implementation method that reads the VERSION file
        # instead of trying to intercept Path creation
        with patch("khora_kernel_vnext.extensions.core.extension.Path.read_text") as mock_read_text:
            # Configure the mock to raise an OSError when called
            mock_read_text.side_effect = OSError("Simulated file read error")
            
            mock_opts_base["khora_config"] = mock_khora_manifest_config
            initial_struct: Structure = {}

            # Call the method that should try to read the VERSION file
            final_struct, _ = core_extension_instance._generate_khora_context_yaml(
                initial_struct, mock_opts_base
            )

            # Parse the YAML content
            data = yaml.safe_load(final_struct[".khora"]["context.yaml"][0])
            
            # Check that kernel_version was set to "UNKNOWN" due to the file read error
            assert data["kernel_version"] == "UNKNOWN"
            
            # Verify the mock was called - this shows our mocking is working
            mock_read_text.assert_called_once()
            
        # Verify other data is still intact
        assert data["project"]["name"] == "TestProject"

    def test_generate_with_missing_project_path_in_opts(
        self,
        core_extension_instance: CoreExtension,
        mock_khora_manifest_config: KhoraManifestConfig,
        monkeypatch
    ):
        # No project_path in opts
        opts_no_project_path = {
            "khora_config": mock_khora_manifest_config
        }
        # Ensure Path is mocked for VERSION file to avoid actual file access
        monkeypatch.setattr(
            "khora_kernel_vnext.extensions.core.extension.Path",
             lambda x: MagicMock(read_text=MagicMock(return_value=MOCK_KERNEL_VERSION)) if str(x).endswith("_internal/VERSION") else Path(x)
        )

        initial_struct: Structure = {}
        
        # If project_path is missing, the method should return early without modifying struct
        final_struct, _ = core_extension_instance._generate_khora_context_yaml(
            initial_struct, opts_no_project_path
        )
        
        assert final_struct == initial_struct # No changes expected
        assert ".khora" not in final_struct # File should not be generated

    def test_yaml_serialization_error(
        self,
        core_extension_instance: CoreExtension,
        mock_opts_base: ScaffoldOpts,
        mock_khora_manifest_config: KhoraManifestConfig,
        monkeypatch,
    ):
        monkeypatch.setattr(
            "khora_kernel_vnext.extensions.core.extension.Path",
             lambda x: MagicMock(read_text=MagicMock(return_value=MOCK_KERNEL_VERSION)) if str(x).endswith("_internal/VERSION") else Path(x)
        )
        mock_opts_base["khora_config"] = mock_khora_manifest_config
        initial_struct: Structure = {}

        # Mock yaml.dump to raise an exception
        with patch("khora_kernel_vnext.extensions.core.extension.yaml.dump", side_effect=yaml.YAMLError("Serialization failed")):
            final_struct, _ = core_extension_instance._generate_khora_context_yaml(
                initial_struct, mock_opts_base
            )

        assert ".khora" in final_struct
        assert "context.yaml" in final_struct[".khora"]
        yaml_content_str = final_struct[".khora"]["context.yaml"][0]
        
        assert "# Error generating context.yaml content: Serialization failed" in yaml_content_str
        assert f"# Raw data:" in yaml_content_str # Check if raw data is included in comment
