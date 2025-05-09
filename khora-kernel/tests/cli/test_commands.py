"""
Tests for CLI commands in Khora Kernel vNext.
"""

import os
import re
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import tomlkit
from datetime import date

from khora_kernel_vnext.cli.commands import (
    bump_version,
    update_changelog,
    is_version_higher,
    find_project_root,
)


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory with a mock project structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create a minimal pyproject.toml
        pyproject = tomlkit.document()
        pyproject["project"] = {"version": "0.1.0", "name": "test-project"}
        
        with open(project_dir / "pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(pyproject))
        
        # Save the original directory
        original_dir = os.getcwd()
        
        # Change to the temp dir
        os.chdir(project_dir)
        
        yield project_dir
        
        # Change back to the original directory
        os.chdir(original_dir)


def test_is_version_higher():
    """Test version comparison logic."""
    assert is_version_higher("0.1.0", "0.2.0") is True
    assert is_version_higher("0.1.0", "1.0.0") is True
    assert is_version_higher("1.9.0", "2.0.0") is True
    assert is_version_higher("0.1.9", "0.1.10") is True
    
    assert is_version_higher("0.2.0", "0.1.0") is False
    assert is_version_higher("1.0.0", "0.9.9") is False
    assert is_version_higher("0.1.0", "0.1.0") is False


def test_find_project_root(temp_project_dir):
    """Test finding the project root directory."""
    # Create a subdirectory
    subdir = temp_project_dir / "src" / "package"
    subdir.mkdir(parents=True)
    
    # Test from the project root
    # Use resolve() on both paths to normalize symlinks (especially on macOS)
    assert find_project_root().resolve() == temp_project_dir.resolve()
    
    # Test from the subdirectory
    os.chdir(subdir)
    assert find_project_root().resolve() == temp_project_dir.resolve()


def test_bump_version_valid(temp_project_dir):
    """Test bumping the version with valid parameters."""
    from click.testing import CliRunner
    from khora_kernel_vnext.cli.commands import main_cli
    
    runner = CliRunner()
    result = runner.invoke(main_cli, ["bump-version", "--new", "0.2.0"])
    
    # Check command succeeded
    assert result.exit_code == 0
    assert "Updated version from 0.1.0 to 0.2.0 in pyproject.toml" in result.output
    
    # Verify pyproject.toml was updated
    with open(temp_project_dir / "pyproject.toml", "r") as f:
        pyproject = tomlkit.parse(f.read())
        assert pyproject["project"]["version"] == "0.2.0"


def test_bump_version_invalid_format(temp_project_dir):
    """Test bumping the version with invalid format."""
    from click.testing import CliRunner
    from khora_kernel_vnext.cli.commands import main_cli
    
    runner = CliRunner()
    result = runner.invoke(main_cli, ["bump-version", "--new", "not.a.version"])
    
    # Should fail with an error message
    assert result.exit_code != 0
    assert "Error: Version not.a.version does not follow the X.Y.Z format" in result.output


def test_bump_version_not_higher(temp_project_dir):
    """Test bumping the version that is not higher than current."""
    from click.testing import CliRunner
    from khora_kernel_vnext.cli.commands import main_cli
    
    runner = CliRunner()
    result = runner.invoke(main_cli, ["bump-version", "--new", "0.0.9"])
    
    # Should fail with an error message
    assert result.exit_code != 0
    assert "Error: New version 0.0.9 is not higher than current version 0.1.0" in result.output


def test_update_changelog(temp_project_dir):
    """Test updating the changelog."""
    # Test creating a new changelog
    update_changelog(temp_project_dir, "0.1.0", "0.2.0")
    
    # Check that the changelog was created
    changelog_path = temp_project_dir / "CHANGELOG.md"
    assert changelog_path.exists()
    
    # Check contents
    with open(changelog_path, "r") as f:
        content = f.read()
        
    # Should contain the version and today's date
    today = date.today().strftime("%Y-%m-%d")
    assert f"## [0.2.0] - {today}" in content
    assert "### Added" in content
    assert "### Changed" in content
    assert "### Fixed" in content
    
    # Test updating an existing changelog
    update_changelog(temp_project_dir, "0.2.0", "0.3.0")
    
    # Check updated contents
    with open(changelog_path, "r") as f:
        content = f.read()
        
    # Should have both versions
    assert f"## [0.3.0] - {today}" in content
    assert f"## [0.2.0] - {today}" in content


def test_bump_version_with_changelog(temp_project_dir):
    """Test bumping the version with changelog update."""
    from click.testing import CliRunner
    from khora_kernel_vnext.cli.commands import main_cli
    
    runner = CliRunner()
    result = runner.invoke(main_cli, ["bump-version", "--new", "0.2.0", "--changelog"])
    
    # Check command succeeded
    assert result.exit_code == 0
    assert "Updated version from 0.1.0 to 0.2.0 in pyproject.toml" in result.output
    assert "Updated CHANGELOG.md with new version 0.2.0" in result.output
    
    # Verify pyproject.toml was updated
    with open(temp_project_dir / "pyproject.toml", "r") as f:
        pyproject = tomlkit.parse(f.read())
        assert pyproject["project"]["version"] == "0.2.0"
    
    # Verify changelog was created
    changelog_path = temp_project_dir / "CHANGELOG.md"
    assert changelog_path.exists()
