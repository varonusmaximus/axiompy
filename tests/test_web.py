"""
Comprehensive tests for axiompy.web module.

Tests railway-oriented validation, error handling, pagination, and adapter patterns.
"""

import pytest
from fastapi import HTTPException
from pydantic import BaseModel, Field

from axiompy.result import Err
from axiompy.web import (
    AdapterPattern,
    PaginationHelper,
    ResultConverter,
    ResultErrorHandler,
    ResultValidator,
)

# ============================================================================
# Test Fixtures and Models
# ============================================================================


class UserModel(BaseModel):
    """Test Pydantic model"""

    id: int = Field(None)
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5)


class DomainUser:
    """Test domain entity"""

    def __init__(self, id=None, name=None, email=None):
        self.id = id
        self.name = name
        self.email = email


@pytest.fixture
def valid_user_data():
    """Valid user data for testing"""
    return {"id": 1, "name": "John Doe", "email": "john@example.com"}


@pytest.fixture
def invalid_user_data():
    """Invalid user data (missing required fields)"""
    return {"name": "John"}  # Missing email


# ============================================================================
# ResultValidator Tests
# ============================================================================


class TestResultValidator:
    """Test suite for ResultValidator"""

    def test_parse_model_valid(self, valid_user_data):
        """Test parsing valid data returns Ok"""
        result = ResultValidator.parse_model(valid_user_data, UserModel)

        assert result.is_ok()
        model = result.unwrap()
        assert isinstance(model, UserModel)
        assert model.name == "John Doe"
        assert model.email == "john@example.com"

    def test_parse_model_invalid_missing_fields(self, invalid_user_data):
        """Test parsing invalid data returns Err"""
        result = ResultValidator.parse_model(invalid_user_data, UserModel)

        assert result.is_err()
        error = result.get_error()
        assert "Validation error" in error
        assert "field(s) failed" in error

    def test_parse_model_invalid_format(self):
        """Test parsing with wrong data format"""
        result = ResultValidator.parse_model("not a dict", UserModel)

        assert result.is_err()
        error = result.get_error()
        assert "Invalid request" in error

    def test_validate_pagination_valid(self):
        """Test valid pagination parameters"""
        result = ResultValidator.validate_pagination(page=1, per_page=10)

        assert result.is_ok()
        page, per_page = result.unwrap()
        assert page == 1
        assert per_page == 10

    def test_validate_pagination_page_zero(self):
        """Test page must be positive"""
        result = ResultValidator.validate_pagination(page=0, per_page=10)

        assert result.is_err()
        error = result.get_error()
        assert "positive" in error.lower()

    def test_validate_pagination_per_page_too_high(self):
        """Test per_page max limit"""
        result = ResultValidator.validate_pagination(page=1, per_page=1000)

        assert result.is_err()
        error = result.get_error()
        assert "between 1 and 100" in error

    def test_validate_pagination_per_page_zero(self):
        """Test per_page must be >= 1"""
        result = ResultValidator.validate_pagination(page=1, per_page=0)

        assert result.is_err()

    def test_validate_id_valid(self):
        """Test valid ID"""
        result = ResultValidator.validate_id(123)

        assert result.is_ok()
        assert result.unwrap() == 123

    def test_validate_id_zero(self):
        """Test ID cannot be zero (empty)"""
        result = ResultValidator.validate_id(0)

        assert result.is_err()
        error = result.get_error()
        assert "cannot be empty" in error

    def test_validate_id_custom_field_name(self):
        """Test custom field name in error"""
        result = ResultValidator.validate_id(0, field_name="UserID")

        assert result.is_err()
        error = result.get_error()
        assert "UserID" in error

    def test_validate_required_with_value(self):
        """Test required validation passes with value"""
        result = ResultValidator.validate_required("some_value", "field")

        assert result.is_ok()
        assert result.unwrap() == "some_value"

    def test_validate_required_with_none(self):
        """Test required validation fails with None"""
        result = ResultValidator.validate_required(None, "field")

        assert result.is_err()
        error = result.get_error()
        assert "cannot be empty" in error


# ============================================================================
# ResultConverter Tests
# ============================================================================


