"""
Pipeline - compose transforms from FilterParams.
"""

from typing import Callable

import numpy as np

from .types import FilterParams, merge_with_defaults
from . import core


def build_pipeline(params: FilterParams) -> list[Callable[[np.ndarray], np.ndarray]]:
    """
    Build a list of transform functions from FilterParams.

    Returns a list of pure functions that will be applied in order.
    """
    p = merge_with_defaults(params)

    transforms: list[Callable[[np.ndarray], np.ndarray]] = []

    if p.get("brightness", 0) != 0:
        transforms.append(lambda rgb: core.adjust_brightness(rgb, p["brightness"]))

    if p.get("contrast", 1.0) != 1.0:
        gamma = 1.0 / p["contrast"]
        transforms.append(lambda rgb, g=gamma: core.adjust_contrast(rgb, g))

    if p.get("saturation", 1.0) != 1.0:
        transforms.append(lambda rgb: core.adjust_saturation(rgb, p["saturation"]))

    if p.get("fade", 0) > 0:
        transforms.append(lambda rgb: core.apply_fade(rgb, p["fade"]))

    if p.get("grain", 0) > 0:
        seed = p.get("grain_seed", 42)
        transforms.append(lambda rgb, s=seed: core.apply_grain(rgb, p["grain"], s))

    if p.get("temperature", 0) != 0:
        transforms.append(lambda rgb: core.adjust_temperature(rgb, p["temperature"]))

    if p.get("tint") and p["tint"] != {"r": 0.0, "g": 0.0, "b": 0.0}:
        transforms.append(lambda rgb: core.apply_tint(rgb, p["tint"]))

    if p.get("vignette", 0) > 0:
        transforms.append(lambda rgb: core.apply_vignette(rgb, p["vignette"]))

    if p.get("highlights", 0) != 0:
        transforms.append(lambda rgb: core.adjust_highlights(rgb, p["highlights"]))

    if p.get("shadows", 0) != 0:
        transforms.append(lambda rgb: core.adjust_shadows(rgb, p["shadows"]))

    return transforms


def apply_pipeline(
    rgb: np.ndarray, pipeline: list[Callable[[np.ndarray], np.ndarray]]
) -> np.ndarray:
    """Apply a pipeline of transforms to an RGB array."""
    result = rgb
    for transform in pipeline:
        result = transform(result)
    return result


def transform_array(rgb: np.ndarray, params: FilterParams) -> np.ndarray:
    """Convenience: apply params directly to RGB array."""
    return apply_pipeline(rgb, build_pipeline(params))
