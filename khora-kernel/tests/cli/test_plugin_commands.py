"""Tests for the plugin-related CLI commands."""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from khora_kernel_vnext.cli.commands import main_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_list_plugins_basic(cli_runner):
    """Test basic functionality of the list-plugins command."""
    with patch('khora_kernel_vnext.cli.commands.find_installed_plugins') as mock_find_local:
        # Mock some installed plugins
        mock_find_local.return_value = [
            {
                'name': 'khora-test-extension',
                'version': '0.1.0',
                'description': 'A test extension for Khora',
                'installed': True
            }
        ]
        
        # Run the command
        result = cli_runner.invoke(main_cli, ['list-plugins'])
        
        # Verify results
        assert result.exit_code == 0
        assert 'khora-test-extension' in result.output
        assert '0.1.0' in result.output
        assert 'A test extension for Khora' in result.output
        assert '[installed]' in result.output
        assert 'Found 1 installed plugins' in result.output


def test_list_plugins_pypi(cli_runner):
    """Test list-plugins command with PyPI option."""
    with patch('khora_kernel_vnext.cli.commands.find_installed_plugins') as mock_find_local:
        with patch('khora_kernel_vnext.cli.commands.find_pypi_plugins') as mock_find_pypi:
            # Mock installed and PyPI plugins
            mock_find_local.return_value = []
            mock_find_pypi.return_value = [
                {
                    'name': 'khora-pypi-extension',
                    'version': '0.2.0',
                    'description': 'A PyPI extension for Khora',
                    'installed': False
                }
            ]
            
            # Run the command with PyPI option
            result = cli_runner.invoke(main_cli, ['list-plugins', '--pypi'])
            
            # Verify results
            assert result.exit_code == 0
            assert 'khora-pypi-extension' in result.output
            assert '0.2.0' in result.output
            assert 'A PyPI extension for Khora' in result.output
            assert '[PyPI]' in result.output
            assert 'Found 0 installed plugins' in result.output
            assert 'Found 1 additional plugins on PyPI' in result.output


def test_list_plugins_verbose(cli_runner):
    """Test list-plugins command with verbose option."""
    with patch('khora_kernel_vnext.cli.commands.find_installed_plugins') as mock_find_local:
        # Mock installed plugins with detailed information
        mock_find_local.return_value = [
            {
                'name': 'khora-test-extension',
                'version': '0.1.0',
                'description': 'A test extension for Khora',
                'installed': True,
                'author': 'Test Author',
                'homepage': 'https://github.com/test/khora-test-extension',
                'features': ['feature1', 'feature2']
            }
        ]
        
        # Run the command with verbose option
        result = cli_runner.invoke(main_cli, ['list-plugins', '--verbose'])
        
        # Verify results
        assert result.exit_code == 0
        assert 'khora-test-extension' in result.output
        assert '0.1.0' in result.output
        assert 'A test extension for Khora' in result.output
        assert 'Author: Test Author' in result.output
        assert 'Homepage: https://github.com/test/khora-test-extension' in result.output
        assert 'Features: feature1, feature2' in result.output


def test_list_plugins_no_plugins(cli_runner):
    """Test list-plugins command when no plugins are found."""
    with patch('khora_kernel_vnext.cli.commands.find_installed_plugins') as mock_find_local:
        with patch('khora_kernel_vnext.cli.commands.find_pypi_plugins') as mock_find_pypi:
            # Mock no plugins found
            mock_find_local.return_value = []
            mock_find_pypi.return_value = []
            
            # Run the command
            result = cli_runner.invoke(main_cli, ['list-plugins'])
            
            # Verify results
            assert result.exit_code == 0
            assert 'No Khora plugins found.' in result.output


def test_list_plugins_pypi_error(cli_runner):
    """Test list-plugins command with PyPI error handling."""
    with patch('khora_kernel_vnext.cli.commands.find_installed_plugins') as mock_find_local:
        with patch('khora_kernel_vnext.cli.commands.find_pypi_plugins') as mock_find_pypi:
            # Mock installed plugins and a PyPI error
            mock_find_local.return_value = [
                {
                    'name': 'khora-test-extension',
                    'version': '0.1.0',
                    'description': 'A test extension for Khora',
                    'installed': True
                }
            ]
            mock_find_pypi.side_effect = Exception("Connection error")
            
            # Run the command with PyPI option
            result = cli_runner.invoke(main_cli, ['list-plugins', '--pypi'])
            
            # Verify results
            assert result.exit_code == 0
            assert 'Error searching PyPI: Connection error' in result.output
            assert 'khora-test-extension' in result.output  # Should still show installed plugins
