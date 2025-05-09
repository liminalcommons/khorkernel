"""
Khora Kernel Core Extension.

This package provides the core functionality for Khora Kernel, including:
- The Khora manifest configuration parser and validator
- Context.yaml generation for AI consumption
- Base extension functionality used across all Khora extensions
"""

from .extension import CoreExtension
from .manifest import (
    KhoraManifestConfig,
    KhoraManifestError,
    KhoraManifestNotFoundError,
    KhoraManifestInvalidError,
    KhoraPathsConfig,
    KhoraFeaturesConfig,
    KhoraPortsConfig,
)

__all__ = [
    'CoreExtension',
    'KhoraManifestConfig',
    'KhoraManifestError',
    'KhoraManifestNotFoundError', 
    'KhoraManifestInvalidError',
    'KhoraPathsConfig',
    'KhoraFeaturesConfig',
    'KhoraPortsConfig',
]
