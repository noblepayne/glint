"""
Pipeline - compose transforms from FilterParams.
Separates global (color) and spatial (detail) transforms.
"""

from typing import Callable

from numpy.typing import NDArray

from .types import FilterParams, merge_with_defaults
from . import core


def build_color_pipeline(params: FilterParams) -> list[Callable[[NDArray], NDArray]]:
    """
    Build a list of global color transforms from FilterParams.
    These are suitable for baking into a 3D LUT.
    """
    p = merge_with_defaults(params)
    transforms: list[Callable[[NDArray], NDArray]] = []

    # 1. Exposure / Tonal (Global)
    if p.get("brightness", 0) != 0:
        transforms.append(lambda rgb: core.adjust_brightness(rgb, p["brightness"]))

    if p.get("contrast", 1.0) != 1.0:
        gamma = 1.0 / p["contrast"]
        transforms.append(lambda rgb, g=gamma: core.adjust_contrast(rgb, g))

    if p.get("highlights", 0) != 0:
        transforms.append(lambda rgb: core.adjust_highlights(rgb, p["highlights"]))

    if p.get("shadows", 0) != 0:
        transforms.append(lambda rgb: core.adjust_shadows(rgb, p["shadows"]))

    # 2. Atmospheric / Contrast (Global)
    if p.get("dehaze", 0) != 0:
        transforms.append(lambda rgb: core.apply_dehaze(rgb, p["dehaze"]))

    # 3. Color Science (Global)
    if p.get("temperature", 0) != 0:
        transforms.append(lambda rgb: core.adjust_temperature(rgb, p["temperature"]))

    if p.get("tint") and p["tint"] != {"r": 0.0, "g": 0.0, "b": 0.0}:
        transforms.append(lambda rgb: core.apply_tint(rgb, p["tint"]))

    if p.get("saturation", 1.0) != 1.0:
        transforms.append(lambda rgb: core.adjust_saturation(rgb, p["saturation"]))

    if p.get("vibrance", 0) != 0:
        transforms.append(lambda rgb: core.adjust_vibrance(rgb, p["vibrance"]))

    # 4. Fade (Global-ish, but mostly color)
    if p.get("fade", 0) > 0:
        transforms.append(lambda rgb: core.apply_fade(rgb, p["fade"]))

    return transforms


def build_spatial_pipeline(params: FilterParams) -> list[Callable[[NDArray], NDArray]]:
    """
    Build a list of spatial effects from FilterParams.
    These cannot be baked into a 3D LUT as they depend on pixel neighborhood.
    """
    p = merge_with_defaults(params)
    transforms: list[Callable[[NDArray], NDArray]] = []

    # 1. Local Contrast (Spatial)
    if p.get("clarity", 0) != 0:
        transforms.append(lambda rgb: core.apply_clarity(rgb, p["clarity"]))

    # 2. Detail (Spatial)
    if p.get("texture", 0) != 0:
        transforms.append(lambda rgb: core.apply_texture(rgb, p["texture"]))

    if p.get("sharpen", 0) != 0:
        transforms.append(lambda rgb: core.apply_sharpen(rgb, p["sharpen"]))

    # 3. Effects (Spatial)
    if p.get("vignette", 0) > 0:
        transforms.append(lambda rgb: core.apply_vignette(rgb, p["vignette"]))

    if p.get("grain", 0) > 0:
        seed = p.get("grain_seed", 42)
        transforms.append(lambda rgb, s=seed: core.apply_grain(rgb, p["grain"], s))

    return transforms


def build_pipeline(params: FilterParams) -> list[Callable[[NDArray], NDArray]]:
    """Legacy helper for a single list of all transforms."""
    return build_color_pipeline(params) + build_spatial_pipeline(params)


def apply_pipeline(
    rgb: NDArray, pipeline: list[Callable[[NDArray], NDArray]]
) -> NDArray:
    """Apply a list of transform functions in order."""
    result = rgb.copy()
    for transform in pipeline:
        result = transform(result)
    return result


def transform_array(rgb: NDArray, params: FilterParams) -> NDArray:
    """Convenience wrapper: build and apply pipeline in one go."""
    return apply_pipeline(rgb, build_pipeline(params))
