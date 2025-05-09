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
    model_validator, # Added for Pydantic V2 style model validation
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
    terraform: bool = False   # Terraform IaC scaffolding
    observability: bool = False  # Observability stack in docker-compose


class KhoraPortsConfig(BaseModel):
    http: PositiveInt = 8000


class KhoraDockerPluginConfig(BaseModel):
    api_service_name: str = "api"


class KhoraPluginsConfig(BaseModel):
    docker: KhoraDockerPluginConfig = Field(default_factory=KhoraDockerPluginConfig)


class KhoraManifestConfig(BaseModel):
    """
    Represents the [tool.khora] section in pyproject.toml.
    """

    project_name: str = Field(
        ..., min_length=1, description="The name of the project."
    )
    project_description: Optional[str] = Field(
        None, description="A short description of the project."
    )
    python_version: str = Field(
        pattern=r"^\d+\.\d+$", description="Python version for the project, e.g., '3.10'."
    )

    paths: KhoraPathsConfig = Field(default_factory=KhoraPathsConfig)
    features: KhoraFeaturesConfig = Field(default_factory=KhoraFeaturesConfig)
    ports: KhoraPortsConfig = Field(default_factory=KhoraPortsConfig)
    plugins_config: KhoraPluginsConfig = Field(default_factory=KhoraPluginsConfig)
    
    # Environment-specific configuration active during this config's creation
    active_environment: Optional[str] = Field(
        None, description="The active environment used when generating this configuration."
    )

    @model_validator(mode='after')
    def validate_api_dir_based_on_fastapi_feature(cls, data: Any) -> Any:
        if isinstance(data, KhoraManifestConfig): # Ensure we operate on the model instance
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
                "loc": ("pyproject.toml",), # General location
                "msg": str(e),
                "input": pyproject_path.read_text() # Include file content for context if possible
            }
            raise KhoraManifestInvalidError([error_detail])

        khora_config_data = data.get("tool", {}).get("khora")
        if khora_config_data is None:
            raise KhoraManifestNotFoundError(
                "[tool.khora] section not found in pyproject.toml"
            )

        try:
            # Handle project_name from [project] section if not in [tool.khora]
            if "project_name" not in khora_config_data and "project" in data and "name" in data["project"]:
                # If not in [tool.khora] but present in [project], use that.
                # This is a common pattern.
                khora_config_data["project_name"] = data["project"]["name"]
            
            # Create a copy of the base config data
            base_config_data = dict(khora_config_data)

            # Apply environment-specific overrides if specified
            if env is not None:
                # Get environment-specific section
                env_section = khora_config_data.get("env", {}).get(env)
                if env_section:
                    # Deep merge environment config into base config
                    merged_config_data = deep_merge_dicts(base_config_data, env_section)
                    # Remove the env section to avoid validation issues
                    if "env" in merged_config_data:
                        del merged_config_data["env"]
                    # Set the active environment
                    merged_config_data["active_environment"] = env
                    return cls(**merged_config_data)
                else:
                    # Environment specified but not found - just use base config
                    base_config_data["active_environment"] = None
            
            # Remove env section from base config to avoid validation issues
            if "env" in base_config_data:
                del base_config_data["env"]
                
            # Return the base configuration (either because no env was specified or env section not found)
            return cls(**base_config_data)
        except ValidationError as e:
            raise KhoraManifestInvalidError(e.errors())
        except TypeError as e: # Catches issues like missing required fields not caught by ValidationError directly
            raise KhoraManifestInvalidError(f"Missing or malformed fields in [tool.khora]: {e}")


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
        config = KhoraManifestConfig.from_project_toml(project_dir=".") # Reading from where dummy is
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
        print(f"\\nAttempting to load faulty manifest (missing api_dir): {faulty_pyproject_path.resolve()}")
        try:
            KhoraManifestConfig.from_project_toml(project_dir=".") # Reading from where faulty is
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

        print(f"\\nAttempting to load faulty manifest (missing python_version): {faulty_pyproject_path_py.resolve()}")
        try:
            KhoraManifestConfig.from_project_toml(project_dir=".") # Reading from where faulty is
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
