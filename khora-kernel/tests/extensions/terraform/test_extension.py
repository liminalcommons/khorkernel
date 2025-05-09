import os
from pathlib import Path
import pytest
from unittest.mock import patch

from pyscaffold.api import create_project

from khora_kernel_vnext.extensions.terraform.extension import TerraformExtension
from khora_kernel_vnext.extensions.core.manifest import KhoraManifestConfig, KhoraFeaturesConfig


@pytest.fixture
def extension():
    """Return a TerraformExtension instance"""
    return TerraformExtension()


def test_extension_creates_files(extension, tmp_path):
    """Test if the extension creates the correct files in the project"""
    # Create a manifest with Terraform feature enabled
    manifest = KhoraManifestConfig(
        project_name="test-project",
        project_description="Test Project",
        python_version="3.9",
        features=KhoraFeaturesConfig(terraform=True)
    )
    
    # Set up a temporary directory for the test
    tmp_path = Path(str(tmp_path))
    project_path = tmp_path / "test-project"
    
    with patch("khora_kernel_vnext.extensions.core.extension.KhoraManifestConfig") as mock_manifest:
        mock_manifest.return_value = manifest
        # Create a test project with the terraform extension
        opts = create_project(
            project_path=project_path,
            extensions=[extension],
            khora_config=manifest
        )
    
    # Verify that the Terraform IaC files were created
    
    # Test for the existence of main directories
    assert (project_path / "infra").exists()
    assert (project_path / "infra" / "terraform").exists()
    assert (project_path / "infra" / "terraform" / "modules").exists()
    assert (project_path / "infra" / "terraform" / "environments").exists()
    assert (project_path / "infra" / "terraform" / "environments" / "dev").exists()
    assert (project_path / "infra" / "terraform" / "environments" / "prod").exists()
    
    # Test for the existence of root terraform files
    assert (project_path / "infra" / "terraform" / "main.tf").exists()
    assert (project_path / "infra" / "terraform" / "variables.tf").exists()
    assert (project_path / "infra" / "terraform" / "outputs.tf").exists()
    assert (project_path / "infra" / "terraform" / "terraform.tfvars").exists()
    assert (project_path / "infra" / "terraform" / "versions.tf").exists()
    assert (project_path / "infra" / "terraform" / "README.md").exists()
    
    # Test for the existence of environment-specific files
    assert (project_path / "infra" / "terraform" / "environments" / "dev" / "main.tf").exists()
    assert (project_path / "infra" / "terraform" / "environments" / "dev" / "terraform.tfvars").exists()
    assert (project_path / "infra" / "terraform" / "environments" / "prod" / "main.tf").exists()
    assert (project_path / "infra" / "terraform" / "environments" / "prod" / "terraform.tfvars").exists()
    
    # Test for modules gitkeep file
    assert (project_path / "infra" / "terraform" / "modules" / ".gitkeep").exists()
    
    # Check if the workflow file was created (CI feature is disabled by default)
    assert not (project_path / ".github" / "workflows" / "terraform.yml").exists()


def test_extension_with_ci(extension, tmp_path):
    """Test if the extension creates correct files when CI is enabled"""
    # Create a manifest with both Terraform and CI features enabled
    manifest = KhoraManifestConfig(
        project_name="test-project",
        project_description="Test Project",
        python_version="3.9",
        features=KhoraFeaturesConfig(terraform=True, ci_github_actions=True)
    )
    
    # Set up a temporary directory for the test
    tmp_path = Path(str(tmp_path))
    project_path = tmp_path / "test-project"
    
    with patch("khora_kernel_vnext.extensions.core.extension.KhoraManifestConfig") as mock_manifest:
        mock_manifest.return_value = manifest
        # Create a test project with the terraform extension
        opts = create_project(
            project_path=project_path,
            extensions=[extension],
            khora_config=manifest
        )
    
    # Verify that the GitHub Actions workflow file was created
    assert (project_path / ".github" / "workflows" / "terraform.yml").exists()


def test_extension_disabled(extension, tmp_path):
    """Test if the extension doesn't create files when the feature is disabled"""
    # Create a manifest with Terraform feature disabled
    manifest = KhoraManifestConfig(
        project_name="test-project",
        project_description="Test Project",
        python_version="3.9",
        features=KhoraFeaturesConfig(terraform=False)
    )
    
    # Set up a temporary directory for the test
    tmp_path = Path(str(tmp_path))
    project_path = tmp_path / "test-project"
    
    with patch("khora_kernel_vnext.extensions.core.extension.KhoraManifestConfig") as mock_manifest:
        mock_manifest.return_value = manifest
        # Create a test project with the terraform extension
        opts = create_project(
            project_path=project_path,
            extensions=[extension],
            khora_config=manifest
        )
    
    # Verify that the Terraform IaC files were NOT created
    assert not (project_path / "infra" / "terraform").exists()