class TestResultConverter:
    """Test suite for ResultConverter"""

    def test_or_not_found_with_value(self):
        """Test converter passes through non-None value"""
        user = DomainUser(id=1, name="John", email="john@example.com")
        result = ResultConverter.or_not_found(user, "User")

        assert result.is_ok()
        assert result.unwrap() == user

    def test_or_not_found_with_none_no_id(self):
        """Test converter returns Err for None without ID"""
        result = ResultConverter.or_not_found(None, "User")

        assert result.is_err()
        error = result.get_error()
        assert "User not found" in error

    def test_or_not_found_with_none_with_id(self):
        """Test converter includes ID in error message"""
        result = ResultConverter.or_not_found(None, "User", resource_id=123)

        assert result.is_err()
        error = result.get_error()
        assert "User 123 not found" in error

    def test_or_not_found_custom_type(self):
        """Test with custom resource type"""
        result = ResultConverter.or_not_found(None, "Article", resource_id=456)

        assert result.is_err()
        error = result.get_error()
        assert "Article 456 not found" in error

    def test_or_empty_list_with_list(self):
        """Test converter passes through list"""
        items = [1, 2, 3]
        result = ResultConverter.or_empty_list(items)

        assert result.is_ok()
        assert result.unwrap() == items

    def test_or_empty_list_with_none(self):
        """Test converter returns empty list for None"""
        result = ResultConverter.or_empty_list(None)

        assert result.is_ok()
        assert result.unwrap() == []

    def test_or_empty_list_with_empty_list(self):
        """Test converter passes through empty list"""
        result = ResultConverter.or_empty_list([])

        assert result.is_ok()
        assert result.unwrap() == []


# ============================================================================
# ResultErrorHandler Tests
# ============================================================================


class TestResultErrorHandler:
    """Test suite for ResultErrorHandler"""

    def test_handle_error_not_found(self):
        """Test handling 'not found' error returns 404"""
        result = Err("Resource 123 not found")

        with pytest.raises(HTTPException) as exc_info:
            ResultErrorHandler.handle_error(result)

        assert exc_info.value.status_code == 404
        assert "NOT_FOUND" in str(exc_info.value.detail)

    def test_handle_error_validation(self):
        """Test handling validation error returns 400"""
        result = Err("Validation error: invalid email")

        with pytest.raises(HTTPException) as exc_info:
            ResultErrorHandler.handle_error(result)

        assert exc_info.value.status_code == 400
        assert "VALIDATION_ERROR" in str(exc_info.value.detail)

    def test_handle_error_conflict(self):
        """Test handling conflict error returns 409"""
        result = Err("Email already exists")

        with pytest.raises(HTTPException) as exc_info:
            ResultErrorHandler.handle_error(result)

        assert exc_info.value.status_code == 409
        assert "CONFLICT" in str(exc_info.value.detail)

    def test_handle_error_generic(self):
        """Test handling generic error uses default status"""
        result = Err("Some random error")

        with pytest.raises(HTTPException) as exc_info:
            ResultErrorHandler.handle_error(result, default_status=500)

        assert exc_info.value.status_code == 500
        assert "ERROR" in str(exc_info.value.detail)

    def test_handle_error_format(self):
        """Test error detail format"""
        result = Err("Invalid input")

        with pytest.raises(HTTPException) as exc_info:
            ResultErrorHandler.handle_error(result)

        detail = exc_info.value.detail
        assert "error" in detail
        assert "error_code" in detail


# ============================================================================
# PaginationHelper Tests
# ============================================================================


