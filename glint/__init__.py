"""
glint - Functional image filter pipeline with LLM support.

Usage:
    glint list                          # List available filters
    glint apply clarendon input.jpg    # Apply filter
    glint generate "moody forest"     # Generate from LLM
    glint export clarendon             # Export to .cube
"""

from .types import FilterParams, DEFAULTS, merge_with_defaults
from . import core
from .filters import FILTERS, get_filter, list_filters
from .pipeline import build_pipeline, apply_pipeline, transform_array
from .apply import (
    apply_to_image,
    apply_to_path,
    load_image,
    image_to_array,
    array_to_image,
)
from .lut import save_cube, generate_cube
from .core import apply_lut_3d
from . import llm
from .blend import blend_filters, blend_images

__version__ = "0.1.0"

__all__ = [
    "FilterParams",
    "DEFAULTS",
    "merge_with_defaults",
    "core",
    "FILTERS",
    "get_filter",
    "list_filters",
    "build_pipeline",
    "apply_pipeline",
    "transform_array",
    "apply_to_image",
    "apply_to_path",
    "load_image",
    "image_to_array",
    "array_to_image",
    "save_cube",
    "generate_cube",
    "apply_lut_3d",
    "llm",
    "blend_filters",
    "blend_images",
]
