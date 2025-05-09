import pytest
from pathlib import Path
import tomllib
import tomlkit

from khora_kernel_vnext.extensions.core.manifest import (
    KhoraManifestConfig,
    KhoraManifestNotFoundError,
    KhoraManifestInvalidError,
    KhoraPathsConfig,
    KhoraFeaturesConfig,
    KhoraPortsConfig,
    KhoraPluginsConfig,
    KhoraDockerPluginConfig,
)

# Helper function to create a dummy pyproject.toml
def create_dummy_pyproject(tmp_path: Path, content: str) -> Path:
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(content)
    return pyproject_file

# Minimal valid [project] section for testing
MINIMAL_PROJECT_SECTION = """
[project]
name = "test-project"
version = "0.1.0"
"""

class TestKhoraManifestConfig:
    def test_parse_valid_full_manifest(self, tmp_path: Path):
        toml_content = f"""
{MINIMAL_PROJECT_SECTION}

[tool.khora]
project_name = "MyKhoraProject"
project_description = "A detailed description."
python_version = "3.12"

[tool.khora.paths]
api_dir = "app/api"
docs_dir = "documentation"

[tool.khora.features]
fastapi = true
docker = true
ci_github_actions = true

[tool.khora.ports]
http = 8001

[tool.khora.plugins_config.docker]
api_service_name = "my_api_service"
"""
        create_dummy_pyproject(tmp_path, toml_content)
        config = KhoraManifestConfig.from_project_toml(tmp_path)

        assert config.project_name == "MyKhoraProject"
        assert config.project_description == "A detailed description."
        assert config.python_version == "3.12"
        assert config.paths.api_dir == Path("app/api")
        assert config.paths.docs_dir == Path("documentation")
        assert config.features.fastapi is True
        assert config.features.docker is True
        assert config.features.ci_github_actions is True
        assert config.ports.http == 8001
        assert config.plugins_config.docker.api_service_name == "my_api_service"

    def test_parse_valid_minimal_manifest_with_defaults(self, tmp_path: Path):
        # project_name can be derived from [project].name
        toml_content = """
[project]
name = "MinimalProject"
version = "0.1.0"

[tool.khora]
# project_name = "MinimalProject" # Should be derived
python_version = "3.11"
"""
        create_dummy_pyproject(tmp_path, toml_content)
        config = KhoraManifestConfig.from_project_toml(tmp_path)

        assert config.project_name == "MinimalProject" # Derived
        assert config.project_description is None
        assert config.python_version == "3.11"
        assert config.paths.api_dir is None # Default
        assert config.paths.docs_dir == Path("docs") # Default
        assert config.features.fastapi is False # Default
        assert config.features.docker is False # Default
        assert config.features.ci_github_actions is False # Default
        assert config.ports.http == 8000 # Default
        assert config.plugins_config.docker.api_service_name == "api" # Default

    def test_project_name_explicitly_in_khora_overrides_project_section(self, tmp_path: Path):
        toml_content = """
[project]
name = "GenericProjectName"
version = "0.1.0"

[tool.khora]
project_name = "SpecificKhoraName"
python_version = "3.10"
"""
        create_dummy_pyproject(tmp_path, toml_content)
        config = KhoraManifestConfig.from_project_toml(tmp_path)
        assert config.project_name == "SpecificKhoraName"

    def test_missing_pyproject_toml(self, tmp_path: Path):
        with pytest.raises(KhoraManifestNotFoundError, match="pyproject.toml not found"):
            KhoraManifestConfig.from_project_toml(tmp_path)

    def test_missing_tool_khora_section(self, tmp_path: Path):
        toml_content = MINIMAL_PROJECT_SECTION
        create_dummy_pyproject(tmp_path, toml_content)
        with pytest.raises(KhoraManifestNotFoundError, match="\\[tool.khora\\] section not found"):
            KhoraManifestConfig.from_project_toml(tmp_path)

    def test_malformed_toml_file(self, tmp_path: Path):
        toml_content = "this is not valid toml"
        create_dummy_pyproject(tmp_path, toml_content)
        # Adjust the regex to be more general or match the specific Pydantic/TOML error message part
        with pytest.raises(KhoraManifestInvalidError, match="Expected '=' after a key"):
            KhoraManifestConfig.from_project_toml(tmp_path)

    # --- Test missing mandatory fields ---
    def test_missing_project_name_when_not_in_project_section(self, tmp_path: Path):
        toml_content = """
# [project] section is missing name
[tool.khora]
# project_name is also missing here
python_version = "3.9"
"""
        create_dummy_pyproject(tmp_path, toml_content)
        with pytest.raises(KhoraManifestInvalidError) as excinfo:
            KhoraManifestConfig.from_project_toml(tmp_path)
        # Pydantic v2 error structure
        assert any(err["type"] == "missing" and err["loc"] == ("project_name",) for err in excinfo.value.errors)


    def test_missing_python_version(self, tmp_path: Path):
        toml_content = """
[project]
name = "NoPythonVer"
[tool.khora]
project_name = "NoPythonVer"
# python_version is missing
"""
        create_dummy_pyproject(tmp_path, toml_content)
        with pytest.raises(KhoraManifestInvalidError) as excinfo:
            KhoraManifestConfig.from_project_toml(tmp_path)
        assert any(err["type"] == "missing" and err["loc"] == ("python_version",) for err in excinfo.value.errors)

    # --- Test invalid field types/values ---
    @pytest.mark.parametrize(
        "field, value, expected_loc, expected_type_msg_part",
        [
            ("project_name", 123, ("project_name",), "string_type"),
            ("python_version", "3.x", ("python_version",), "string_pattern_mismatch"),
            ("python_version", "3.12.1", ("python_version",), "string_pattern_mismatch"),
            ("paths", {"api_dir": 123}, ("paths", "api_dir"), "path_type"),
        ],
    )
    def test_invalid_field_types_or_values(self, tmp_path: Path, field, value, expected_loc, expected_type_msg_part):
        """Test validation failures for various invalid field types and values.
        
        This test ensures that the Pydantic models correctly validate each field
        according to its expected type and constraints.
        """
        # Create base valid TOML content using tomlkit for better serialization control
        doc = tomlkit.document()
        
        # Add project section
        project = tomlkit.table()
        project.add("name", "test-project")
        project.add("version", "0.1.0")
        doc.add("project", project)
        
        # Add tool.khora section with valid values
        khora = tomlkit.table()
        khora.add("project_name", "ValidProject")
        khora.add("python_version", "3.10")  # Valid Python version
        
        # Add the specific invalid field based on the test case
        if field == "project_name":
            # Replace with invalid non-string value
            khora.remove("project_name")
            khora.add("project_name", value)  # Integer instead of string
            
        elif field == "python_version":
            # Replace with invalid pattern
            khora.remove("python_version")
            khora.add("python_version", value)  # Invalid version format
            
        elif field == "paths":
            # Add a paths section with invalid value
            paths = tomlkit.table()
            if isinstance(value, dict) and "api_dir" in value:
                # Handle nested dict like {"api_dir": 123}
                paths.add("api_dir", value["api_dir"])  # Integer instead of path string
            khora.add("paths", paths)
        
        # Add the khora section to the document
        doc.add("tool", {"khora": khora})
        
        # Write the TOML content to a file
        toml_content = tomlkit.dumps(doc)
        create_dummy_pyproject(tmp_path, toml_content)
        
        # Verify TOML is parsable before proceeding
        try:
            with open(tmp_path / "pyproject.toml", "rb") as f:
                tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            pytest.fail(f"Generated invalid TOML: {e}")
        
        # This should raise KhoraManifestInvalidError due to validation failures
        with pytest.raises(KhoraManifestInvalidError) as excinfo:
            KhoraManifestConfig.from_project_toml(tmp_path)
        
        # Get the validation errors
        errors = excinfo.value.errors
        assert isinstance(errors, list) and len(errors) > 0, "No validation errors found"
        
        # Check for the specific error we're expecting
        found_error = False
        error_details = []
        
        for error in errors:
            error_details.append(f"{error.get('loc', 'unknown_loc')}: {error.get('type', 'unknown_type')}")
            
            # Handle both exact loc matches and partial matches for nested fields
            loc_match = False
            if error.get("loc") == expected_loc:
                loc_match = True
            elif isinstance(error.get("loc"), tuple) and len(error.get("loc", ())) >= len(expected_loc):
                # Check if expected_loc is a prefix of the actual loc
                if error.get("loc")[0:len(expected_loc)] == expected_loc:
                    loc_match = True
            
            # Check if the type contains the expected message part
            if loc_match and expected_type_msg_part in error.get("type", ""):
                found_error = True
                break
        
        assert found_error, f"Expected error for loc={expected_loc} with type containing '{expected_type_msg_part}', but got errors: {error_details}"


    # --- Test conditional validation ---
    def test_fastapi_true_api_dir_missing(self, tmp_path: Path):
        toml_content = """
[project]
name = "FastApiTest"
[tool.khora]
project_name = "FastApiTest"
python_version = "3.10"
[tool.khora.features]
fastapi = true
# paths.api_dir is missing
"""
        create_dummy_pyproject(tmp_path, toml_content)
        with pytest.raises(KhoraManifestInvalidError) as excinfo:
            KhoraManifestConfig.from_project_toml(tmp_path)
        
        # Pydantic v2 validator error structure has different format than v1
        # Check for any error that mentions both paths.api_dir and features.fastapi
        errors = excinfo.value.errors
        found_validation_error = False
        for err in errors:
            # Check for type being value_error and message containing the key parts
            if (err["type"] == "value_error" and 
                "paths.api_dir" in err["msg"] and 
                "features.fastapi" in err["msg"]):
                found_validation_error = True
                break
        assert found_validation_error, f"Expected validation error for api_dir with fastapi, got: {errors}"

    def test_fastapi_true_api_dir_present(self, tmp_path: Path):
        toml_content = """
[project]
name = "FastApiTest"
[tool.khora]
project_name = "FastApiTest"
python_version = "3.10"
[tool.khora.paths]
api_dir = "src/api"
[tool.khora.features]
fastapi = true
"""
        create_dummy_pyproject(tmp_path, toml_content)
        config = KhoraManifestConfig.from_project_toml(tmp_path) # Should not raise
        assert config.paths.api_dir == Path("src/api")
        assert config.features.fastapi is True

    def test_fastapi_false_api_dir_optional(self, tmp_path: Path):
        toml_content_missing = """
[project]
name = "NoFastApiTest"
[tool.khora]
project_name = "NoFastApiTest"
python_version = "3.10"
[tool.khora.features]
fastapi = false
# paths.api_dir is missing - this is OK
"""
        create_dummy_pyproject(tmp_path, toml_content_missing)
        config_missing = KhoraManifestConfig.from_project_toml(tmp_path)
        assert config_missing.paths.api_dir is None
        assert config_missing.features.fastapi is False

        toml_content_present = """
[project]
name = "NoFastApiTest"
[tool.khora]
project_name = "NoFastApiTest"
python_version = "3.10"
[tool.khora.paths]
api_dir = "src/api" # Present, also OK
[tool.khora.features]
fastapi = false
"""
        create_dummy_pyproject(tmp_path, toml_content_present)
        config_present = KhoraManifestConfig.from_project_toml(tmp_path)
        assert config_present.paths.api_dir == Path("src/api")
        assert config_present.features.fastapi is False
        
    def test_empty_khora_section(self, tmp_path: Path):
        toml_content = """
[project]
name = "EmptyKhora"
[tool.khora]
# Empty section
"""
        create_dummy_pyproject(tmp_path, toml_content)
        with pytest.raises(KhoraManifestInvalidError) as excinfo:
            KhoraManifestConfig.from_project_toml(tmp_path)
        
        # Pydantic v2 validation error structure
        errors = excinfo.value.errors
        # Test may get project_name from [project].name, so only check python_version
        # Make sure we find a "missing" type error with loc=("python_version",)
        python_version_missing = False
        for err in errors:
            if err["type"] == "missing" and err["loc"] == ("python_version",):
                python_version_missing = True
                break
        assert python_version_missing, f"Expected missing python_version error, got: {errors}"
