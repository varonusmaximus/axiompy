# @!documentation

"""
Test script for the Metrics Service API.

This script demonstrates how to use the Metrics API programmatically and tests
all the endpoints without requiring curl commands.

Usage:
    # In one terminal, start the server:
    python examples/metrics/metrics_server.py

    # In another terminal, run this test:
    python examples/metrics/test_metrics_api.py
"""

import json
import time

import pytest
import requests

# Mark all tests in this module as requiring a running server
pytestmark = pytest.mark.skip(
    reason="Requires running metrics server (python examples/metrics/metrics_server.py)"
)


BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test the health check endpoint."""
    print("\n🔍 Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✅ Health check passed")


def test_create_metric():
    """Test creating a new metric."""
    print("\n🔍 Testing metric creation...")

    metric_data = {
        "name": "daily_revenue",
        "description": "Total daily revenue from all sales",
        "source_system": "sales_database",
        "query_template": "SELECT DATE(created_at) as date, SUM(amount) as revenue FROM sales WHERE DATE(created_at) = ?",
        "tags": "financial,daily,revenue",
    }

    response = requests.post(f"{BASE_URL}/api/v1/metrics", json=metric_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 201
    assert "metric" in response.json()
    print("✅ Metric creation passed")
    return response.json()["metric"]["id"]


def test_create_multiple_metrics():
    """Create multiple metrics for testing."""
    print("\n🔍 Creating additional metrics...")

    metrics = [
        {
            "name": "active_users",
            "description": "Count of active users per day",
            "source_system": "user_database",
            "query_template": "SELECT COUNT(DISTINCT user_id) FROM activity WHERE DATE(timestamp) = ?",
            "tags": "users,daily,engagement",
        },
        {
            "name": "conversion_rate",
            "description": "Daily conversion rate percentage",
            "source_system": "analytics_database",
            "query_template": "SELECT (COUNT(conversions) * 100.0 / COUNT(visits)) as rate FROM events WHERE DATE(created_at) = ?",
            "tags": "financial,conversion,daily",
        },
        {
            "name": "avg_order_value",
            "description": "Average order value",
            "source_system": "sales_database",
            "query_template": "SELECT AVG(order_total) FROM orders WHERE DATE(created_at) = ?",
            "tags": "financial,sales",
        },
    ]

    created_ids = []
    for metric_data in metrics:
        try:
            response = requests.post(f"{BASE_URL}/api/v1/metrics", json=metric_data)
            if response.status_code == 201:
                created_ids.append(response.json()["metric"]["id"])
                print(f"  ✓ Created: {metric_data['name']}")
        except Exception as e:
            print(f"  ✗ Failed to create {metric_data['name']}: {e}")

    print(f"✅ Created {len(created_ids)} additional metrics")
    return created_ids


def test_get_metric(metric_id: int):
    """Test getting a specific metric."""
    print(f"\n🔍 Testing get metric (ID: {metric_id})...")

    response = requests.get(f"{BASE_URL}/api/v1/metrics/{metric_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    assert response.json()["metric"]["id"] == metric_id
    print("✅ Get metric passed")


def test_list_all_metrics():
    """Test listing all metrics."""
    print("\n🔍 Testing list all metrics...")

    response = requests.get(f"{BASE_URL}/api/v1/metrics")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found {data['count']} metrics")
    print(f"Response: {json.dumps(data, indent=2)}")
    assert response.status_code == 200
    assert "metrics" in data
    assert data["count"] > 0
    print("✅ List all metrics passed")


def test_filter_by_tag():
    """Test filtering metrics by tag."""
    print("\n🔍 Testing filter by tag (tag=financial)...")

    response = requests.get(f"{BASE_URL}/api/v1/metrics?tag=financial")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found {data['count']} metrics with tag 'financial'")
    print(f"Response: {json.dumps(data, indent=2)}")
    assert response.status_code == 200

    # Verify all returned metrics have the tag
    for metric in data["metrics"]:
        assert "financial" in metric.get("tags", "")

    print("✅ Filter by tag passed")


def test_update_metric(metric_id: int):
    """Test updating a metric."""
    print(f"\n🔍 Testing update metric (ID: {metric_id})...")

    update_data = {
        "description": "Updated: Total daily revenue from all sales channels",
        "tags": "financial,daily,revenue,updated",
    }

    response = requests.put(f"{BASE_URL}/api/v1/metrics/{metric_id}", json=update_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200

    updated_metric = response.json()["metric"]
    assert updated_metric["description"] == update_data["description"]
    assert "updated" in updated_metric["tags"]
    print("✅ Update metric passed")


def test_update_nonexistent_metric():
    """Test updating a metric that doesn't exist."""
    print("\n🔍 Testing update nonexistent metric...")

    response = requests.put(
        f"{BASE_URL}/api/v1/metrics/99999", json={"description": "This should fail"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 404
    print("✅ Update nonexistent metric properly returned 404")


def test_validation_errors():
    """Test validation error handling."""
    print("\n🔍 Testing validation errors...")

    # Test missing required field
    invalid_metric = {
        "name": "incomplete_metric",
        # Missing required fields
    }

    response = requests.post(f"{BASE_URL}/api/v1/metrics", json=invalid_metric)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 400
    assert "error" in response.json()
    print("✅ Validation error handling passed")


def test_delete_metric(metric_id: int):
    """Test deleting a metric."""
    print(f"\n🔍 Testing delete metric (ID: {metric_id})...")

    response = requests.delete(f"{BASE_URL}/api/v1/metrics/{metric_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200

    # Verify it's actually deleted
    get_response = requests.get(f"{BASE_URL}/api/v1/metrics/{metric_id}")
    assert get_response.status_code == 404
    print("✅ Delete metric passed")


def run_all_tests():
    """Run all API tests."""
    print("=" * 70)
    print("🧪 Starting Metrics API Tests")
    print("=" * 70)

    try:
        # Wait for server to be ready
        print("\n⏳ Waiting for server to be ready...")
        max_retries = 10
        for i in range(max_retries):
            try:
                requests.get(f"{BASE_URL}/health", timeout=1)
                print("✓ Server is ready")
                break
            except requests.exceptions.RequestException:
                if i < max_retries - 1:
                    time.sleep(1)
                else:
                    raise Exception("Server not responding. Make sure to start it first!")

        # Run tests
        test_health_check()

        metric_id = test_create_metric()
        additional_ids = test_create_multiple_metrics()

        test_get_metric(metric_id)
        test_list_all_metrics()
        test_filter_by_tag()
        test_update_metric(metric_id)
        test_update_nonexistent_metric()
        test_validation_errors()

        # Delete one of the additional metrics (keep the first one for other tests)
        if additional_ids:
            test_delete_metric(additional_ids[0])

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to the server.")
        print("Please make sure the metrics server is running:")
        print("  python examples/metrics_server.py")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
