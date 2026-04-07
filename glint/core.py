"""
Core transform functions - pure functions operating on numpy arrays.

Each function takes an RGB numpy array (shape: H x W x 3, values 0-1)
and returns a transformed array of the same shape.
"""

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageFilter


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


def adjust_vibrance(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Adjust vibrance (smart saturation).

    Increases saturation more for muted pixels than for already-saturated ones.
    amount: -1 to 1 (0 = no change)
    """
    if amount == 0:
        return rgb

    # Calculate current saturation per pixel
    # Simple max(r,g,b) - min(r,g,b) estimate
    mx = np.max(rgb, axis=2, keepdims=True)
    mn = np.min(rgb, axis=2, keepdims=True)
    sat = (mx - mn) / (mx + 1e-6)

    # Weight: lower saturation gets more boost
    weight = 1.0 - sat
    boost = 1.0 + (amount * weight)

    # Apply boost
    gray = np.mean(rgb, axis=2, keepdims=True)
    result = gray + (rgb - gray) * boost
    return np.clip(result, 0, 1)


def apply_clarity(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Apply clarity (local contrast enhancement).

    Uses a large-radius high-pass filter blended via soft light.
    amount: -1 to 1 (0 = no change)
    """
    if amount == 0:
        return rgb

    # Need PIL for fast large-radius blur
    from PIL import Image

    h, w, _ = rgb.shape
    pil_img = Image.fromarray((rgb * 255).astype(np.uint8))

    # Large radius for clarity (approx 5-10% of image size)
    radius = max(h, w) * 0.05
    blurred = pil_img.filter(ImageFilter.GaussianBlur(radius))
    blurred_arr = np.array(blurred).astype(np.float64) / 255.0

    # High pass
    high_pass = rgb - blurred_arr + 0.5

    # Soft Light blend: 2ab + a^2(1-2b) if b < 0.5, else 2a(1-b) + sqrt(a)(2b-1)
    # Simplified version for speed
    def soft_light(a, b):
        return (1 - 2 * b) * a**2 + 2 * b * a

    result = soft_light(rgb, np.clip(high_pass, 0, 1))

    # Blend original and clarity based on amount
    return np.clip(rgb * (1 - abs(amount)) + result * abs(amount), 0, 1)


def apply_texture(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Apply texture (fine-detail enhancement).

    Similar to clarity but with a very small radius.
    amount: -1 to 1 (0 = no change)
    """
    if amount == 0:
        return rgb

    # Small radius (1-3px)
    h, w, _ = rgb.shape
    pil_img = Image.fromarray((rgb * 255).astype(np.uint8))
    blurred = pil_img.filter(ImageFilter.GaussianBlur(2.0))
    blurred_arr = np.array(blurred).astype(np.float64) / 255.0

    # High pass
    high_pass = rgb - blurred_arr + 0.5

    # Overlay blend
    def overlay(a, b):
        return np.where(a < 0.5, 2 * a * b, 1 - 2 * (1 - a) * (1 - b))

    result = overlay(rgb, np.clip(high_pass, 0, 1))

    return np.clip(rgb * (1 - abs(amount)) + result * abs(amount), 0, 1)


def apply_dehaze(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Apply dehaze (atmospheric clarity).

    Simple implementation using black point offset and global contrast.
    amount: -1 to 1 (0 = no change)
    """
    if amount == 0:
        return rgb

    # Positive amount = remove haze (deepen blacks, boost contrast)
    if amount > 0:
        # Lower black point
        result = np.clip(rgb - (amount * 0.1), 0, 1)
        # Boost contrast
        gamma = 1.0 - (amount * 0.2)
        result = np.power(result, gamma)
        # Boost saturation slightly
        gray = np.mean(result, axis=2, keepdims=True)
        result = gray + (result - gray) * (1.0 + amount * 0.2)
    else:
        # Negative amount = add haze (lift blacks, reduce contrast)
        abs_amount = abs(amount)
        result = rgb + (abs_amount * 0.15)
        gamma = 1.0 + (abs_amount * 0.3)
        result = np.power(np.clip(result, 0.001, 1), gamma)

    return np.clip(result, 0, 1)


def apply_sharpen(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Apply sharpening using a 3x3 Laplacian kernel.
    """
    if amount <= 0:
        return rgb

    from PIL import ImageFilter

    pil_img = Image.fromarray((rgb * 255).astype(np.uint8))
    # Apply subtle sharpening pass
    sharpened = pil_img.filter(ImageFilter.SHARPEN)
    if amount > 0.5:
        sharpened = sharpened.filter(ImageFilter.SHARPEN)

    sharpened_arr = np.array(sharpened).astype(np.float64) / 255.0

    # Blend based on amount
    return np.clip(rgb * (1 - amount) + sharpened_arr * amount, 0, 1)


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
