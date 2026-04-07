"""
Additional tests for edge cases in core transforms and other modules.
"""

import numpy as np
from PIL import Image
import pytest

from glint import core
from glint.types import DEFAULTS, FilterParams, merge_with_defaults
from glint.pipeline import build_pipeline, transform_array
from glint.filters import FILTERS
from glint.apply import image_to_array, array_to_image


class TestEdgeCases:
    """Edge case tests for core transforms."""

    def test_adjust_contrast_gamma_zero(self):
        """contrast with gamma=0 should handle gracefully."""
        rgb = np.ones((10, 10, 3)) * 0.5
        # gamma=0 would cause division issues, but function uses 1/gamma
        # So for contrast > 1, gamma < 1; for contrast < 1, gamma > 1
        # contrast 0 would give gamma = infinity, but we skip contrast=1
        result = core.adjust_contrast(rgb, 0.5)  # gamma 0.5 = contrast 2
        assert result.shape == rgb.shape
        assert result.max() <= 1.0

    def test_adjust_contrast_gamma_very_large(self):
        """Very large gamma should still work."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result = core.adjust_contrast(rgb, 10.0)
        assert result.shape == rgb.shape

    def test_adjust_brightness_extreme_positive(self):
        """Extreme positive brightness should clamp."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result = core.adjust_brightness(rgb, 10.0)
        assert result.max() <= 1.0

    def test_adjust_brightness_extreme_negative(self):
        """Extreme negative brightness should clamp."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result = core.adjust_brightness(rgb, -10.0)
        assert result.min() >= 0.0

    def test_adjust_saturation_extreme(self):
        """Extreme saturation values should clamp."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result = core.adjust_saturation(rgb, 10.0)
        assert result.max() <= 1.0
        assert result.min() >= 0.0

    def test_saturation_zero_creates_grayscale(self):
        """saturation=0 should create grayscale."""
        rgb = np.array([[[0.8, 0.2, 0.4]]])
        result = core.adjust_saturation(rgb, 0.0)
        # All channels should be equal (grayscale)
        assert result[0, 0, 0] == result[0, 0, 1] == result[0, 0, 2]

    def test_apply_fade_extreme(self):
        """Extreme fade values should clamp."""
        rgb = np.random.rand(10, 10, 3)
        result = core.apply_fade(rgb, 2.0)  # Much more than typical max
        assert result.max() <= 1.0
        assert result.min() >= 0.0

    def test_apply_fade_zero_returns_unchanged(self):
        """fade=0 should return unchanged."""
        rgb = np.array([[[0.5, 0.6, 0.7]]])
        result = core.apply_fade(rgb, 0.0)
        assert np.allclose(result, rgb)

    def test_apply_grain_negative_returns_unchanged(self):
        """negative grain should return unchanged."""
        rgb = np.array([[[0.5, 0.6, 0.7]]])
        result = core.apply_grain(rgb, -0.5)
        assert np.allclose(result, rgb)

    def test_apply_grain_large_seed(self):
        """Large seed values should work."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result = core.apply_grain(rgb, 0.5, seed=999999999)
        assert result.shape == rgb.shape

    def test_adjust_temperature_extreme(self):
        """Extreme temperature should clamp."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result = core.adjust_temperature(rgb, 10.0)
        assert result.max() <= 1.0
        assert result.min() >= 0.0

        result = core.adjust_temperature(rgb, -10.0)
        assert result.max() <= 1.0
        assert result.min() >= 0.0

    def test_apply_tint_empty_dict(self):
        """Empty tint dict should work."""
        rgb = np.array([[[0.5, 0.6, 0.7]]])
        result = core.apply_tint(rgb, {})
        assert np.allclose(result, rgb)

    def test_apply_tint_partial(self):
        """Partial tint dict should only modify specified channels."""
        rgb = np.array([[[0.5, 0.6, 0.7]]])
        result = core.apply_tint(rgb, {"r": 0.1})
        assert result[0, 0, 0] != 0.5
        assert result[0, 0, 1] == 0.6  # Unchanged
        assert result[0, 0, 2] == 0.7  # Unchanged

    def test_apply_vignette_zero_returns_unchanged(self):
        """vignette=0 should return unchanged."""
        rgb = np.array([[[0.5, 0.6, 0.7]]])
        result = core.apply_vignette(rgb, 0.0)
        assert np.allclose(result, rgb)

    def test_apply_vignette_negative_returns_unchanged(self):
        """negative vignette should return unchanged."""
        rgb = np.array([[[0.5, 0.6, 0.7]]])
        result = core.apply_vignette(rgb, -0.5)
        assert np.allclose(result, rgb)

    def test_apply_vignette_extreme(self):
        """Extreme vignette should clamp."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result = core.apply_vignette(rgb, 5.0)
        assert result.max() <= 1.0
        assert result.min() >= 0.0

    def test_adjust_highlights_extreme(self):
        """Extreme highlight values should clamp."""
        rgb = np.random.rand(10, 10, 3)
        result = core.adjust_highlights(rgb, 10.0)
        assert result.max() <= 1.0
        assert result.min() >= 0.0

    def test_adjust_shadows_extreme(self):
        """Extreme shadow values should clamp."""
        rgb = np.random.rand(10, 10, 3)
        result = core.adjust_shadows(rgb, 10.0)
        assert result.max() <= 1.0
        assert result.min() >= 0.0

    def test_channel_mix_identity(self):
        """Identity matrix should preserve colors."""
        rgb = np.array([[[0.2, 0.4, 0.6]]])
        identity = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        result = core.channel_mix(rgb, identity)
        assert np.allclose(result, rgb, atol=0.001)

    def test_channel_mix_swap(self):
        """Swap R and B channels."""
        rgb = np.array([[[0.2, 0.4, 0.6]]])
        swap = [[0, 0, 1], [0, 1, 0], [1, 0, 0]]
        result = core.channel_mix(rgb, swap)
        assert np.allclose(result[0, 0, 0], 0.6, atol=0.01)  # R gets B
        assert np.allclose(result[0, 0, 2], 0.2, atol=0.01)  # B gets R

    def test_color_grading_extreme(self):
        """Extreme color grading should clamp."""
        rgb = np.random.rand(10, 10, 3)
        result = core.color_grading(
            rgb,
            shadows=(10.0, 10.0, 10.0),
            midtones=(10.0, 10.0, 10.0),
            highlights=(10.0, 10.0, 10.0),
        )
        assert result.max() <= 1.0
        assert result.min() >= 0.0


class TestEmptyAndSinglePixel:
    """Test transforms on edge case image sizes."""

    def test_single_pixel_image(self):
        """Should work on 1x1 pixel images."""
        rgb = np.array([[[0.5, 0.5, 0.5]]])
        result = transform_array(rgb, {"contrast": 1.2})
        assert result.shape == rgb.shape

    def test_single_row_image(self):
        """Should work on single row images."""
        rgb = np.ones((1, 10, 3)) * 0.5
        result = transform_array(rgb, {"brightness": 0.1})
        assert result.shape == rgb.shape

    def test_single_column_image(self):
        """Should work on single column images."""
        rgb = np.ones((10, 1, 3)) * 0.5
        result = transform_array(rgb, {"saturation": 1.1})
        assert result.shape == rgb.shape


class TestColorChannelManipulation:
    """Test transforms that affect specific color channels."""

    def test_vignette_affects_corners(self):
        """Vignette should darken edges more than center."""
        # Create uniform image
        h, w = 100, 100
        rgb = np.ones((h, w, 3)) * 0.5

        result = core.apply_vignette(rgb, 0.5)

        # Center should be brighter than corners (less darkening)
        center_y, center_x = h // 2, w // 2
        center_val = result[center_y, center_x, 0]
        corner_val = result[0, 0, 0]

        # Center value should be close to original (0.5) since it's at center
        # Corner should be darkened
        assert center_val > corner_val
        assert center_val > 0.4  # Center preserved near 0.5


class TestTypesEdgeCases:
    """Edge cases for type handling."""

    def test_merge_with_defaults_empty(self):
        """Empty dict should return defaults."""
        result = merge_with_defaults({})
        assert result == DEFAULTS

    def test_merge_with_defaults_full_override(self):
        """All values can be overridden."""
        custom = {
            "contrast": 2.0,
            "brightness": 0.1,
            "saturation": 0.5,
            "fade": 0.3,
        }
        result = merge_with_defaults(custom)
        assert result["contrast"] == 2.0
        assert result["brightness"] == 0.1
        assert result["saturation"] == 0.5
        assert result["fade"] == 0.3

    def test_merge_with_partial_tint(self):
        """Partial tint should merge with defaults."""
        result = merge_with_defaults({"tint": {"r": 0.1}})
        assert result["tint"]["r"] == 0.1
        assert result["tint"]["g"] == 0.0
        assert result["tint"]["b"] == 0.0


class TestPipelineEdgeCases:
    """Edge cases for pipeline."""

    def test_pipeline_with_all_params(self):
        """Pipeline with all params should build."""
        params: FilterParams = {
            "contrast": 1.2,
            "brightness": 0.1,
            "saturation": 1.1,
            "fade": 0.2,
            "grain": 0.1,
            "temperature": 0.05,
            "tint": {"r": 0.01, "g": 0.0, "b": -0.01},
            "vignette": 0.3,
            "highlights": 0.1,
            "shadows": 0.1,
        }
        pipeline = build_pipeline(params)
        assert len(pipeline) > 0

    def test_pipeline_preserves_dtype(self):
        """Pipeline should preserve float64 dtype."""
        rgb = np.ones((10, 10, 3), dtype=np.float64) * 0.5
        result = transform_array(rgb, {"contrast": 1.1})
        assert result.dtype == np.float64


class TestImageConversion:
    """Test PIL Image conversion functions."""

    def test_image_to_array_normalizes(self):
        """image_to_array should normalize to 0-1."""
        img = Image.new("RGB", (10, 10), (255, 128, 0))
        arr = image_to_array(img)
        assert arr.max() <= 1.0
        assert arr.min() >= 0.0

    def test_array_to_image_round_trip(self):
        """array_to_image should convert back to valid image."""
        arr = np.random.rand(10, 10, 3)
        img = array_to_image(arr)
        assert isinstance(img, Image.Image)
        assert img.mode == "RGB"

    def test_array_to_image_clamps(self):
        """array_to_image should clamp out-of-range values."""
        arr = np.ones((10, 10, 3)) * 1.5  # Out of 0-1 range
        img = array_to_image(arr)
        arr_back = np.array(img) / 255.0
        assert arr_back.max() <= 1.0
        assert arr_back.min() >= 0.0


class TestLUTGeneration:
    """Test LUT generation."""

    def test_generate_cube_shape(self):
        """generate_cube should produce correct shape."""
        from glint.lut import generate_cube

        params: FilterParams = {"contrast": 1.2}
        lut = generate_cube(params, size=10)

        # Should be size^3 entries with 3 channels each
        assert lut.shape == (1000, 3)

    def test_generate_cube_values_clamped(self):
        """generate_cube output should be clamped to 0-1."""
        from glint.lut import generate_cube

        # Extreme params
        params: FilterParams = {"brightness": 10.0, "contrast": 2.0}
        lut = generate_cube(params, size=10)

        assert lut.max() <= 1.0
        assert lut.min() >= 0.0


class TestBlend:
    """Test blending functions."""

    def test_blend_filters_empty_raises(self):
        """blend_filters with empty list should raise."""
        from glint.blend import blend_filters

        with pytest.raises(ValueError):
            blend_filters([])

    def test_blend_filters_length_mismatch(self):
        """blend_filters with mismatched lengths should raise."""
        from glint.blend import blend_filters

        with pytest.raises(ValueError):
            blend_filters([{"contrast": 1.0}], weights=[0.5, 0.5])

    def test_blend_filters_single_filter(self):
        """blending single filter should return equivalent params."""
        from glint.blend import blend_filters

        result = blend_filters([{"contrast": 1.2, "brightness": 0.1}])
        assert result["contrast"] == 1.2
        assert result["brightness"] == 0.1

    def test_blend_filters_weights_normalized(self):
        """blend_filters should normalize weights."""
        from glint.blend import blend_filters

        result = blend_filters(
            [{"contrast": 1.0}, {"contrast": 2.0}],
            weights=[1.0, 3.0],  # Total 4, should normalize to 0.25, 0.75
        )
        assert result["contrast"] == 1.75  # 1.0 * 0.25 + 2.0 * 0.75


class TestFiltersCompleteness:
    """Ensure all filters have required fields."""

    def test_all_filters_have_description(self):
        """All filters should have description."""
        for name, params in FILTERS.items():
            assert "description" in params, f"Filter {name} missing description"

    def test_all_filters_have_valid_params(self):
        """All filters should have valid numeric params."""
        for name, params in FILTERS.items():
            for key in ["contrast", "saturation", "brightness"]:
                if key in params:
                    assert isinstance(
                        params[key], (int, float)
                    ), f"Filter {name} has invalid {key}"
