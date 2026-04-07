"""
Apply transforms to PIL Images.
"""

from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image

from .types import FilterParams
from .pipeline import build_pipeline, apply_pipeline


class ImageLike(Protocol):
    """Protocol for objects that can be converted to PIL Image."""

    def convert(self, mode: str) -> Image.Image: ...


def image_to_array(img: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array normalized to 0-1."""
    arr = np.array(img.convert("RGB"), dtype=np.float64)
    return arr / 255.0


def array_to_image(arr: np.ndarray) -> Image.Image:
    """Convert numpy array back to PIL Image."""
    arr = np.clip(arr * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def apply_to_image(img: Image.Image, params: FilterParams) -> Image.Image:
    """Apply filter params to a PIL Image."""
    arr = image_to_array(img)
    transformed = apply_pipeline(arr, build_pipeline(params))
    return array_to_image(transformed)


def apply_to_path(
    input_path: Path, params: FilterParams, output_path: Path
) -> Image.Image:
    """Load image, apply params, save to output path."""
    img = Image.open(input_path).convert("RGB")
    result = apply_to_image(img, params)
    result.save(output_path)
    return result


def load_image(path: Path) -> Image.Image:
    """Load and return a PIL Image."""
    return Image.open(path).convert("RGB")


def preview_image(img: Image.Image, params: FilterParams) -> Image.Image:
    """Apply params for preview (same as apply_to_image)."""
    return apply_to_image(img, params)
