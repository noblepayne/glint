"""
Core transform functions - pure functions operating on numpy arrays.

Each function takes an RGB numpy array (shape: H x W x 3, values 0-1)
and returns a transformed array of the same shape.
"""

import numpy as np
from numpy.typing import NDArray


def adjust_contrast(rgb: NDArray[np.float64], gamma: float) -> NDArray[np.float64]:
    """
    Adjust contrast using power curve (gamma).

    gamma < 1: increases contrast (darker darks, brighter brights)
    gamma > 1: decreases contrast (flatter)
    """
    return np.power(np.clip(rgb, 0, 1), gamma)


def adjust_brightness(rgb: NDArray[np.float64], lift: float) -> NDArray[np.float64]:
    """
    Adjust brightness by adding a lift value.

    Positive lift brightens, negative darkens.
    """
    return np.clip(rgb + lift, 0, 1)


def adjust_saturation(rgb: NDArray[np.float64], factor: float) -> NDArray[np.float64]:
    """
    Adjust saturation.

    factor > 1: more saturated
    factor < 1: less saturated (toward gray)
    factor = 0: grayscale
    """
    gray = np.mean(rgb, axis=2, keepdims=True)
    return np.clip(gray + (rgb - gray) * factor, 0, 1)


def apply_fade(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Apply vintage fade effect.

    This simulates the "memory" look - a soft, dreamy quality like a
    faded photograph or a pleasant memory. It's like a subtle translucent
    layer that lifts the blacks and flattens the dynamic range.

    Key elements:
    - Lifts blacks (adds to dark areas)
    - Compresses highlights slightly
    - Soft desaturation
    - Very slight brightness boost in mids
    """
    if amount <= 0:
        return rgb

    # 1. Lift blacks - like adding a subtle white/color layer
    # The less amount, the less we lift
    faded = rgb + (amount * 0.12)

    # 2. Compress highlights - reduces dynamic range, gives that "flat" look
    # Lift the curve at the top
    faded = np.power(np.clip(faded, 0.001, 1), 1 - (amount * 0.15))

    # 3. Soft desaturation - not harsh, just muted
    gray = np.mean(faded, axis=2, keepdims=True)
    faded = gray + (faded - gray) * (1 - amount * 0.35)

    # 4. Final softness - slight blur-like effect via smooth curve
    # This helps the "dreamy" quality
    faded = np.power(np.clip(faded, 0.001, 1), 0.95 + (amount * 0.1))

    return np.clip(faded, 0, 1)


def apply_grain(
    rgb: NDArray[np.float64], amount: float, seed: int | None = None
) -> NDArray[np.float64]:
    """
    Add film grain noise.

    Uses Gaussian noise that scales with amount.
    Seed is used to create a local random generator (pure).
    """
    if amount <= 0:
        return rgb

    rng = np.random.default_rng(seed)
    h, w, c = rgb.shape
    noise = rng.standard_normal((h, w, c)) * (amount * 0.08)

    return np.clip(rgb + noise, 0, 1)


def adjust_temperature(rgb: NDArray[np.float64], shift: float) -> NDArray[np.float64]:
    """
    Adjust color temperature.

    Positive shift: warmer (more yellow/orange)
    Negative shift: cooler (more blue)
    """
    if shift == 0:
        return rgb

    result = rgb.copy()

    if shift > 0:
        result[:, :, 0] = np.clip(result[:, :, 0] + shift * 0.15, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] + shift * 0.05, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] - shift * 0.1, 0, 1)
    else:
        abs_shift = abs(shift)
        result[:, :, 0] = np.clip(result[:, :, 0] - abs_shift * 0.1, 0, 1)
        result[:, :, 1] = np.clip(result[:, :, 1] - abs_shift * 0.02, 0, 1)
        result[:, :, 2] = np.clip(result[:, :, 2] + abs_shift * 0.12, 0, 1)

    return result


def apply_tint(rgb: NDArray[np.float64], tint: dict[str, float]) -> NDArray[np.float64]:
    """
    Apply RGB tint offsets to specific channels.

    tint: {'r': float, 'g': float, 'b': float} with values -0.3 to 0.3
    """
    result = rgb.copy()

    if "r" in tint:
        result[:, :, 0] = np.clip(result[:, :, 0] + tint["r"], 0, 1)
    if "g" in tint:
        result[:, :, 1] = np.clip(result[:, :, 1] + tint["g"], 0, 1)
    if "b" in tint:
        result[:, :, 2] = np.clip(result[:, :, 2] + tint["b"], 0, 1)

    return result


def apply_vignette(rgb: NDArray[np.float64], strength: float) -> NDArray[np.float64]:
    """
    Apply radial vignette (darker edges).

    strength: 0 = no vignette, 1 = strong
    """
    if strength <= 0:
        return rgb

    h, w, _ = rgb.shape
    y, x = np.ogrid[:h, :w]

    cy, cx = h / 2, w / 2
    max_dist = np.sqrt(cy**2 + cx**2)

    dist = np.sqrt((y - cy) ** 2 + (x - cx) ** 2) / max_dist
    vignette = 1 - (dist**2) * strength

    return np.clip(rgb * vignette[:, :, np.newaxis], 0, 1)


def adjust_highlights(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Adjust highlights (bright areas).

    Positive: lift highlights
    Negative: clip/lower highlights
    """
    if amount == 0:
        return rgb

    lum = np.mean(rgb, axis=2, keepdims=True)
    mask = np.clip((lum - 0.5) * 2, 0, 1)

    adjustment = amount * 0.3 * mask
    return np.clip(rgb + adjustment, 0, 1)


def adjust_shadows(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Adjust shadows (dark areas).

    Positive: lift shadows
    Negative: deepen shadows
    """
    if amount == 0:
        return rgb

    lum = np.mean(rgb, axis=2, keepdims=True)
    mask = np.clip((0.5 - lum) * 2, 0, 1)

    adjustment = amount * 0.3 * mask
    return np.clip(rgb + adjustment, 0, 1)


def channel_mix(
    rgb: NDArray[np.float64], matrix: list[list[float]]
) -> NDArray[np.float64]:
    """
    Apply a 3x3 matrix color transformation.

    Useful for color grading (e.g., teal/orange split).
    """
    arr = rgb.reshape(-1, 3)
    mixed = arr @ np.array(matrix)
    return np.clip(mixed.reshape(rgb.shape), 0, 1)


def color_grading(
    rgb: NDArray[np.float64],
    shadows: tuple[float, float, float] = (0, 0, 0),
    midtones: tuple[float, float, float] = (0, 0, 0),
    highlights: tuple[float, float, float] = (0, 0, 0),
) -> NDArray[np.float64]:
    """
    Apply color grading to shadows, midtones, and highlights separately.

    Each parameter is a 3-tuple of RGB offsets.
    """
    lum = np.mean(rgb, axis=2, keepdims=True)

    shadow_mask = np.clip((0.33 - lum) * 3, 0, 1)
    highlight_mask = np.clip((lum - 0.66) * 3, 0, 1)
    midtone_mask = np.clip(1 - shadow_mask - highlight_mask, 0, 1)

    result = rgb.copy()
    result += np.array(shadows) * shadow_mask
    result += np.array(midtones) * midtone_mask
    result += np.array(highlights) * highlight_mask

    return np.clip(result, 0, 1)
