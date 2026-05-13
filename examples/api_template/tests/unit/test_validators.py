"""
Unit tests for validation logic.

Tests validator functions in isolation.
"""

import pytest

from axiompy.validators import ValidationError, ensure_not_empty, ensure_not_none, ensure_positive


class TestValidators:
    """Test suite for axiompy validators."""

    def test_ensure_not_empty_success(self):
        """Test ensure_not_empty with valid input."""
        ensure_not_empty("valid", "Value should not be empty")
        ensure_not_empty("data", "Should pass for non-empty string")

    def test_ensure_not_empty_failure(self):
        """Test ensure_not_empty with empty input."""
        with pytest.raises(ValidationError):
            ensure_not_empty("", "Value cannot be empty")

    def test_ensure_not_none_success(self):
        """Test ensure_not_none with valid input."""
        ensure_not_none("value", "Value should not be None")
        ensure_not_none(42, "Should pass for non-None value")

    def test_ensure_not_none_failure(self):
        """Test ensure_not_none with None input."""
        with pytest.raises(ValidationError):
            ensure_not_none(None, "Value cannot be None")

    def test_ensure_positive_success(self):
        """Test ensure_positive with valid input."""
        ensure_positive(1, "Value should be positive")
        ensure_positive(100, "Should pass for positive number")

    def test_ensure_positive_with_none_allowed(self):
        """Test ensure_positive with allow_none=True."""
        ensure_positive(None, "Value can be None", allow_none=True)
        ensure_positive(5, "Value should be positive", allow_none=True)

    def test_ensure_positive_failure(self):
        """Test ensure_positive with zero/negative."""
        with pytest.raises(ValidationError):
            ensure_positive(0, "Value must be positive")

        with pytest.raises(ValidationError):
            ensure_positive(-1, "Value must be positive")


class TestBusinessValidators:
    """Test suite for business logic validators."""

    def test_validate_resource_name(self):
        """Test resource name validation."""
        # Valid names
        valid_names = ["Resource", "My Resource", "Resource-123", "resource_name"]
        for name in valid_names:
            ensure_not_empty(name, "Name cannot be empty")

    def test_validate_priority(self):
        """Test priority validation."""
        # Valid priorities
        for priority in [1, 2, 3, 4, 5]:
            ensure_positive(priority, "Priority must be positive")

    def test_validate_limit_parameter(self):
        """Test limit parameter validation."""
        valid_limits = [1, 10, 50, 100]
        for limit in valid_limits:
            ensure_positive(limit, "Limit must be positive")

        # Invalid limits
        with pytest.raises(ValidationError):
            ensure_positive(0, "Limit must be positive")
