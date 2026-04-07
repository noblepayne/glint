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
    """
    return np.power(np.clip(rgb, 0, 1), gamma)


def adjust_brightness(rgb: NDArray[np.float64], lift: float) -> NDArray[np.float64]:
    """
    Adjust brightness by adding a lift value.
    """
    return np.clip(rgb + lift, 0, 1)


def adjust_saturation(rgb: NDArray[np.float64], factor: float) -> NDArray[np.float64]:
    """
    Adjust saturation.
    """
    gray = np.mean(rgb, axis=2, keepdims=True)
    return np.clip(gray + (rgb - gray) * factor, 0, 1)


def adjust_vibrance(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Adjust vibrance (smart saturation).
    """
    if amount == 0:
        return rgb

    mx = np.max(rgb, axis=2, keepdims=True)
    mn = np.min(rgb, axis=2, keepdims=True)
    sat = (mx - mn) / (mx + 1e-6)

    weight = 1.0 - sat
    boost = 1.0 + (amount * weight)

    gray = np.mean(rgb, axis=2, keepdims=True)
    result = gray + (rgb - gray) * boost
    return np.clip(result, 0, 1)


def apply_clarity(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Apply clarity (local contrast enhancement).
    """
    if amount == 0:
        return rgb

    h, w, _ = rgb.shape
    pil_img = Image.fromarray((rgb * 255).astype(np.uint8))
    radius = max(h, w) * 0.05

    blurred = pil_img.filter(ImageFilter.GaussianBlur(radius))
    blurred_arr = np.array(blurred).astype(np.float64) / 255.0
    high_pass = rgb - blurred_arr + 0.5

    def soft_light(a, b):
        return np.where(
            b < 0.5,
            a - (1 - 2 * b) * a * (1 - a),
            a + (2 * b - 1) * (np.sqrt(a + 1e-6) - a),
        )

    result = soft_light(rgb, np.clip(high_pass, 0, 1))
    return np.clip(rgb * (1 - abs(amount)) + result * abs(amount), 0, 1)


def apply_texture(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Apply texture (fine-detail enhancement).
    """
    if amount == 0:
        return rgb

    h, w, _ = rgb.shape
    pil_img = Image.fromarray((rgb * 255).astype(np.uint8))
    blurred = pil_img.filter(ImageFilter.GaussianBlur(2.0))
    blurred_arr = np.array(blurred).astype(np.float64) / 255.0
    high_pass = rgb - blurred_arr + 0.5

    def overlay(a, b):
        return np.where(a < 0.5, 2 * a * b, 1 - 2 * (1 - a) * (1 - b))

    result = overlay(rgb, np.clip(high_pass, 0, 1))
    return np.clip(rgb * (1 - abs(amount)) + result * abs(amount), 0, 1)


def apply_dehaze(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Apply dehaze (atmospheric clarity).
    """
    if amount == 0:
        return rgb

    if amount > 0:
        result = np.clip(rgb - (amount * 0.1), 0, 1)
        gamma = 1.0 - (amount * 0.2)
        result = np.power(result, gamma)
        gray = np.mean(result, axis=2, keepdims=True)
        result = gray + (result - gray) * (1.0 + amount * 0.2)
    else:
        abs_amount = abs(amount)
        result = rgb + (abs_amount * 0.15)
        gamma = 1.0 + (abs_amount * 0.3)
        result = np.power(np.clip(result, 0.001, 1), gamma)

    return np.clip(result, 0, 1)


def apply_sharpen(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Apply sharpening using PIL's optimized SHARPEN filter.
    """
    if amount <= 0:
        return rgb

    pil_img = Image.fromarray((rgb * 255).astype(np.uint8))
    sharpened = pil_img.filter(ImageFilter.SHARPEN)
    if amount > 0.5:
        sharpened = sharpened.filter(ImageFilter.SHARPEN)

    sharpened_arr = np.array(sharpened).astype(np.float64) / 255.0
    return np.clip(rgb * (1 - amount) + sharpened_arr * amount, 0, 1)


def apply_lut_3d(
    rgb: NDArray[np.float64], lut: NDArray[np.float64]
) -> NDArray[np.float64]:
    """
    Apply a 3D LUT to an RGB array using vectorized trilinear interpolation.
    lut: array of shape (size^3, 3) or (size, size, size, 3)
    """
    size = int(round(lut.shape[0] ** (1 / 3))) if len(lut.shape) == 2 else lut.shape[0]
    lut_3d = lut.reshape(size, size, size, 3).astype(np.float64)

    # Scale RGB to 0-(size-1)
    coords = rgb * (size - 1.0)

    # Indices for the 8 corners of the cube
    idx_low = np.floor(coords).astype(int)
    idx_high = np.ceil(coords).astype(int)

    # Weights for interpolation
    weight_high = coords - idx_low

    # Clip indices to prevent index out of bounds
    idx_low = np.clip(idx_low, 0, size - 1)
    idx_high = np.clip(idx_high, 0, size - 1)

    # Extract coordinates for readability
    r_l, g_l, b_l = idx_low[:, :, 0], idx_low[:, :, 1], idx_low[:, :, 2]
    r_h, g_h, b_h = idx_high[:, :, 0], idx_high[:, :, 1], idx_high[:, :, 2]

    # Trilinear interpolation
    c000 = lut_3d[r_l, g_l, b_l]
    c100 = lut_3d[r_h, g_l, b_l]
    c010 = lut_3d[r_l, g_h, b_l]
    c001 = lut_3d[r_l, g_l, b_h]
    c110 = lut_3d[r_h, g_h, b_l]
    c101 = lut_3d[r_h, g_l, b_h]
    c011 = lut_3d[r_l, g_h, b_h]
    c111 = lut_3d[r_h, g_h, b_h]

    # Interpolate
    wr = weight_high[:, :, 0:1]
    wg = weight_high[:, :, 1:2]
    wb = weight_high[:, :, 2:3]

    result = (
        c000 * (1 - wr) * (1 - wg) * (1 - wb)
        + c100 * wr * (1 - wg) * (1 - wb)
        + c010 * (1 - wr) * wg * (1 - wb)
        + c001 * (1 - wr) * (1 - wg) * wb
        + c110 * wr * wg * (1 - wb)
        + c101 * wr * (1 - wg) * wb
        + c011 * (1 - wr) * wg * wb
        + c111 * wr * wg * wb
    )

    return np.clip(result, 0, 1)


def apply_fade(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Apply vintage fade effect.
    """
    if amount <= 0:
        return rgb

    faded = rgb + (amount * 0.12)
    faded = np.power(np.clip(faded, 0.001, 1), 1 - (amount * 0.15))
    gray = np.mean(faded, axis=2, keepdims=True)
    faded = gray + (faded - gray) * (1 - amount * 0.35)
    faded = np.power(np.clip(faded, 0.001, 1), 0.95 + (amount * 0.1))

    return np.clip(faded, 0, 1)


def apply_grain(
    rgb: NDArray[np.float64], amount: float, seed: int | None = None
) -> NDArray[np.float64]:
    """
    Add film grain noise.
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
    Apply RGB tint offsets.
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
    Apply radial vignette.
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
    Adjust highlights.
    """
    if amount == 0:
        return rgb

    lum = np.mean(rgb, axis=2, keepdims=True)
    mask = np.clip((lum - 0.5) * 2, 0, 1)
    adjustment = amount * 0.3 * mask
    return np.clip(rgb + adjustment, 0, 1)


def adjust_shadows(rgb: NDArray[np.float64], amount: float) -> NDArray[np.float64]:
    """
    Adjust shadows.
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
    Apply a 3x3 matrix.
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
    Apply color grading.
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
