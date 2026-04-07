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
    vibrance: float
    clarity: float
    texture: float
    dehaze: float
    sharpen: float


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
    "vibrance": 0.0,
    "clarity": 0.0,
    "texture": 0.0,
    "dehaze": 0.0,
    "sharpen": 0.0,
}

MODELS = {
    "gemini-3-flash": "openrouter/google/gemini-3-flash-preview",
    "gemini-2.0-flash": "openrouter/google/gemini-2.0-flash-001",
    "gemma-4": "openrouter/google/gemma-4-31b-it",
    "gpt-4o-mini": "openrouter/openai/gpt-4o-mini",
    "claude-haiku": "openrouter/anthropic/claude-3.5-haiku",
    "gpt-oss": "openrouter/openai/gpt-oss-20b",
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
