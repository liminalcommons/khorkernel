import os
from pathlib import Path
import pytest
from unittest.mock import patch

from pyscaffold.api import create_project

from khora_kernel_vnext.extensions.playwright.extension import PlaywrightExtension
from khora_kernel_vnext.extensions.core.manifest import KhoraManifestConfig, KhoraFeaturesConfig


@pytest.fixture
def extension():
    """Return a PlaywrightExtension instance"""
    return PlaywrightExtension()


def test_extension_creates_files(extension, tmp_path):
    """Test if the extension creates the correct files in the project"""
    # Create a manifest with Playwright feature enabled
    manifest = KhoraManifestConfig(
        project_name="test-project",
        project_description="Test Project",
        python_version="3.9",
        features=KhoraFeaturesConfig(playwright=True)
    )
    
    # Set up a temporary directory for the test
    tmp_path = Path(str(tmp_path))
    project_path = tmp_path / "test-project"
    
    with patch("khora_kernel_vnext.extensions.core.extension.KhoraManifestConfig") as mock_manifest:
        mock_manifest.return_value = manifest
        # Create a test project with the playwright extension
        opts = create_project(
            project_path=project_path,
            extensions=[extension],
            khora_config=manifest
        )
    
    # Verify that the Playwright UI testing files were created
    
    # Test for the existence of main directories
    assert (project_path / "tests" / "ui").exists()
    assert (project_path / "tests" / "ui" / "tests").exists()
    
    # Test for the existence of config files
    assert (project_path / "tests" / "ui" / "playwright.config.py").exists()
    assert (project_path / "tests" / "ui" / "conftest.py").exists()
    assert (project_path / "tests" / "ui" / "requirements.txt").exists()
    
    # Test for the existence of the test file
    assert (project_path / "tests" / "ui" / "tests" / "__init__.py").exists()
    assert (project_path / "tests" / "ui" / "tests" / "test_sample.py").exists()
    
    # Check if the workflow file was created (CI feature is disabled by default)
    assert not (project_path / ".github" / "workflows" / "playwright.yml").exists()


def test_extension_with_ci(extension, tmp_path):
    """Test if the extension creates correct files when CI is enabled"""
    # Create a manifest with both Playwright and CI features enabled
    manifest = KhoraManifestConfig(
        project_name="test-project",
        project_description="Test Project",
        python_version="3.9",
        features=KhoraFeaturesConfig(playwright=True, ci_github_actions=True)
    )
    
    # Set up a temporary directory for the test
    tmp_path = Path(str(tmp_path))
    project_path = tmp_path / "test-project"
    
    with patch("khora_kernel_vnext.extensions.core.extension.KhoraManifestConfig") as mock_manifest:
        mock_manifest.return_value = manifest
        # Create a test project with the playwright extension
        opts = create_project(
            project_path=project_path,
            extensions=[extension],
            khora_config=manifest
        )
    
    # Verify that the GitHub Actions workflow file was created
    assert (project_path / ".github" / "workflows" / "playwright.yml").exists()


def test_extension_disabled(extension, tmp_path):
    """Test if the extension doesn't create files when the feature is disabled"""
    # Create a manifest with Playwright feature disabled
    manifest = KhoraManifestConfig(
        project_name="test-project",
        project_description="Test Project",
        python_version="3.9",
        features=KhoraFeaturesConfig(playwright=False)
    )
    
    # Set up a temporary directory for the test
    tmp_path = Path(str(tmp_path))
    project_path = tmp_path / "test-project"
    
    with patch("khora_kernel_vnext.extensions.core.extension.KhoraManifestConfig") as mock_manifest:
        mock_manifest.return_value = manifest
        # Create a test project with the playwright extension
        opts = create_project(
            project_path=project_path,
            extensions=[extension],
            khora_config=manifest
        )
    
    # Verify that the Playwright UI testing files were NOT created
    assert not (project_path / "tests" / "ui").exists()
