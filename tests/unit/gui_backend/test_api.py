"""Test the API routes with seesion middleware."""

from unittest import TestCase
from fastapi.testclient import TestClient

from simple_config_builder.gui_backend.api import app


def test_session():
    """Test the route for the session API."""
    client = TestClient(app)
    response = client.get("/api/v1/session")
    assert response.status_code == 200
    assert response.json()["session_key"] is not None


class ApiTest(TestCase):
    """Test the API routes with seesion middleware."""

    def setUp(self):
        """Set up the test client."""
        self.client = TestClient(app)
        self.client.cookies["session_key"] = "test-session"
        super().setUp()

    def test_session(self):
        """Test the session API route."""
        response = self.client.get("/api/v1/session")
        assert response.status_code == 200
        assert response.json()["session_key"] is not None

    def test_version(self):
        """Test the version API route."""
        response = self.client.get("/api/v1/version")
        assert response.status_code == 200
        print(response.json())
        assert response.json()["version"] is not None

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
        # load config with path: tests/unit/gui_backend/test_api.py
        response = self.client.post(
            "/api/v1/load-config",
            params={
                "config_path": "tests/unit/config_files/config_auto_reload.json"  # noqa
            },
        )
        assert response.status_code == 200
        assert response.json()["config"] is not None

    def test_get_config_classes(self):
        """Test the get-config-classes API route."""
        response = self.client.get("/api/v1/get-config-classes")
        assert response.status_code == 200
        assert response.json()["classes"] is not None

    def tearDown(self):
        """Tear down the test client."""
        super().tearDown()
