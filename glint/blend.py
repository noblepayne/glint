"""
Blend - compose multiple filters together.
"""

import numpy as np

from .types import FilterParams
from .pipeline import build_pipeline, apply_pipeline
from .apply import image_to_array, array_to_image
from PIL import Image


def blend_filters(
    filters: list[FilterParams],
    weights: list[float] | None = None,
) -> FilterParams:
    """
    Blend multiple filters into a single FilterParams.

    Interpolates numeric parameters. For tint, averages the offsets.
    """
    if not filters:
        raise ValueError("At least one filter required")

    if weights is None:
        weights = [1.0 / len(filters)] * len(filters)

    if len(filters) != len(weights):
        raise ValueError("filters and weights must have same length")

    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    result: FilterParams = {}

    numeric_keys = {
        "contrast",
        "brightness",
        "saturation",
        "fade",
        "grain",
        "temperature",
        "vignette",
        "highlights",
        "shadows",
    }

    for key in numeric_keys:
        values = [
            f.get(
                key,
                (
                    0
                    if key in {"fade", "grain", "vignette"}
                    else (1 if key in {"contrast", "saturation"} else 0)
                ),
            )
            for f in filters
        ]
        result[key] = sum(v * w for v, w in zip(values, weights))

    tint_r = sum(f.get("tint", {}).get("r", 0) * w for f, w in zip(filters, weights))
    tint_g = sum(f.get("tint", {}).get("g", 0) * w for f, w in zip(filters, weights))
    tint_b = sum(f.get("tint", {}).get("b", 0) * w for f, w in zip(filters, weights))
    result["tint"] = {"r": tint_r, "g": tint_g, "b": tint_b}

    return result


def blend_images(
    img: Image.Image,
    filters: list[FilterParams],
    weights: list[float] | None = None,
) -> Image.Image:
    """
    Apply multiple filters and blend the results.

    Useful for combining effects from different presets.
    """
    arr = image_to_array(img)

    blended_arr = np.zeros_like(arr)

    if weights is None:
        weights = [1.0 / len(filters)] * len(filters)

    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    for f, w in zip(filters, weights):
        pipeline = build_pipeline(f)
        transformed = apply_pipeline(arr, pipeline)
        blended_arr += transformed * w

    return array_to_image(blended_arr)
