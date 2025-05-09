"""Khora Documentation Extension.

This extension provides basic documentation scaffolding for projects.
It supports both Sphinx and MkDocs documentation generators.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from pyscaffold.extensions import Extension
from pyscaffold.operations import create
from pyscaffold.structure import merge, ensure, reject
from pyscaffold import actions

from khora_kernel_vnext.sdk.templates import TemplateManager


class DocsExtension(Extension):
    """Extension for adding documentation scaffolding to Khora projects."""
    
    def augment_cli(self, parser):
        """Augments the command-line interface parser.
        
        Args:
            parser: CLI parser
            
        Returns:
            The parser with docs-related options added
        """
        parser.add_argument(
            "--docs-type",
            dest="docs_type",
            choices=["sphinx", "mkdocs"],
            default="sphinx",
            help="Documentation generator to use (default: sphinx)",
        )
        
        return parser
        
    def activate(self, actions: List[Tuple[str, Dict[str, Any]]]) -> List[Tuple[str, Dict[str, Any]]]:
        """Activate extension, register actions and perform modifications.
        
        Args:
            actions: list of actions to perform
            
        Returns:
            Modified list of actions
        """
        # Check if docs feature is enabled in the manifest
        opts = self.options
        if not self._is_docs_enabled(opts):
            # Skip if docs feature is not enabled
            return actions
        
        # Initialize new actions list
        new_actions = []
        
        for action, options in actions:
            # Add the new actions just before the 'write_manifest' action
            if action == "write_manifest":
                new_actions.extend(self._generate_docs_structure(opts))
                
            # Keep the original action
            new_actions.append((action, options))
        
        return new_actions
    
    def _is_docs_enabled(self, opts: Dict[str, Any]) -> bool:
        """Check if the docs feature is enabled in the manifest.
        
        Args:
            opts: PyScaffold options dictionary
            
        Returns:
            True if docs feature is enabled, False otherwise
        """
        khora_features = opts.get("khora_features", {})
        return khora_features.get("documentation", False)
    
    def _get_docs_type(self, opts: Dict[str, Any]) -> str:
        """Get the documentation generator type from options.
        
        Args:
            opts: PyScaffold options dictionary
            
        Returns:
            Documentation generator type: 'sphinx' or 'mkdocs'
        """
        # Get from CLI args if specified, otherwise use default
        return opts.get("docs_type", "sphinx")
    
    def _generate_docs_structure(self, opts: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Generate the documentation structure based on the selected generator.
        
        Args:
            opts: PyScaffold options dictionary
            
        Returns:
            List of actions to create documentation files
        """
        actions = []
        docs_type = self._get_docs_type(opts)
        project_name = opts.get("project", "my-project")
        project_description = opts.get("description", "Project documentation")
        
        # Add docs directory to update dependencies in pyproject.toml
        actions.append(self._update_dependencies_action(docs_type))
        
        if docs_type == "sphinx":
            actions.extend(self._generate_sphinx_structure(opts, project_name, project_description))
        else:  # mkdocs
            actions.extend(self._generate_mkdocs_structure(opts, project_name, project_description))
        
        return actions
    
    def _update_dependencies_action(self, docs_type: str) -> Tuple[str, Dict[str, Any]]:
        """Create an action to update dependencies in pyproject.toml.
        
        Args:
            docs_type: Documentation generator type
            
        Returns:
            Action to update dependencies
        """
        def _updater(content, opts):
            # This function will be called to modify the pyproject.toml content
            if docs_type == "sphinx":
                # Add Sphinx dependencies
                deps_to_add = ["sphinx", "sphinx-rtd-theme", "myst-parser"]
            else:  # mkdocs
                # Add MkDocs dependencies
                deps_to_add = ["mkdocs", "mkdocs-material", "mkdocstrings[python]"]
            
            # Simple approach - this would need to be more robust in a real implementation
            # to handle different formats of pyproject.toml
            new_content = content
            
            # Find the dev dependencies section
            if "[project.optional-dependencies.dev]" in content:
                dev_section_pos = content.find("[project.optional-dependencies.dev]")
                next_section_pos = content.find("[", dev_section_pos + 1)
                if next_section_pos == -1:
                    next_section_pos = len(content)
                
                # Prepare the dependency list to add
                deps_str = ""
                for dep in deps_to_add:
                    if dep not in content:
                        deps_str += f'"{dep}", '
                
                if deps_str:
                    # Insert before the next section
                    new_content = (
                        content[:next_section_pos] +
                        deps_str.strip() + "\n" +
                        content[next_section_pos:]
                    )
            
            return new_content
        
        return "custom_action", {
            "action_type": "modify",
            "target": "pyproject.toml",
            "modification": _updater,
            "description": f"Add {docs_type} dependencies"
        }
    
    def _generate_sphinx_structure(self, opts: Dict[str, Any], project_name: str, project_description: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Generate Sphinx documentation structure.
        
        Args:
            opts: PyScaffold options
            project_name: Project name
            project_description: Project description
            
        Returns:
            List of actions to create Sphinx documentation
        """
        actions = []
        
        # Initialize template manager for docs extension
        template_manager = TemplateManager('docs')

        # conf.py
        conf_py_content = template_manager.get_template('sphinx_conf_py')
        conf_py_content = template_manager.render_pyscaffold_template(
            conf_py_content,
            {
                "project_name": project_name,
                "project_description": project_description,
            }
        )
        actions.append((
            "create",
            {
                "path": "docs/conf.py",
                "content": conf_py_content,
                "force": False
            }
        ))
        
        # index.rst
        index_rst_content = template_manager.get_template('sphinx_index_rst')
        index_rst_content = template_manager.render_pyscaffold_template(
            index_rst_content,
            {
                "project_name": project_name,
                "project_description": project_description,
            }
        )
        actions.append((
            "create",
            {
                "path": "docs/index.rst",
                "content": index_rst_content,
                "force": False
            }
        ))
        
        # Create Makefile for building docs
        makefile_content = template_manager.get_template('sphinx_makefile')
        makefile_content = template_manager.render_pyscaffold_template(
            makefile_content,
            {}
        )
        actions.append((
            "create",
            {
                "path": "docs/Makefile",
                "content": makefile_content,
                "force": False
            }
        ))
        
        # Create _static and _templates directories
        actions.append((
            "ensure",
            {
                "path": "docs/_static"
            }
        ))
        actions.append((
            "ensure",
            {
                "path": "docs/_templates"
            }
        ))
        
        return actions
    
    def _generate_mkdocs_structure(self, opts: Dict[str, Any], project_name: str, project_description: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Generate MkDocs documentation structure.
        
        Args:
            opts: PyScaffold options
            project_name: Project name
            project_description: Project description
            
        Returns:
            List of actions to create MkDocs documentation
        """
        actions = []
        
        # Initialize template manager for docs extension
        template_manager = TemplateManager('docs')
        
        # mkdocs.yml
        mkdocs_yml_content = template_manager.get_template('mkdocs_yml')
        mkdocs_yml_content = template_manager.render_pyscaffold_template(
            mkdocs_yml_content,
            {
                "project_name": project_name,
                "project_description": project_description,
            }
        )
        actions.append((
            "create",
            {
                "path": "mkdocs.yml",
                "content": mkdocs_yml_content,
                "force": False
            }
        ))
        
        # index.md
        index_md_content = template_manager.get_template('mkdocs_index_md')
        index_md_content = template_manager.render_pyscaffold_template(
            index_md_content,
            {
                "project_name": project_name,
                "project_description": project_description,
            }
        )
        actions.append((
            "create",
            {
                "path": "docs/index.md",
                "content": index_md_content,
                "force": False
            }
        ))
        
        # Create additional docs directories
        actions.append((
            "ensure",
            {
                "path": "docs/api"
            }
        ))
        
        # Add API documentation stub
        actions.append((
            "create",
            {
                "path": "docs/api/index.md",
                "content": "# API Documentation\n\nAPI documentation will be generated here.\n",
                "force": False
            }
        ))
        
        return actions
