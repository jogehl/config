"""Test the API routes with seesion middleware."""

from unittest import TestCase
from fastapi.testclient import TestClient

from simple_config_builder.api import make_api



class ApiTest(TestCase):
    """Test the API routes with seesion middleware."""

    def setUp(self):
        """Set up the test client."""
        app = make_api("tests/unit/config_files/config.yaml")
        self.client = TestClient(app)
        super().setUp()


    def test_version(self):
        """Test the version API route."""
        response = self.client.get("/api/v1/version")
        assert response.status_code == 200
        print(response.json())
        assert response.json()["version"] is not None


    def test_favicon(self):
        """Test the favicon API route."""
        response = self.client.get("/favicon.ico")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/vnd.microsoft.icon"


    def test_get_config_classes(self):
        """Test the get-config-classes API route."""
        response = self.client.get("/api/v1/get-config-classes")
        assert response.status_code == 200
        assert response.json()["classes"] is not None

    def tearDown(self):
        """Tear down the test client."""
        super().tearDown()
