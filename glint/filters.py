"""
Pre-built filter presets.
"""

from .types import FilterParams

FILTERS: dict[str, FilterParams] = {
    "none": {
        "name": "None",
        "description": "Original image (identity transform)",
        "contrast": 1.0,
        "saturation": 1.0,
        "brightness": 0.0,
        "fade": 0.0,
        "grain": 0.0,
        "temperature": 0.0,
        "vignette": 0.0,
        "highlights": 0.0,
        "shadows": 0.0,
    },
    "clarendon": {
        "name": "Clarendon",
        "description": "Bright, high contrast with cool cyan shadows",
        "contrast": 1.25,
        "saturation": 1.15,
        "temperature": -0.12,
        "tint": {"r": -0.05, "g": 0.05, "b": 0.08},
        "highlights": 0.1,
        "shadows": 0.05,
    },
    "valencia": {
        "name": "Valencia",
        "description": "Warm vintage fade with creamy yellow tones",
        "contrast": 0.9,
        "saturation": 0.85,
        "fade": 0.3,
        "temperature": 0.15,
        "tint": {"r": 0.08, "g": 0.05, "b": -0.05},
        "brightness": 0.05,
    },
    "juno": {
        "name": "Juno",
        "description": "Teal shadows and warm highlights",
        "contrast": 1.1,
        "saturation": 1.1,
        "temperature": 0.08,
        "tint": {"r": 0.05, "g": -0.05, "b": -0.08},
        "shadows": 0.1,
        "highlights": 0.05,
    },
    "lark": {
        "name": "Lark",
        "description": "Faded, desaturated, misty look",
        "contrast": 0.9,
        "saturation": 0.75,
        "fade": 0.3,
        "brightness": 0.05,
        "temperature": -0.03,
    },
    "gingham": {
        "name": "Gingham",
        "description": "Light, airy, warm brightness",
        "contrast": 0.95,
        "saturation": 0.85,
        "brightness": 0.08,
        "temperature": 0.06,
        "fade": 0.15,
    },
    "moon": {
        "name": "Moon",
        "description": "High contrast black and white",
        "contrast": 1.4,
        "saturation": 0.0,
        "brightness": -0.05,
    },
    "crema": {
        "name": "Crema",
        "description": "Warm vintage matte",
        "contrast": 0.92,
        "saturation": 0.8,
        "fade": 0.4,
        "temperature": 0.15,
        "brightness": 0.03,
    },
    "ludwig": {
        "name": "Ludwig",
        "description": "Slightly desaturated with warm shadows",
        "contrast": 1.05,
        "saturation": 0.9,
        "fade": 0.15,
        "temperature": 0.05,
        "tint": {"r": 0.03, "g": 0.0, "b": -0.02},
    },
    "tokyo-night": {
        "name": "Tokyo Night",
        "description": "Dark moody city vibes with teal/green tones",
        "contrast": 1.25,
        "saturation": 0.85,
        "brightness": -0.08,
        "temperature": -0.05,
        "tint": {"r": -0.03, "g": 0.1, "b": 0.12},
        "shadows": 0.15,
    },
    "forest-fog": {
        "name": "Forest Fog",
        "description": "Dark green moody forest with mist",
        "contrast": 0.88,
        "saturation": 0.7,
        "fade": 0.25,
        "temperature": -0.05,
        "tint": {"r": -0.08, "g": 0.12, "b": -0.03},
        "shadows": 0.1,
        "vignette": 0.2,
    },
    "cinematic": {
        "name": "Cinematic",
        "description": "Teal and orange Hollywood look",
        "contrast": 1.2,
        "saturation": 1.05,
        "temperature": -0.02,
        "tint": {"r": 0.05, "g": -0.03, "b": -0.08},
        "shadows": 0.08,
        "highlights": 0.05,
        "vignette": 0.15,
    },
    "noir": {
        "name": "Noir",
        "description": "Dramatic high contrast black and white",
        "contrast": 1.5,
        "saturation": 0.0,
        "brightness": -0.05,
        "vignette": 0.3,
    },
    "glint-raw": {
        "name": "Glint Raw",
        "description": "High contrast, low highlights, boosted shadows with heavy grain and fade.",
        "contrast": 1.35,
        "brightness": -0.08,
        "fade": 0.25,
        "grain": 0.3,
        "highlights": -0.15,
        "shadows": 0.15,
        "temperature": 0.02,
    },
}


def list_filters() -> list[tuple[str, str]]:
    """Return list of (name, description) tuples."""
    # Ensure 'none' is first
    items = list(FILTERS.items())
    return [(k, v.get("description", "")) for k, v in items]


def get_filter(name: str) -> FilterParams | None:
    """Get filter by name, returns None if not found."""
    return FILTERS.get(name.lower())
