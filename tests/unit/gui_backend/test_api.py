"""Test GUI backend API routes."""

from collections.abc import Callable
from unittest import TestCase

from fastapi.testclient import TestClient

from simple_config_builder import Configclass
from simple_config_builder.gui_backend.api import app


class _ApiConfigClass(Configclass):
    """Test configuration class for API validation tests."""

    key: str
    func: Callable | None = None


class _NestedItem(Configclass):
    """Nested config class for list/dict schema checks."""

    name: str
    size: int


class _ContainerClass(Configclass):
    """Container config class for list/dict nested checks."""

    items: list[_NestedItem]
    mapping: dict[str, _NestedItem]


class ApiTest(TestCase):
    """Test the API routes."""

    def setUp(self):
        """Set up the test client."""
        self.client = TestClient(app)
        super().setUp()

    def test_version(self):
        """Test the version API route."""
        response = self.client.get("/api/v1/version")
        assert response.status_code == 200
        assert response.json()["version"] is not None

    def test_formats(self):
        """Test the formats API route."""
        response = self.client.get("/api/v1/formats")
        assert response.status_code == 200
        assert response.json()["formats"] == ["json", "yaml", "toml"]

    def test_cors_preflight(self):
        """Test CORS preflight response headers."""
        response = self.client.options(
            "/api/v1/formats",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] in (
            "*",
            "http://localhost:5173",
        )
        assert response.headers.get("access-control-allow-credentials") != "true"

    def test_root(self):
        """Test the root API route."""
        response = self.client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "Welcome to the GUI backend API!"

    def test_favicon(self):
        """Test the favicon API route."""
        response = self.client.get("/favicon.ico")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/vnd.microsoft.icon"

    def test_load_config(self):
        """Test the load-config API route."""
        response = self.client.post(
            "/api/v1/load-config",
            json={
                "config_path": "tests/unit/config_files/config_auto_reload.json"
            },
        )
        assert response.status_code == 200
        assert response.json()["config"] is not None
        assert response.json()["metadata"]["exists"] is True

    def test_config_metadata(self):
        """Test config metadata endpoint."""
        response = self.client.post(
            "/api/v1/config-metadata",
            json={"config_path": "tests/unit/config_files/config_auto_reload.json"},
        )
        assert response.status_code == 200
        assert response.json()["exists"] is True
        assert response.json()["sha256"] is not None

    def test_get_config_classes(self):
        """Test the get-config-classes API route."""
        response = self.client.get("/api/v1/get-config-classes")
        assert response.status_code == 200
        assert response.json()["classes"] is not None

    def test_get_config_class_schema(self):
        """Test schema endpoint for a class."""
        class_name = f"{_ApiConfigClass.__module__}.{_ApiConfigClass.__name__}"
        response = self.client.get(f"/api/v1/get-config-class/{class_name}")
        assert response.status_code == 200
        assert response.json()["schema"] is not None
        assert response.json()["normalized_schema"] is not None

    def test_normalized_schema_contains_list_and_dict_children(self):
        """List/dict of Configclass should include nested child metadata."""
        class_name = f"{_ContainerClass.__module__}.{_ContainerClass.__name__}"
        response = self.client.get(f"/api/v1/get-config-class/{class_name}")
        assert response.status_code == 200
        fields = response.json()["normalized_schema"]["fields"]

        items_field = next(field for field in fields if field["name"] == "items")
        mapping_field = next(
            field for field in fields if field["name"] == "mapping"
        )

        assert len(items_field["item_children"]) > 0
        assert len(mapping_field["value_children"]) > 0

    def test_validate_config(self):
        """Test config validation endpoint."""
        class_name = f"{_ApiConfigClass.__module__}.{_ApiConfigClass.__name__}"
        response = self.client.post(
            "/api/v1/validate-config",
            json={"class_name": class_name, "data": {"key": "value"}},
        )
        assert response.status_code == 200
        assert response.json()["valid"] is True

    def test_save_config(self):
        """Test save-config endpoint."""
        response = self.client.post(
            "/api/v1/save-config",
            json={
                "config_path": "tests/unit/config_files/config_api_save.json",
                "config_type": "json",
                "data": {"hello": "world"},
            },
        )
        assert response.status_code == 200
        assert response.json()["saved"] is True
        assert response.json()["sha256"] is not None

    def tearDown(self):
        """Tear down the test client."""
        super().tearDown()
