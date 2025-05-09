"""
Utility functions for Khora extensions.

This module provides common utility functions for Khora extensions,
such as file and directory operations, error handling, and other helpers.
"""

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from pyscaffold.actions import ScaffoldOpts
from pyscaffold.exceptions import ShellCommandException

# Create our own implementation since pyscaffold.structure.ensure_exists isn't available
def ensure_exists(path: Path) -> Path:
    """
    Ensure that a given path exists.
    
    Args:
        path: Path to ensure exists
        
    Returns:
        The path object
    """
    path.mkdir(parents=True, exist_ok=True)
    return path

logger = logging.getLogger(__name__)


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        path: Path to the directory
        
    Returns:
        Path object for the directory
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured directory exists: {path_obj}")
    return path_obj


def copy_directory_structure(src: Union[str, Path], dest: Union[str, Path], ignore: Optional[Set[str]] = None) -> None:
    """
    Copy a directory structure from source to destination.
    
    Args:
        src: Source directory
        dest: Destination directory
        ignore: Set of file/directory names to ignore
    """
    src_path = Path(src)
    dest_path = Path(dest)
    
    # Create destination if it doesn't exist
    ensure_directory(dest_path)
    
    # Prepare ignore function for shutil.copytree
    def ignore_func(directory, contents):
        ignored = set()
        if ignore:
            for item in contents:
                if item in ignore:
                    ignored.add(item)
        return ignored
    
    # Walk source directory and copy files/directories
    for item in src_path.glob("**/*"):
        # Get relative path from source root
        rel_path = item.relative_to(src_path)
        target_path = dest_path / rel_path
        
        # Skip ignored items
        if ignore and any(part in ignore for part in rel_path.parts):
            continue
        
        if item.is_dir():
            # Create directory
            target_path.mkdir(exist_ok=True, parents=True)
        else:
            # Copy file
            target_path.parent.mkdir(exist_ok=True, parents=True)
            shutil.copy2(item, target_path)
            
    logger.info(f"Copied directory structure from {src_path} to {dest_path}")


def safe_run_command(cmd: str, cwd: Optional[Union[str, Path]] = None) -> Tuple[str, str]:
    """
    Safely run a shell command and capture its output.
    
    Args:
        cmd: Command to run
        cwd: Working directory for the command
        
    Returns:
        Tuple of (stdout, stderr)
    """
    import subprocess
    
    try:
        logger.debug(f"Running command: {cmd}")
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=cwd
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Command failed with code {process.returncode}: {cmd}")
            logger.error(f"stderr: {stderr}")
            raise ShellCommandException(f"Command failed: {cmd}", stderr)
            
        return stdout, stderr
    except Exception as e:
        logger.error(f"Failed to run command: {cmd}")
        logger.error(f"Error: {str(e)}")
        raise


def snake_to_camel(snake_case: str) -> str:
    """
    Convert a snake_case string to camelCase.
    
    Args:
        snake_case: String in snake_case format
        
    Returns:
        String in camelCase format
    """
    components = snake_case.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def snake_to_pascal(snake_case: str) -> str:
    """
    Convert a snake_case string to PascalCase.
    
    Args:
        snake_case: String in snake_case format
        
    Returns:
        String in PascalCase format
    """
    return ''.join(x.title() for x in snake_case.split('_'))


def camel_to_snake(camel_case: str) -> str:
    """
    Convert a camelCase string to snake_case.
    
    Args:
        camel_case: String in camelCase format
        
    Returns:
        String in snake_case format
    """
    # Replace capital letters with underscore + lowercase letter
    # except for the first letter
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_case)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def store_value_in_opts(opts: ScaffoldOpts, key: str, value: any) -> None:
    """
    Store a value in the PyScaffold options dictionary.
    
    This function avoids overwriting existing values if key exists
    and the value can be merged (dicts, lists).
    
    Args:
        opts: PyScaffold options dictionary
        key: Key to store the value under
        value: Value to store
    """
    if key in opts:
        # Try to merge values if possible
        if isinstance(opts[key], dict) and isinstance(value, dict):
            opts[key].update(value)
            logger.debug(f"Merged {len(value)} items into existing {key} dict in opts")
        elif isinstance(opts[key], list) and isinstance(value, list):
            opts[key].extend(value)
            logger.debug(f"Added {len(value)} items to existing {key} list in opts")
        else:
            # Overwrite
            logger.warning(f"Overwriting existing value for {key} in opts")
            opts[key] = value
    else:
        # Key doesn't exist, just set it
        opts[key] = value
        logger.debug(f"Added {key} to opts")


def get_nested_value(data: Dict, path: List[str], default: any = None) -> any:
    """
    Get a nested value from a dictionary using a path list.
    
    Args:
        data: Dictionary to get value from
        path: List of keys to navigate the dictionary hierarchy
        default: Default value to return if path doesn't exist
        
    Returns:
        The value if found, default otherwise
    """
    current = data
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Args:
        filename: String to sanitize
        
    Returns:
        Sanitized string safe for use in filenames
    """
    # Replace spaces with underscores
    s = filename.replace(' ', '_')
    
    # Remove invalid characters
    s = re.sub(r'[^a-zA-Z0-9_.-]', '', s)
    
    # Ensure it doesn't start with a dot (hidden file)
    if s.startswith('.'):
        s = 'file_' + s
        
    return s
