"""
Tests for the diagnostic CLI commands (health, inspect).
"""

import os
import sys
import pytest
from pathlib import Path
from unittest import mock
from click.testing import CliRunner

from khora_kernel_vnext.cli.commands import main_cli, health, inspect


@pytest.fixture
def mock_project_root(tmp_path):
    """Create a basic mock project structure for testing."""
    # Create basic project structure
    pyproject_path = tmp_path / "pyproject.toml"
    
    # Create pyproject.toml with minimal content
    pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"
description = "Test project"

[tool.khora]
features = { docker = true, ci_github_actions = true }
paths = { api_dir = "api" }
"""
    pyproject_path.write_text(pyproject_content)
    
    # Create .khora directory and context.yaml
    khora_dir = tmp_path / ".khora"
    khora_dir.mkdir()
    
    context_yaml = khora_dir / "context.yaml"
    context_yaml.write_text("project_name: test-project")
    
    # Create a simple Python file for syntax checking
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    
    py_file = src_dir / "main.py"
    py_file.write_text("def hello(): return 'Hello, World!'")
    
    # Create docker-compose.yml
    docker_compose = tmp_path / "docker-compose.yml"
    docker_compose.write_text("version: '3'\nservices:\n  api:\n    image: python:3.9")
    
    # Create .github workflows directory
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    
    ci_workflow = workflows_dir / "ci.yml"
    ci_workflow.write_text("name: CI\non: [push]")
    
    # Create KG directory with empty file
    kg_dir = khora_dir / "kg"
    kg_dir.mkdir()
    
    kg_file = kg_dir / "project.json"
    kg_file.write_text("{}")
    
    return tmp_path


def test_health_command_success(mock_project_root):
    """Test that health command exits with success when project is healthy."""
    runner = CliRunner()
    
    with mock.patch(
        'khora_kernel_vnext.cli.commands.find_project_root', 
        return_value=mock_project_root
    ):
        result = runner.invoke(main_cli, ["health"])
        
    assert result.exit_code == 0
    assert "Running Khora health check..." in result.output
    assert "No issues found" in result.output


def test_health_command_verbose(mock_project_root):
    """Test that health command with --verbose shows detailed info."""
    runner = CliRunner()
    
    with mock.patch(
        'khora_kernel_vnext.cli.commands.find_project_root', 
        return_value=mock_project_root
    ):
        result = runner.invoke(main_cli, ["health", "--verbose"])
        
    assert result.exit_code == 0
    assert "Detailed check results" in result.output
    assert "pyproject.toml" in result.output
    assert ".khora/context.yaml" in result.output
    assert "docker-compose.yml" in result.output


def test_health_command_finds_issues(mock_project_root):
    """Test that health command exits with error when issues are found."""
    # Remove khora section from pyproject.toml to create an issue
    pyproject_path = mock_project_root / "pyproject.toml"
    pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"
description = "Test project"
"""
    pyproject_path.write_text(pyproject_content)
    
    runner = CliRunner()
    
    with mock.patch(
        'khora_kernel_vnext.cli.commands.find_project_root', 
        return_value=mock_project_root
    ):
        result = runner.invoke(main_cli, ["health"])
        
    assert result.exit_code == 1
    assert "Issues were found in the project" in result.output
    # With our improved output, the error message should now be visible in non-verbose mode too
    assert "[tool.khora] section not found" in result.output


def test_inspect_command(mock_project_root):
    """Test that inspect command generates a report."""
    runner = CliRunner()
    
    with mock.patch(
        'khora_kernel_vnext.cli.commands.find_project_root', 
        return_value=mock_project_root
    ):
        result = runner.invoke(main_cli, ["inspect"])
        
    assert result.exit_code == 0
    assert "Khora Project Inspection Report" in result.output
    assert f"Project: {mock_project_root.name}" in result.output
    assert "Manifest Analysis" in result.output
    assert "File Structure Analysis" in result.output
    assert "Project Score:" in result.output


def test_inspect_command_output_file(mock_project_root, tmp_path):
    """Test that inspect command can write to an output file."""
    output_file = tmp_path / "report.md"
    runner = CliRunner()
    
    with mock.patch(
        'khora_kernel_vnext.cli.commands.find_project_root', 
        return_value=mock_project_root
    ):
        result = runner.invoke(main_cli, ["inspect", "--out", str(output_file)])
        
    assert result.exit_code == 0
    assert f"Inspection report written to: {output_file}" in result.output
    assert output_file.exists()
    
    # Verify content of the output file
    content = output_file.read_text()
    assert "Khora Project Inspection Report" in content
    assert f"Project: {mock_project_root.name}" in content
