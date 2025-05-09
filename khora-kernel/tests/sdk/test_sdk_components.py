"""
Tests for the Khora Kernel SDK components.
"""

import argparse
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from khora_kernel.sdk.extension import (
    KhoraExtension, 
    create_extension_action, 
    KhoraComponentProvider,
    KhoraAction
)
from khora_kernel.sdk.context import (
    ContributedComponent,
    add_component_to_opts,
    get_component_from_opts,
    merge_component_infos
)
from khora_kernel.sdk.config import (
    KhoraConfigAccessor,
    get_config_accessor
)
from khora_kernel.sdk.templates import (
    TemplateManager,
    get_extension_template
)
from khora_kernel.sdk.utils import (
    ensure_directory,
    snake_to_camel,
    snake_to_pascal,
    camel_to_snake,
    sanitize_filename,
    get_nested_value
)


class TestKhoraExtensionBase:
    """Test the KhoraExtension base class."""
    
    class TestExtension(KhoraExtension):
        name = "test_extension"
        
        def activate(self, actions):
            return self.register(actions, self.dummy_action)
            
        def dummy_action(self, struct, opts):
            return struct, opts
    
    def test_extension_initialization(self):
        """Test that the extension can be initialized."""
        ext = self.TestExtension()
        assert ext.name == "test_extension"
        assert ext.flag == "--test-extension"
        assert ext.persist is True
        
    def test_extension_augment_cli(self):
        """Test the augment_cli method."""
        ext = self.TestExtension()
        parser = MagicMock(spec=argparse.ArgumentParser)
        
        result = ext.augment_cli(parser)
        
        parser.add_argument.assert_called_once()
        assert result is ext  # Should return self for chaining
        
    def test_extension_requires(self):
        """Test the requires method."""
        ext = self.TestExtension()
        deps = ext.requires()
        
        # By default, all extensions depend on core
        assert "khora_core" in deps
        
    def test_register_action(self):
        """Test registering an action."""
        ext = self.TestExtension()
        
        actions = []
        action = lambda s, o: (s, o)
        
        # Simple registration
        result = ext.register(actions, action)
        assert len(result) == 1
        
        # Register with after
        result = ext.register([], action, after="define_structure")
        assert len(result) == 1
        
        # Register with before
        result = ext.register([], action, before="define_structure")
        assert len(result) == 1
        
        # Register with both (should use before)
        with patch("khora_kernel.sdk.extension.logger") as mock_logger:
            result = ext.register([], action, before="a", after="b")
            assert len(result) == 1
            assert mock_logger.warning.called


class TestCreateExtensionAction:
    """Test the create_extension_action factory function."""
    
    def test_create_named_action(self):
        """Test creating a named action."""
        def dummy_func(s, o):
            return s, o
            
        action = create_extension_action("test_action", dummy_func, "Test description")
        
        # Should have the name set
        assert action.__name__ == "test_action"
        
        # Should wrap the function but still work
        struct = {"test": "value"}
        opts = {"option": "value"}
        result_struct, result_opts = action(struct, opts)
        assert result_struct == struct
        assert result_opts == opts
        
    def test_action_catches_exceptions(self):
        """Test that the action catches exceptions."""
        def failing_func(s, o):
            raise ValueError("Test error")
            
        action = create_extension_action("failing_action", failing_func)
        
        # Should not raise an exception
        with patch("khora_kernel.sdk.extension.logger") as mock_logger:
            struct = {}
            opts = {}
            result_struct, result_opts = action(struct, opts)
            
            # Should log the error
            assert mock_logger.error.called
            # Should return the original struct and opts
            assert result_struct is struct
            assert result_opts is opts


class TestContributedComponent:
    """Test the ContributedComponent class."""
    
    def test_component_initialization(self):
        """Test component initialization."""
        component = ContributedComponent(
            name="test_component",
            component_type="service",
            metadata={"language": "python"},
            subcomponents=[{"name": "sub", "type": "module"}]
        )
        
        assert component.name == "test_component"
        assert component.component_type == "service"
        assert component.metadata == {"language": "python"}
        assert len(component.subcomponents) == 1
        
    def test_to_dict(self):
        """Test converting component to dictionary."""
        component = ContributedComponent(
            name="test_component",
            component_type="service",
            metadata={"language": "python"},
            subcomponents=[{"name": "sub", "type": "module"}]
        )
        
        result = component.to_dict()
        assert result["type"] == "service"
        assert result["language"] == "python"
        assert "subcomponents" in result
        assert len(result["subcomponents"]) == 1


