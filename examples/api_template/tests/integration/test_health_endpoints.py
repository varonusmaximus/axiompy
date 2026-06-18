# @!documentation

"""
Integration tests for health check endpoints.

Tests API endpoints end-to-end with real HTTP requests.
"""


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "operational"

    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert data["status"] == "healthy"

    def test_api_documentation(self, client):
        """Test API documentation is available."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


class TestErrorHandling:
    """Test suite for error handling."""

    def test_404_not_found(self, client):
        """Test 404 error for non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_400_validation_error(self, client):
        """Test 400 error for invalid request."""
        # Send POST without required fields
        response = client.post("/api/v1/resources", json={})
        # Expect 400 or 422 validation error
        assert response.status_code in [400, 422]

    def test_error_response_format(self, client):
        """Test error response has required fields."""
        response = client.post("/api/v1/resources", json={})
        if response.status_code in [400, 422]:
            data = response.json()
            # Response should have detail or similar error field
            assert "detail" in data or "error" in data
