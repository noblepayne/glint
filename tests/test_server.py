"""
Tests for server endpoints.
"""

import io
import base64
from unittest.mock import patch

from PIL import Image
import pytest


# Server tests require httpx for async test client
try:
    from fastapi.testclient import TestClient

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


# Test data helpers
def create_test_image(format="PNG"):
    """Create a simple test image."""
    img = Image.new("RGB", (10, 10), (128, 100, 80))
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf


def image_to_data_url(img, format="PNG"):
    """Convert PIL Image to data URL."""
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return f"data:image/{format.lower()};base64,{b64}"


class TestServerEndpoints:
    """Test server endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not HAS_FASTAPI:
            pytest.skip("FastAPI not installed")
        from glint.server import app

        return TestClient(app)

    def test_index_returns_html(self, client):
        """GET / should return HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "glint" in response.text.lower()

    def test_filter_not_found(self, client):
        """GET /filter/{name} should return 404 for unknown filter."""
        response = client.get("/filter/nonexistent")
        assert response.status_code == 404

    def test_filter_known_filter(self, client):
        """GET /filter/{name} should return params for known filter."""
        response = client.get("/filter/clarendon")
        assert response.status_code == 200
        data = response.json()
        # Should have filter params but not name/description
        assert "contrast" in data
        assert "name" not in data
        assert "description" not in data

    def test_filter_case_insensitive(self, client):
        """GET /filter/{name} should be case insensitive."""
        response1 = client.get("/filter/clarendon")
        response2 = client.get("/filter/Clarendon")
        assert response1.json() == response2.json()


class TestApplyEndpoint:
    """Test /apply endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not HAS_FASTAPI:
            pytest.skip("FastAPI not installed")
        from glint.server import app

        return TestClient(app)

    def test_apply_missing_image(self, client):
        """POST /apply should fail without image."""
        response = client.post("/apply", json={"params": {}})
        # Should handle missing image gracefully
        assert response.status_code in (400, 422, 500)

    def test_apply_missing_params(self, client):
        """POST /apply should work with default params."""
        img = Image.new("RGB", (10, 10), (128, 100, 80))
        img_b64 = image_to_data_url(img)

        response = client.post("/apply", json={"image": img_b64, "params": {}})
        assert response.status_code == 200
        data = response.json()
        assert "image" in data

    def test_apply_with_params(self, client):
        """POST /apply should apply custom params."""
        img = Image.new("RGB", (10, 10), (128, 100, 80))
        img_b64 = image_to_data_url(img)

        params = {"contrast": 1.5, "saturation": 1.2}
        response = client.post("/apply", json={"image": img_b64, "params": params})
        assert response.status_code == 200
        data = response.json()
        assert "image" in data


class TestGenerateEndpoint:
    """Test /generate endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not HAS_FASTAPI:
            pytest.skip("FastAPI not installed")
        from glint.server import app

        return TestClient(app)

    def test_generate_missing_prompt(self, client):
        """POST /generate should fail without prompt."""
        response = client.post("/generate", json={})
        assert response.status_code == 400

    @patch("glint.server.llm.generate_from_prompt")
    def test_generate_with_prompt(self, mock_generate, client):
        """POST /generate should return params."""
        mock_generate.return_value = {
            "contrast": 1.2,
            "saturation": 1.1,
            "brightness": 0.05,
        }

        response = client.post(
            "/generate", json={"prompt": "warm sunset look", "model": "test-model"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "params" in data
        assert data["params"]["contrast"] == 1.2


class TestUploadEndpoint:
    """Test /upload endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not HAS_FASTAPI:
            pytest.skip("FastAPI not installed")
        from glint.server import app

        return TestClient(app)

    def test_upload_no_file(self, client):
        """POST /upload should fail without file."""
        response = client.post("/upload")
        assert response.status_code == 422

    def test_upload_invalid_file(self, client):
        """POST /upload should fail with invalid file."""
        response = client.post("/upload", files={"file": ("test.txt", b"not an image")})
        assert response.status_code in (400, 422, 500)

    def test_upload_valid_image(self, client):
        """POST /upload should accept valid image."""
        img_buf = create_test_image()
        response = client.post(
            "/upload", files={"file": ("test.png", img_buf.read(), "image/png")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "image" in data
        # Should be a data URL
        assert data["image"].startswith("data:image")

    def test_upload_resizes_large_image(self, client):
        """POST /upload should resize very large images."""
        # Create a large image
        img = Image.new("RGB", (2000, 2000), (128, 100, 80))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        response = client.post(
            "/upload", files={"file": ("large.png", buf.read(), "image/png")}
        )
        assert response.status_code == 200

        # Decode the response to check size
        data = response.json()
        header, b64data = data["image"].split(",", 1)
        img_bytes = base64.b64decode(b64data)
        result_img = Image.open(io.BytesIO(img_bytes))

        # Should be resized to max 1200
        assert max(result_img.size) <= 1200
