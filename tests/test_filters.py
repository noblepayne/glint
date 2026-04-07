"""
Tests for glint filters and pipeline.
"""

import numpy as np
from PIL import Image
from glint.filters import FILTERS, get_filter, list_filters
from glint.pipeline import build_pipeline, apply_pipeline, transform_array
from glint.types import FilterParams


class TestFilters:
    """Test filter presets."""

    def test_all_filters_have_name(self):
        """All filters should have a name."""
        for name, params in FILTERS.items():
            assert "name" in params, f"Filter {name} missing 'name'"

    def test_get_filter_returns_params(self):
        """get_filter should return filter params."""
        result = get_filter("clarendon")
        assert result is not None
        assert "name" in result

    def test_get_filter_case_insensitive(self):
        """get_filter should be case insensitive."""
        result1 = get_filter("clarendon")
        result2 = get_filter("Clarendon")
        assert result1 == result2

    def test_get_filter_unknown_returns_none(self):
        """get_filter should return None for unknown filters."""
        result = get_filter("nonexistent_filter")
        assert result is None

    def test_list_filters_returns_tuples(self):
        """list_filters should return list of (name, desc) tuples."""
        result = list_filters()
        assert len(result) > 0
        assert all(isinstance(r, tuple) and len(r) == 2 for r in result)


class TestPipeline:
    """Test pipeline building and execution."""

    def test_build_pipeline_empty_params(self):
        """Empty params should produce empty pipeline."""
        pipeline = build_pipeline({})
        assert len(pipeline) == 0

    def test_build_pipeline_with_contrast(self):
        """contrast != 1 should add transform."""
        pipeline = build_pipeline({"contrast": 1.5})
        assert len(pipeline) > 0

    def test_build_pipeline_with_grain(self):
        """grain > 0 should add grain transform with seed."""
        pipeline = build_pipeline({"grain": 0.5})
        assert len(pipeline) > 0

    def test_apply_pipeline_returns_array(self):
        """apply_pipeline should return numpy array."""
        rgb = np.ones((10, 10, 3)) * 0.5
        pipeline = []
        result = apply_pipeline(rgb, pipeline)
        assert isinstance(result, np.ndarray)
        assert result.shape == rgb.shape

    def test_transform_array_works(self):
        """transform_array convenience function works."""
        rgb = np.ones((10, 10, 3)) * 0.5
        result = transform_array(rgb, {})
        assert result.shape == rgb.shape

    def test_pipeline_respects_grain_seed(self):
        """Same grain_seed should produce same grain pattern."""
        params: FilterParams = {"grain": 0.5, "grain_seed": 123}
        pipeline = build_pipeline(params)
        rgb = np.ones((20, 20, 3)) * 0.5
        result1 = apply_pipeline(rgb, pipeline)
        result2 = apply_pipeline(rgb, pipeline)
        assert np.allclose(result1, result2)


class TestApplyToImage:
    """Test PIL Image application."""

    def test_apply_to_image_creates_output(self):
        """Should be able to apply params to a PIL Image."""
        from glint.apply import apply_to_image

        img = Image.new("RGB", (10, 10), (128, 100, 80))
        params: FilterParams = {"contrast": 1.2}
        result = apply_to_image(img, params)
        assert isinstance(result, Image.Image)
        assert result.size == img.size
