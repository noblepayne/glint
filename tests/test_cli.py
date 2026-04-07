"""
Tests for CLI commands.
"""

import io
import argparse
from pathlib import Path
from unittest.mock import patch

from PIL import Image


class TestCLiList:
    """Test 'list' command."""

    def test_list_filters(self):
        """glint list should show available filters."""
        from glint.cli import cmd_list

        # Capture output
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = cmd_list(argparse.Namespace())

        assert result == 0
        output = captured.getvalue()
        assert "clarendon" in output
        assert "Available filters" in output


class TestCliApply:
    """Test 'apply' command."""

    def test_apply_no_input_shows_params(self):
        """apply without input should show params."""
        from glint.cli import cmd_apply

        args = argparse.Namespace(
            filter="clarendon",
            input=None,
            output=None,
            contrast=None,
            brightness=None,
            saturation=None,
            fade=None,
            grain=None,
            temperature=None,
            vignette=None,
            highlights=None,
            shadows=None,
            tint_r=None,
            tint_g=None,
            tint_b=None,
            strength=1.0,
        )

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = cmd_apply(args)

        assert result == 0
        output = captured.getvalue()
        assert "contrast" in output

    def test_apply_unknown_filter(self):
        """apply with unknown filter should error."""
        from glint.cli import cmd_apply

        args = argparse.Namespace(
            filter="nonexistent_filter",
            input=None,
            output=None,
            contrast=None,
            brightness=None,
            saturation=None,
            fade=None,
            grain=None,
            temperature=None,
            vignette=None,
            highlights=None,
            shadows=None,
            tint_r=None,
            tint_g=None,
            tint_b=None,
            strength=1.0,
        )

        captured = io.StringIO()
        with patch("sys.stderr", captured):
            result = cmd_apply(args)

        assert result == 1
        output = captured.getvalue()
        assert "Error" in output
        assert "Unknown filter" in output

    def test_apply_missing_input(self):
        """apply with non-existent input should error."""
        from glint.cli import cmd_apply

        args = argparse.Namespace(
            filter=None,
            input="/nonexistent/image.png",
            output=None,
            contrast=None,
            brightness=None,
            saturation=None,
            fade=None,
            grain=None,
            temperature=None,
            vignette=None,
            highlights=None,
            shadows=None,
            tint_r=None,
            tint_g=None,
            tint_b=None,
            strength=1.0,
        )

        captured = io.StringIO()
        with patch("sys.stderr", captured):
            result = cmd_apply(args)

        assert result == 1
        output = captured.getvalue()
        assert "Error" in output

    def test_apply_with_image(self):
        """apply with valid image should process it."""
        from glint.cli import cmd_apply

        # Create a temp image
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name

        try:
            # Create test image
            test_img = Image.new("RGB", (10, 10))
            test_img.save(temp_path)

            # Mock inside the function
            original_load = __import__(
                "glint.apply", fromlist=["load_image"]
            ).load_image
            original_apply = __import__(
                "glint.apply", fromlist=["apply_to_image"]
            ).apply_to_image

            def mock_load(path):
                return test_img

            def mock_apply(img, params):
                return test_img

            import glint.apply

            glint.apply.load_image = mock_load
            glint.apply.apply_to_image = mock_apply

            args = argparse.Namespace(
                filter="clarendon",
                input=temp_path,
                output=None,
                contrast=None,
                brightness=None,
                saturation=None,
                fade=None,
                grain=None,
                temperature=None,
                vignette=None,
                highlights=None,
                shadows=None,
                tint_r=None,
                tint_g=None,
                tint_b=None,
                strength=1.0,
            )

            captured = io.StringIO()
            with patch("sys.stdout", captured):
                result = cmd_apply(args)

            assert result == 0
            output = captured.getvalue()
            assert "Applying filter" in output

        finally:
            Path(temp_path).unlink(missing_ok=True)
            import glint.apply

            glint.apply.load_image = original_load
            glint.apply.apply_to_image = original_apply

    def test_apply_with_params_override(self):
        """apply with CLI params should override filter."""
        from glint.cli import cmd_apply

        args = argparse.Namespace(
            filter="clarendon",
            input=None,
            output=None,
            contrast=1.5,  # Override
            brightness=None,
            saturation=None,
            fade=None,
            grain=None,
            temperature=None,
            vignette=None,
            highlights=None,
            shadows=None,
            tint_r=None,
            tint_g=None,
            tint_b=None,
            strength=1.0,
        )

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = cmd_apply(args)

        assert result == 0
        output = captured.getvalue()
        assert "contrast: 1.5" in output


class TestCliGenerate:
    """Test 'generate' command."""

    @patch("glint.cli.llm.generate_from_prompt")
    def test_generate_basic(self, mock_generate):
        """generate should call LLM."""
        from glint.cli import cmd_generate

        mock_generate.return_value = {
            "contrast": 1.2,
            "saturation": 1.1,
        }

        args = argparse.Namespace(
            prompt="warm sunset",
            model="test-model",
            save=None,
            apply=False,
            image=None,
            output=None,
        )

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = cmd_generate(args)

        assert result == 0
        mock_generate.assert_called_once_with("warm sunset", model="test-model")

        output = captured.getvalue()
        assert "contrast" in output

    @patch("glint.cli.llm.generate_from_prompt")
    def test_generate_llm_error(self, mock_generate):
        """generate should handle LLM errors."""
        from glint.cli import cmd_generate

        mock_generate.side_effect = Exception("LLM error")

        args = argparse.Namespace(
            prompt="warm sunset",
            model="test-model",
            save=None,
            apply=False,
            image=None,
            output=None,
        )

        captured = io.StringIO()
        with patch("sys.stderr", captured):
            result = cmd_generate(args)

        assert result == 1
        output = captured.getvalue()
        assert "Error" in output


class TestCliExport:
    """Test 'export' command."""

    def test_export_unknown_filter(self):
        """export with unknown filter should error."""
        from glint.cli import cmd_export

        args = argparse.Namespace(
            filter="nonexistent",
            output=None,
            size=33,
        )

        captured = io.StringIO()
        with patch("sys.stderr", captured):
            result = cmd_export(args)

        assert result == 1
        output = captured.getvalue()
        assert "Error" in output

    @patch("glint.cli.save_cube")
    def test_export_known_filter(self, mock_save):
        """export with known filter should work."""
        from glint.cli import cmd_export

        args = argparse.Namespace(
            filter="clarendon",
            output=None,
            size=33,
        )

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = cmd_export(args)

        assert result == 0
        mock_save.assert_called_once()


class TestCliMain:
    """Test main CLI entry point."""

    def test_no_command_shows_help(self):
        """Running without command should show help."""
        from glint.cli import main

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            with patch("sys.argv", ["glint"]):
                result = main()

        # Returns 1 when no command
        assert result == 1

    def test_list_command(self):
        """Running 'list' should work."""
        from glint.cli import main

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            with patch("sys.argv", ["glint", "list"]):
                result = main()

        assert result == 0
        output = captured.getvalue()
        assert "Available filters" in output

    def test_apply_command_shows_help(self):
        """Running 'apply' without args should show help."""
        from glint.cli import main

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            with patch("sys.argv", ["glint", "apply"]):
                result = main()

        # argparse will show error/help
        assert result >= 0

    def test_serve_command_help(self):
        """Running 'serve --help' should show help."""
        from glint.cli import main

        # argparse --help exits with status 0, but output goes to stderr
        with patch("sys.argv", ["glint", "serve", "--help"]):
            try:
                result = main()
            except SystemExit as e:
                result = e.code

        # Help exits with 0
        assert result == 0
