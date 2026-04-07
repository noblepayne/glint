"""
Tests for glint types and core transforms.
"""

import numpy as np
from glint.types import merge_with_defaults, DEFAULTS
from glint import core


class TestMergeWithDefaults:
    """Test merge_with_defaults handles falsy values correctly."""

    def test_saturation_zero_preserved(self):
        """saturation=0 should be kept (grayscale), not replaced with default."""
        params = {"saturation": 0.0}
        result = merge_with_defaults(params)
        assert result["saturation"] == 0.0

    def test_brightness_zero_preserved(self):
        """brightness=0 should be kept, not replaced with default."""
        params = {"brightness": 0.0}
        result = merge_with_defaults(params)
        assert result["brightness"] == 0.0

    def test_contrast_one_preserved(self):
        """contrast=1.0 should be kept."""
        params = {"contrast": 1.0}
        result = merge_with_defaults(params)
        assert result["contrast"] == 1.0

    def test_fade_zero_preserved(self):
        """fade=0 should be kept."""
        params = {"fade": 0.0}
        result = merge_with_defaults(params)
        assert result["fade"] == 0.0

    def test_unknown_key_preserved(self):
        """Unknown keys should be passed through."""
        params = {"custom_field": 42}
        result = merge_with_defaults(params)
        assert result.get("custom_field") == 42

    def test_tint_merge(self):
        """Partial tint dict should merge with defaults."""
        params = {"tint": {"r": 0.1}}
        result = merge_with_defaults(params)
        assert result["tint"]["r"] == 0.1
        assert result["tint"]["g"] == 0.0
        assert result["tint"]["b"] == 0.0


class TestGrain:
    """Test grain function is pure and deterministic."""

    def test_different_seeds_different_output(self):
        """Different seeds should produce different noise."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result1 = core.apply_grain(rgb, 0.5, seed=1)
        result2 = core.apply_grain(rgb, 0.5, seed=2)
        assert not np.allclose(result1, result2)

    def test_same_seed_same_output(self):
        """Same seed should produce reproducible results."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result1 = core.apply_grain(rgb, 0.5, seed=42)
        result2 = core.apply_grain(rgb, 0.5, seed=42)
        assert np.allclose(result1, result2)

    def test_no_seed_works(self):
        """Works without seed."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result = core.apply_grain(rgb, 0.5)
        assert result.shape == rgb.shape

    def test_zero_amount_returns_original(self):
        """amount=0 should return input unchanged."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result = core.apply_grain(rgb, 0.0)
        assert np.allclose(result, rgb)

    def test_output_clamped(self):
        """Output should always be in [0,1]."""
        rgb = np.ones((10, 10, 3)) * 0.9
        result = core.apply_grain(rgb, 1.0)
        assert result.min() >= 0.0
        assert result.max() <= 1.0


class TestTransformsOutputBounds:
    """All transforms should output values in [0,1]."""

    def test_contrast_output_bounds(self):
        rgb = np.random.rand(10, 10, 3)
        result = core.adjust_contrast(rgb, 0.5)
        assert result.min() >= 0.0 and result.max() <= 1.0

    def test_brightness_output_bounds(self):
        rgb = np.random.rand(10, 10, 3)
        result = core.adjust_brightness(rgb, 0.5)
        assert result.min() >= 0.0 and result.max() <= 1.0

    def test_saturation_output_bounds(self):
        rgb = np.random.rand(10, 10, 3)
        result = core.adjust_saturation(rgb, 2.0)
        assert result.min() >= 0.0 and result.max() <= 1.0

    def test_fade_output_bounds(self):
        rgb = np.random.rand(10, 10, 3)
        result = core.apply_fade(rgb, 0.5)
        assert result.min() >= 0.0 and result.max() <= 1.0

    def test_temperature_output_bounds(self):
        rgb = np.random.rand(10, 10, 3)
        result = core.adjust_temperature(rgb, 0.5)
        assert result.min() >= 0.0 and result.max() <= 1.0

    def test_vignette_output_bounds(self):
        rgb = np.random.rand(10, 10, 3)
        result = core.apply_vignette(rgb, 0.5)
        assert result.min() >= 0.0 and result.max() <= 1.0

    def test_highlights_output_bounds(self):
        rgb = np.random.rand(10, 10, 3)
        result = core.adjust_highlights(rgb, 0.5)
        assert result.min() >= 0.0 and result.max() <= 1.0

    def test_shadows_output_bounds(self):
        rgb = np.random.rand(10, 10, 3)
        result = core.adjust_shadows(rgb, 0.5)
        assert result.min() >= 0.0 and result.max() <= 1.0


class TestIdentityTransforms:
    """Transforms with identity values should not modify input."""

    def test_contrast_identity(self):
        rgb = np.array([[[0.5, 0.5, 0.5]]])
        result = core.adjust_contrast(rgb, 1.0)
        assert np.allclose(result, rgb)

    def test_brightness_identity(self):
        rgb = np.array([[[0.5, 0.5, 0.5]]])
        result = core.adjust_brightness(rgb, 0.0)
        assert np.allclose(result, rgb)

    def test_saturation_identity(self):
        rgb = np.array([[[0.5, 0.5, 0.5]]])
        result = core.adjust_saturation(rgb, 1.0)
        assert np.allclose(result, rgb)

    def test_temperature_identity(self):
        rgb = np.array([[[0.5, 0.5, 0.5]]])
        result = core.adjust_temperature(rgb, 0.0)
        assert np.allclose(result, rgb)


class TestDefaults:
    """Test DEFAULTS contains expected values."""

    def test_grain_seed_in_defaults(self):
        """grain_seed should be defined in defaults."""
        assert "grain_seed" in DEFAULTS

    def test_grain_seed_default_value(self):
        """grain_seed should have a sensible default."""
        assert DEFAULTS["grain_seed"] == 42