class TestComponentInfoFunctions:
    """Test the component info helper functions."""
    
    def test_add_component_to_opts(self):
        """Test adding component info to opts."""
        opts = {}
        component_info = {"type": "service", "count": 1}
        
        add_component_to_opts(opts, "test_component", component_info)
        
        assert "component_info" in opts
        assert "test_component" in opts["component_info"]
        assert opts["component_info"]["test_component"] == component_info
        
    def test_get_component_from_opts(self):
        """Test getting component info from opts."""
        # When component exists
        opts = {"component_info": {"test_component": {"type": "service"}}}
        result = get_component_from_opts(opts, "test_component")
        assert result == {"type": "service"}
        
        # When component doesn't exist
        result = get_component_from_opts(opts, "nonexistent")
        assert result is None
        
        # When component_info doesn't exist
        opts = {}
        result = get_component_from_opts(opts, "test_component")
        assert result is None
        
    def test_merge_component_infos(self):
        """Test merging component infos."""
        original = {
            "type": "service",
            "count": 1,
            "tags": ["a", "b"],
            "metadata": {
                "version": "1.0",
                "owner": "team1"
            }
        }
        
        addition = {
            "count": 2,
            "tags": ["c"],
            "metadata": {
                "version": "2.0",
                "deployment": "k8s"
            }
        }
        
        result = merge_component_infos(original, addition)
        
        # Scalar values should be replaced
        assert result["count"] == 2
        # Lists should be concatenated
        assert set(result["tags"]) == {"a", "b", "c"}
        # Nested dicts should be recursively merged
        assert result["metadata"]["version"] == "2.0"
        assert result["metadata"]["owner"] == "team1"
        assert result["metadata"]["deployment"] == "k8s"


