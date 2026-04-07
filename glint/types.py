from typing import TypedDict

_SENTINEL = object()


class FilterParams(TypedDict, total=False):
    """Schema for filter parameters. All fields optional with sensible defaults."""

    name: str
    contrast: float
    brightness: float
    saturation: float
    fade: float
    grain: float
    grain_seed: int
    temperature: float
    tint: dict[str, float]
    vignette: float
    highlights: float
    shadows: float


DEFAULTS: FilterParams = {
    "contrast": 1.0,
    "brightness": 0.0,
    "saturation": 1.0,
    "fade": 0.0,
    "grain": 0.0,
    "grain_seed": 42,
    "temperature": 0.0,
    "tint": {"r": 0.0, "g": 0.0, "b": 0.0},
    "vignette": 0.0,
    "highlights": 0.0,
    "shadows": 0.0,
}


def merge_with_defaults(params: FilterParams) -> FilterParams:
    """Merge user params with defaults, keeping user values where present.

    Unlike naive merge, properly handles falsy values like 0, 0.0, False.
    """
    result = DEFAULTS.copy()
    for key, value in params.items():
        if (
            isinstance(value, dict)
            and key in DEFAULTS
            and isinstance(DEFAULTS[key], dict)
        ):
            result[key] = {**DEFAULTS[key], **value}
        else:
            result[key] = value
    return result
