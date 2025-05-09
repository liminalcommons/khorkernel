"""
Integration test for the bump-version CLI command.
"""
import pytest
import os
import subprocess
import tempfile
from pathlib import Path
import tomlkit
from click.testing import CliRunner

from khora_kernel_vnext.cli.commands import main_cli


@pytest.fixture
def temp_test_project():
    """Create a temporary test project with proper structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create a minimal project structure
        (project_dir / "src").mkdir()
        (project_dir / "tests").mkdir()
        
        # Create a pyproject.toml with version
        pyproject = tomlkit.document()
        pyproject["project"] = {
            "name": "test-project",
            "version": "0.1.0",
            "description": "Test project for bump-version command",
        }
        
        with open(project_dir / "pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(pyproject))
        
        # Save current directory
        original_dir = os.getcwd()
        
        # Change to temp dir for testing
        os.chdir(project_dir)
        
        yield project_dir
        
        # Change back to original directory
        os.chdir(original_dir)


def test_bump_version_command(temp_test_project):
    """Test the bump-version command as a CLI command."""
    runner = CliRunner()
    result = runner.invoke(main_cli, ["bump-version", "--new", "0.2.0"])
    
    # Check the command output
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert "Updated version from 0.1.0 to 0.2.0 in pyproject.toml" in result.output
    
    # Verify the file was actually updated
    with open(temp_test_project / "pyproject.toml", "r") as f:
        pyproject = tomlkit.parse(f.read())
    
    assert pyproject["project"]["version"] == "0.2.0"


def test_bump_version_with_changelog(temp_test_project):
    """Test the bump-version command with changelog update."""
    runner = CliRunner()
    result = runner.invoke(main_cli, ["bump-version", "--new", "0.2.0", "--changelog"])
    
    # Check the command output
    assert result.exit_code == 0, f"Command failed with: {result.output}"
    assert "Updated version from 0.1.0 to 0.2.0 in pyproject.toml" in result.output
    assert "Updated CHANGELOG.md with new version 0.2.0" in result.output
    
    # Verify changelog was created
    changelog_path = temp_test_project / "CHANGELOG.md"
    assert changelog_path.exists()
    
    with open(changelog_path, "r") as f:
        content = f.read()
    
    assert "# Changelog" in content
    assert "## [0.2.0]" in content
    assert "### Added" in content
    assert "### Changed" in content
    assert "### Fixed" in content


def test_bump_version_invalid_format(temp_test_project):
    """Test the bump-version command with invalid version format."""
    runner = CliRunner()
    result = runner.invoke(main_cli, ["bump-version", "--new", "not.a.version"])
    
    # Should fail with an error message
    assert result.exit_code != 0
    assert "Error: Version not.a.version does not follow the X.Y.Z format" in result.output


def test_bump_version_not_higher(temp_test_project):
    """Test the bump-version command with version that's not higher."""
    # First update to 0.2.0
    runner = CliRunner()
    runner.invoke(main_cli, ["bump-version", "--new", "0.2.0"])
    
    # Then try to "update" to 0.1.5 (which is lower)
    result = runner.invoke(main_cli, ["bump-version", "--new", "0.1.5"])
    
    # Should fail with an error message
    assert result.exit_code != 0
    assert "Error: New version 0.1.5 is not higher than current version 0.2.0" in result.output


def test_bump_version_multiple_updates(temp_test_project):
    """Test multiple version updates sequentially."""
    runner = CliRunner()
    
    # First update
    result1 = runner.invoke(main_cli, ["bump-version", "--new", "0.2.0"])
    assert result1.exit_code == 0
    
    # Second update
    result2 = runner.invoke(main_cli, ["bump-version", "--new", "0.3.0"])
    assert result2.exit_code == 0
    
    # Third update
    result3 = runner.invoke(main_cli, ["bump-version", "--new", "1.0.0"])
    assert result3.exit_code == 0
    
    # Verify final version
    with open(temp_test_project / "pyproject.toml", "r") as f:
        pyproject = tomlkit.parse(f.read())
    
    assert pyproject["project"]["version"] == "1.0.0"


def test_bump_version_with_existing_changelog(temp_test_project):
    """Test the bump-version command with an existing changelog."""
    # Create a changelog first
    changelog_content = """# Changelog

## [0.1.0] - 2025-05-01

### Added
- Initial release

"""
    with open(temp_test_project / "CHANGELOG.md", "w") as f:
        f.write(changelog_content)
    
    # Run the bump version command
    runner = CliRunner()
    result = runner.invoke(main_cli, ["bump-version", "--new", "0.2.0", "--changelog"])
    
    # Check the command succeeded
    assert result.exit_code == 0
    
    # Check the changelog was updated correctly
    with open(temp_test_project / "CHANGELOG.md", "r") as f:
        updated_content = f.read()
    
    assert "## [0.2.0]" in updated_content
    assert "## [0.1.0]" in updated_content 
    assert updated_content.find("## [0.2.0]") < updated_content.find("## [0.1.0]")