class TestPaginationHelper:
    """Test suite for PaginationHelper"""

    def test_paginate_first_page(self):
        """Test pagination first page"""
        items = list(range(1, 26))  # 25 items
        result = PaginationHelper.paginate(items, page=1, per_page=10)

        assert result["items"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["per_page"] == 10
        assert result["pagination"]["total"] == 25
        assert result["pagination"]["total_pages"] == 3

    def test_paginate_middle_page(self):
        """Test pagination middle page"""
        items = list(range(1, 26))
        result = PaginationHelper.paginate(items, page=2, per_page=10)

        assert result["items"] == [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        assert result["pagination"]["page"] == 2

    def test_paginate_last_page_partial(self):
        """Test pagination last page with fewer items"""
        items = list(range(1, 26))
        result = PaginationHelper.paginate(items, page=3, per_page=10)

        assert result["items"] == [21, 22, 23, 24, 25]
        assert result["pagination"]["page"] == 3
        assert result["pagination"]["total_pages"] == 3

    def test_paginate_exact_boundary(self):
        """Test pagination exact boundary (30 items, 3 pages of 10)"""
        items = list(range(1, 31))
        result = PaginationHelper.paginate(items, page=3, per_page=10)

        assert result["items"] == [21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
        assert result["pagination"]["total_pages"] == 3

    def test_paginate_empty_list(self):
        """Test pagination with empty list"""
        result = PaginationHelper.paginate([], page=1, per_page=10)

        assert result["items"] == []
        assert result["pagination"]["total"] == 0
        assert result["pagination"]["total_pages"] == 0

    def test_paginate_single_item(self):
        """Test pagination with single item"""
        result = PaginationHelper.paginate([1], page=1, per_page=10)

        assert result["items"] == [1]
        assert result["pagination"]["total"] == 1
        assert result["pagination"]["total_pages"] == 1

    def test_paginate_models(self):
        """Test pagination with Pydantic models"""
        models = [
            UserModel(id=i, name=f"User{i}", email=f"user{i}@example.com") for i in range(1, 26)
        ]
        result = PaginationHelper.paginate_models(models, page=1, per_page=10)

        assert len(result["items"]) == 10
        assert result["items"][0]["name"] == "User1"
        assert result["pagination"]["total"] == 25
        assert result["pagination"]["total_pages"] == 3

    def test_paginate_models_serialized(self):
        """Test paginated models are properly serialized"""
        models = [
            UserModel(id=i, name=f"User{i}", email=f"user{i}@example.com") for i in range(1, 6)
        ]
        result = PaginationHelper.paginate_models(models, page=1, per_page=10)

        # Verify serialization
        for item in result["items"]:
            assert isinstance(item, dict)
            assert "id" in item
            assert "name" in item
            assert "email" in item


# ============================================================================
# AdapterPattern Tests
# ============================================================================


class TestAdapterPattern:
    """Test suite for AdapterPattern"""

    def test_adapt_create_success(self, valid_user_data):
        """Test successful create adapter flow"""

        def to_domain(model):
            return DomainUser(name=model.name, email=model.email)

        def create_service(domain_user):
            domain_user.id = 123
            return domain_user

        def from_domain(domain_user):
            return UserModel(id=domain_user.id, name=domain_user.name, email=domain_user.email)

        result = AdapterPattern.adapt_create(
            valid_user_data, UserModel, to_domain, create_service, from_domain
        )

        assert result.is_ok()
        response = result.unwrap()
        assert "data" in response
        assert "message" in response
        assert response["data"]["id"] == 123

    def test_adapt_create_validation_failure(self, invalid_user_data):
        """Test create adapter fails on validation"""

        def to_domain(model):
            return DomainUser(name=model.name, email=model.email)

        def create_service(domain_user):
            return domain_user

        def from_domain(domain_user):
            return UserModel(id=domain_user.id, name=domain_user.name, email=domain_user.email)

        result = AdapterPattern.adapt_create(
            invalid_user_data, UserModel, to_domain, create_service, from_domain
        )

        assert result.is_err()
        error = result.get_error()
        assert "Validation error" in error

    def test_adapt_get_found(self, valid_user_data):
        """Test GET adapter finds resource"""

        def get_service(resource_id):
            return DomainUser(id=resource_id, name="John", email="john@example.com")

        def from_domain(domain_user):
            return UserModel(id=domain_user.id, name=domain_user.name, email=domain_user.email)

        result = AdapterPattern.adapt_get(123, get_service, from_domain)

        assert result.is_ok()
        response = result.unwrap()
        assert "data" in response
        assert response["data"]["id"] == 123

    def test_adapt_get_not_found(self):
        """Test GET adapter resource not found"""

        def get_service(resource_id):
            return None

        def from_domain(domain_user):
            return UserModel(id=domain_user.id, name=domain_user.name, email=domain_user.email)

        result = AdapterPattern.adapt_get(999, get_service, from_domain)

        assert result.is_err()
        error = result.get_error()
        assert "999" in error or "not found" in error.lower()


# ============================================================================
# Integration Tests
# ============================================================================


class TestWebIntegration:
    """Integration tests for web module components together"""

    def test_full_pipeline_success(self, valid_user_data):
        """Test full ROP pipeline: parse → validate → service → format"""
        # Step 1: Parse HTTP
        parse_result = ResultValidator.parse_model(valid_user_data, UserModel)
        assert parse_result.is_ok()

        # Step 2: Convert to domain
        model = parse_result.unwrap()
        domain_user = DomainUser(name=model.name, email=model.email)

        # Step 3: Service call
        domain_user.id = 42

        # Step 4: Convert back to HTTP
        response_model = UserModel(
            id=domain_user.id, name=domain_user.name, email=domain_user.email
        )

        # Step 5: Format response
        response = {"data": response_model.model_dump(mode="json"), "status": "success"}

        assert response["data"]["id"] == 42

    def test_full_pipeline_error_handling(self, invalid_user_data):
        """Test full ROP pipeline with error short-circuit"""
        parse_result = ResultValidator.parse_model(invalid_user_data, UserModel)
        assert parse_result.is_err()

        # Verify error handling
        with pytest.raises(HTTPException):
            ResultErrorHandler.handle_error(parse_result)

    def test_pagination_with_models_full_flow(self):
        """Test pagination with models from service"""
        # Simulate service returning models
        models = [
            UserModel(id=i, name=f"User{i}", email=f"user{i}@example.com") for i in range(1, 26)
        ]

        # Paginate
        result = PaginationHelper.paginate_models(models, page=2, per_page=10)

        # Verify
        assert len(result["items"]) == 10
        assert result["items"][0]["id"] == 11  # Second page starts at 11
        assert result["pagination"]["page"] == 2
        assert result["pagination"]["total"] == 25