class TestKhoraConfigAccessor:
    """Test the KhoraConfigAccessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock Khora config
        self.mock_config = MagicMock()
        self.mock_config.features = MagicMock()
        self.mock_config.features.test_feature = True
        self.mock_config.features.disabled_feature = False
        
        self.mock_config.paths = MagicMock()
        self.mock_config.paths.test_path = "test/path"
        
        self.mock_config.plugins_config = MagicMock()
        self.mock_config.plugins_config.test_plugin = {"setting": "value"}
        
        # Create the opts dict
        self.opts = {"khora_config": self.mock_config}
        
        # Create the accessor
        self.accessor = KhoraConfigAccessor(self.opts)
    
    def test_has_config(self):
        """Test the has_config property."""
        # When config exists
        assert self.accessor.has_config is True
        
        # When config doesn't exist
        empty_accessor = KhoraConfigAccessor({})
        assert empty_accessor.has_config is False
        
    def test_is_feature_enabled(self):
        """Test checking if a feature is enabled."""
        # Feature is enabled
        assert self.accessor.is_feature_enabled("test_feature") is True
        
        # Feature is disabled
        assert self.accessor.is_feature_enabled("disabled_feature") is False
        
        # Feature doesn't exist
        assert self.accessor.is_feature_enabled("nonexistent_feature") is False
        
    def test_get_path(self):
        """Test getting a path."""
        # Path exists
        assert self.accessor.get_path("test_path", "default") == "test/path"
        
        # Path doesn't exist, use default
        assert self.accessor.get_path("nonexistent_path", "default") == "default"
        
    def test_get_plugin_config(self):
        """Test getting plugin config."""
        # Plugin exists
        assert self.accessor.get_plugin_config("test_plugin") == {"setting": "value"}
        
        # Plugin doesn't exist
        assert self.accessor.get_plugin_config("nonexistent") is None
        
    def test_get_config_value(self):
        """Test getting a config value by path."""
        # Value exists
        assert self.accessor.get_config_value(["features", "test_feature"]) is True
        
        # Value doesn't exist
        assert self.accessor.get_config_value(["nonexistent", "path"]) is None
        assert self.accessor.get_config_value(["nonexistent", "path"], "default") == "default"
        
    def test_get_config_accessor_factory(self):
        """Test the get_config_accessor factory function."""
        accessor = get_config_accessor(self.opts)
        assert isinstance(accessor, KhoraConfigAccessor)
        assert accessor.opts is self.opts


class TestTemplateManager:
    """Test the TemplateManager class."""
    
    @patch("khora_kernel.sdk.templates.pyscaffold_get_template")
    def test_get_template(self, mock_get_template):
        """Test getting a template."""
        mock_get_template.return_value = "template content"
        
        manager = TemplateManager("test_extension")
        result = manager.get_template("test_template")
        
        assert result == "template content"
        mock_get_template.assert_called_with(
            "test_template", 
            relative_to="khora_kernel.extensions.test_extension.templates"
        )
        
    @patch("khora_kernel.sdk.templates.jinja2")
    def test_render_jinja2_template(self, mock_jinja2):
        """Test rendering a Jinja2 template."""
        mock_template = MagicMock()
        mock_template.render.return_value = "rendered template"
        mock_jinja2.Template.return_value = mock_template
        
        manager = TemplateManager("test_extension")
        result = manager.render_jinja2_template(
            "{{ variable }}", 
            {"variable": "value"}
        )
        
        assert result == "rendered template"
        mock_template.render.assert_called_with(variable="value")
        
    def test_render_pyscaffold_template(self):
        """Test rendering a PyScaffold template."""
        manager = TemplateManager("test_extension")
        result = manager.render_pyscaffold_template(
            "Project: {{ project_name }}, Version: {{ version }}",
            {"project_name": "TestProject", "version": "1.0.0"}
        )
        
        assert result == "Project: TestProject, Version: 1.0.0"


class TestUtilityFunctions:
    """Test the utility functions."""
    
    def test_ensure_directory(self, tmp_path):
        """Test ensuring a directory exists."""
        test_dir = tmp_path / "test_dir"
        
        # Directory doesn't exist yet
        assert not test_dir.exists()
        
        # Ensure it exists
        result = ensure_directory(test_dir)
        
        # Should now exist
        assert test_dir.exists()
        assert test_dir.is_dir()
        assert result == test_dir
        
        # Ensure existing directory (should not raise)
        result = ensure_directory(test_dir)
        assert result == test_dir
        
    def test_string_case_conversions(self):
        """Test string case conversion utilities."""
        # Snake to camel
        assert snake_to_camel("test_case_conversion") == "testCaseConversion"
        assert snake_to_camel("single") == "single"
        
        # Snake to pascal
        assert snake_to_pascal("test_case_conversion") == "TestCaseConversion"
        assert snake_to_pascal("single") == "Single"
        
        # Camel to snake
        assert camel_to_snake("testCaseConversion") == "test_case_conversion"
        assert camel_to_snake("TestCaseConversion") == "test_case_conversion"
        assert camel_to_snake("single") == "single"
        
    def test_sanitize_filename(self):
        """Test sanitizing filenames."""
        assert sanitize_filename("test file.txt") == "test_file.txt"
        assert sanitize_filename("test@file#.txt") == "testfile.txt"
        assert sanitize_filename(".hidden") == "file_.hidden"
        assert sanitize_filename("normal.txt") == "normal.txt"
        
    def test_get_nested_value(self):
        """Test getting nested values from dictionaries."""
        data = {
            "level1": {
                "level2": {
                    "level3": "value"
                },
                "other": 123
            },
            "top": "top_value"
        }
        
        # Existing paths
        assert get_nested_value(data, ["level1", "level2", "level3"]) == "value"
        assert get_nested_value(data, ["level1", "other"]) == 123
        assert get_nested_value(data, ["top"]) == "top_value"
        
        # Non-existent paths
        assert get_nested_value(data, ["nonexistent"]) is None
        assert get_nested_value(data, ["level1", "nonexistent"]) is None
        assert get_nested_value(data, ["level1", "level2", "nonexistent"]) is None
        
        # With default
        assert get_nested_value(data, ["nonexistent"], "default") == "default"
