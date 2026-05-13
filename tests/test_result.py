"""
Comprehensive tests for Railway-Oriented Programming Result types.

Tests cover:
- Ok and Err creation and properties
- Chaining operations with then()
- Error recovery with or_else()
- Value transformation with map()
- Error transformation with map_error()
- Extracting values (unwrap, unwrap_or, expect)
- Utility functions (collect_results, partition_results, try_catch)
- Result composition and edge cases
"""

import pytest

from axiompy.result import CoreResult, Err, Ok, Result, collect_results, partition_results, try_catch


class TestOkVariant:
    """Tests for Ok (success) variant."""

    def test_ok_creation(self):
        """Test creating an Ok result."""
        result = Ok(42)
        assert result.is_ok()
        assert not result.is_err()
        assert result.get_value() == 42
        assert result.get_error() is None

    def test_ok_with_string(self):
        """Test Ok with string value."""
        result = Ok("hello")
        assert result.is_ok()
        assert result.get_value() == "hello"

    def test_ok_with_none(self):
        """Test Ok can wrap None."""
        result = Ok(None)
        assert result.is_ok()
        assert result.get_value() is None

    def test_ok_with_list(self):
        """Test Ok with list value."""
        data = [1, 2, 3]
        result = Ok(data)
        assert result.is_ok()
        assert result.get_value() == data

    def test_ok_with_dict(self):
        """Test Ok with dict value."""
        data = {"key": "value"}
        result = Ok(data)
        assert result.is_ok()
        assert result.get_value() == data

    def test_ok_repr(self):
        """Test Ok string representation."""
        result = Ok(42)
        assert "Ok" in repr(result)
        assert "42" in repr(result)

    def test_ok_bool(self):
        """Test Ok is truthy."""
        result = Ok(42)
        assert bool(result)


class TestErrVariant:
    """Tests for Err (error) variant."""

    def test_err_creation(self):
        """Test creating an Err result."""
        result = Err("error message")
        assert not result.is_ok()
        assert result.is_err()
        assert result.get_error() == "error message"
        assert result.get_value() is None

    def test_err_with_exception(self):
        """Test Err with exception object."""
        exc = ValueError("invalid value")
        result = Err(exc)
        assert result.is_err()
        assert result.get_error() == exc

    def test_err_with_none(self):
        """Test Err can wrap None."""
        result = Err(None)
        assert result.is_err()
        assert result.get_error() is None

    def test_err_with_dict(self):
        """Test Err with dict error."""
        error_dict = {"code": "ERR_001", "message": "Something went wrong"}
        result = Err(error_dict)
        assert result.is_err()
        assert result.get_error() == error_dict

    def test_err_repr(self):
        """Test Err string representation."""
        result = Err("failed")
        assert "Err" in repr(result)
        assert "failed" in repr(result)

    def test_err_bool(self):
        """Test Err is falsy."""
        result = Err("error")
        assert not bool(result)


class TestThen:
    """Tests for then() - chaining operations."""

    def test_then_with_ok(self):
        """Test then() with Ok result."""
        result = Ok(5).then(lambda x: Ok(x * 2))
        assert result.is_ok()
        assert result.get_value() == 10

    def test_then_returns_ok(self):
        """Test then() that returns Ok."""
        result = Ok(3).then(lambda x: Ok(x + 10))
        assert result.is_ok()
        assert result.get_value() == 13

    def test_then_returns_err(self):
        """Test then() that returns Err."""
        result = Ok(5).then(lambda x: Err("failed"))
        assert result.is_err()
        assert result.get_error() == "failed"

    def test_then_with_err_skips_function(self):
        """Test then() with Err result skips the function."""
        called = []
        result = Err("initial error").then(lambda x: (called.append(x), Ok(x))[1])
        assert result.is_err()
        assert result.get_error() == "initial error"
        assert len(called) == 0  # Function was not called

    def test_then_chaining(self):
        """Test chaining multiple then() calls."""
        result = Ok(5).then(lambda x: Ok(x * 2)).then(lambda x: Ok(x + 3)).then(lambda x: Ok(x**2))
        assert result.is_ok()
        assert result.get_value() == 169  # ((5*2)+3)^2 = 13^2 = 169

    def test_then_chaining_with_error(self):
        """Test chaining stops at first error."""
        called = []

        def track_call(x):
            called.append(x)
            return Ok(x * 2)

        result = (
            Ok(5).then(track_call).then(lambda x: Err("error")).then(track_call)
        )  # This should not be called
        assert result.is_err()
        assert len(called) == 1  # Only first operation called

    def test_then_with_validation(self):
        """Test then() for validation pattern."""

        def is_positive(x):
            return Ok(x) if x > 0 else Err("not positive")

        def is_even(x):
            return Ok(x) if x % 2 == 0 else Err("not even")

        # Test valid path
        result = Ok(4).then(is_positive).then(is_even)
        assert result.is_ok()
        assert result.get_value() == 4

        # Test first validation fails
        result = Ok(-4).then(is_positive).then(is_even)
        assert result.is_err()
        assert result.get_error() == "not positive"

        # Test second validation fails
        result = Ok(3).then(is_positive).then(is_even)
        assert result.is_err()
        assert result.get_error() == "not even"


class TestOrElse:
    """Tests for or_else() - error recovery."""

    def test_or_else_with_ok_skips_handler(self):
        """Test or_else() with Ok skips the handler."""
        called = []
        result = Ok(42).or_else(lambda e: (called.append(e), Ok(0))[1])
        assert result.is_ok()
        assert result.get_value() == 42
        assert len(called) == 0

    def test_or_else_with_err_calls_handler(self):
        """Test or_else() with Err calls the handler."""
        result = Err("error").or_else(lambda e: Ok(f"recovered from {e}"))
        assert result.is_ok()
        assert result.get_value() == "recovered from error"

    def test_or_else_returns_err(self):
        """Test or_else() that returns Err."""
        result = Err("error1").or_else(lambda e: Err(f"error2: {e}"))
        assert result.is_err()
        assert "error2" in result.get_error()

    def test_or_else_recovery_chain(self):
        """Test chaining recovery attempts."""

        def recover1(err):
            if "recoverable" in str(err):
                return Ok("recovered")
            return Err(err)

        result = Err("recoverable error").or_else(recover1)
        assert result.is_ok()
        assert result.get_value() == "recovered"

    def test_or_else_fallback_chain(self):
        """Test chaining fallback operations."""
        result = Err("error1").or_else(lambda e: Err("error2")).or_else(lambda e: Ok("final"))
        assert result.is_ok()
        assert result.get_value() == "final"


class TestMap:
    """Tests for map() - transform success values."""

    def test_map_with_ok(self):
        """Test map() with Ok result."""
        result = Ok(5).map(lambda x: x * 2)
        assert result.is_ok()
        assert result.get_value() == 10

    def test_map_with_err_skips_function(self):
        """Test map() with Err skips function."""
        called = []
        result = Err("error").map(lambda x: (called.append(x), x * 2)[1])
        assert result.is_err()
        assert len(called) == 0

    def test_map_type_transformation(self):
        """Test map() transforming type."""
        result = Ok(42).map(str)
        assert result.is_ok()
        assert result.get_value() == "42"

    def test_map_to_collection(self):
        """Test map() to collection."""
        result = Ok(3).map(lambda x: [x] * x)
        assert result.is_ok()
        assert result.get_value() == [3, 3, 3]

    def test_map_chaining(self):
        """Test chaining map() calls."""
        result = Ok(5).map(lambda x: x * 2).map(lambda x: x + 1).map(str)
        assert result.is_ok()
        assert result.get_value() == "11"

    def test_map_preserves_error(self):
        """Test map() preserves error through chain."""
        result = Ok(5).map(lambda x: x * 2).then(lambda x: Err("error")).map(lambda x: x + 100)
        assert result.is_err()
        assert result.get_error() == "error"


class TestMapError:
    """Tests for map_error() - transform error values."""

    def test_map_error_with_err(self):
        """Test map_error() with Err result."""
        result = Err("error").map_error(lambda e: f"mapped: {e}")
        assert result.is_err()
        assert result.get_error() == "mapped: error"

    def test_map_error_with_ok_skips_function(self):
        """Test map_error() with Ok skips function."""
        called = []
        result = Ok(42).map_error(lambda e: (called.append(e), "new")[1])
        assert result.is_ok()
        assert result.get_value() == 42
        assert len(called) == 0

    def test_map_error_type_transformation(self):
        """Test map_error() transforming error type."""
        result = Err("simple").map_error(lambda e: {"error": e})
        assert result.is_err()
        assert result.get_error() == {"error": "simple"}

    def test_map_error_chaining(self):
        """Test chaining map_error() calls."""
        result = Err("error1").map_error(lambda e: f"step1: {e}").map_error(lambda e: f"step2: {e}")
        assert result.is_err()
        assert "step2" in result.get_error()


class TestUnwrap:
    """Tests for unwrap() - extract value or raise."""

    def test_unwrap_with_ok(self):
        """Test unwrap() with Ok returns value."""
        result = Ok(42)
        assert result.unwrap() == 42

    def test_unwrap_with_err_raises(self):
        """Test unwrap() with Err raises RuntimeError."""
        result = Err("something failed")
        with pytest.raises(RuntimeError) as exc_info:
            result.unwrap()
        assert "something failed" in str(exc_info.value)

    def test_unwrap_with_none_value(self):
        """Test unwrap() can return None."""
        result = Ok(None)
        assert result.unwrap() is None

    def test_unwrap_preserves_type(self):
        """Test unwrap() preserves value type."""
        data = {"key": "value"}
        result = Ok(data)
        assert result.unwrap() is data


class TestUnwrapOr:
    """Tests for unwrap_or() - extract with default."""

    def test_unwrap_or_with_ok(self):
        """Test unwrap_or() with Ok returns value."""
        result = Ok(42)
        assert result.unwrap_or(0) == 42

    def test_unwrap_or_with_err(self):
        """Test unwrap_or() with Err returns default."""
        result = Err("error")
        assert result.unwrap_or(0) == 0

    def test_unwrap_or_default_not_called_for_ok(self):
        """Test unwrap_or() doesn't evaluate default for Ok."""
        # Note: Python evaluates all arguments before function call,
        # so we just verify Ok returns its value
        result = Ok(42)
        assert result.unwrap_or(99) == 42


class TestUnwrapOrElse:
    """Tests for unwrap_or_else() - extract with computation."""

    def test_unwrap_or_else_with_ok(self):
        """Test unwrap_or_else() with Ok returns value."""
        result = Ok(42)
        assert result.unwrap_or_else(lambda e: 0) == 42

    def test_unwrap_or_else_with_err(self):
        """Test unwrap_or_else() with Err calls function."""
        result = Err("invalid")
        value = result.unwrap_or_else(lambda e: len(e))
        assert value == 7

    def test_unwrap_or_else_function_not_called_for_ok(self):
        """Test unwrap_or_else() function not called for Ok."""
        called = []
        result = Ok(42)
        result.unwrap_or_else(lambda e: (called.append(e), 0)[1])
        assert len(called) == 0


class TestExpect:
    """Tests for expect() - extract or raise with message."""

    def test_expect_with_ok(self):
        """Test expect() with Ok returns value."""
        result = Ok(42)
        assert result.expect("should work") == 42

    def test_expect_with_err_raises_with_message(self):
        """Test expect() with Err raises with custom message."""
        result = Err("failed")
        with pytest.raises(RuntimeError) as exc_info:
            result.expect("custom error message")
        assert "custom error message" in str(exc_info.value)
        assert "failed" in str(exc_info.value)


class TestEquality:
    """Tests for Result equality."""

    def test_ok_equality(self):
        """Test Ok equality."""
        assert Ok(42) == Ok(42)
        assert Ok(42) != Ok(43)

    def test_err_equality(self):
        """Test Err equality."""
        assert Err("error") == Err("error")
        assert Err("error1") != Err("error2")

    def test_ok_err_inequality(self):
        """Test Ok and Err are not equal."""
        assert Ok(42) != Err(42)

    def test_equality_with_non_result(self):
        """Test Result not equal to non-Result."""
        assert Ok(42) != 42
        assert Err("error") != "error"


class TestAliases:
    """Tests for method aliases."""

    def test_and_then_alias(self):
        """Test and_then() is alias for then()."""
        result1 = Ok(5).then(lambda x: Ok(x * 2))
        result2 = Ok(5).and_then(lambda x: Ok(x * 2))
        assert result1 == result2


class TestMapOr:
    """Tests for map_or() - transform with default."""

    def test_map_or_with_ok(self):
        """Test map_or() with Ok."""
        result = Ok(5)
        assert result.map_or(0, lambda x: x * 2) == 10

    def test_map_or_with_err(self):
        """Test map_or() with Err."""
        result = Err("error")
        assert result.map_or(99, lambda x: x * 2) == 99


class TestMapOrElse:
    """Tests for map_or_else() - transform or compute."""

    def test_map_or_else_with_ok(self):
        """Test map_or_else() with Ok."""
        result = Ok(5)
        assert result.map_or_else(lambda e: 0, lambda x: x * 2) == 10

    def test_map_or_else_with_err(self):
        """Test map_or_else() with Err."""
        result = Err("error")
        assert result.map_or_else(lambda e: len(e), lambda x: x * 2) == 5


class TestCollectResults:
    """Tests for collect_results() utility."""

    def test_collect_all_ok(self):
        """Test collecting all Ok results."""
        results = [Ok(1), Ok(2), Ok(3)]
        collected = collect_results(results)
        assert collected.is_ok()
        assert collected.get_value() == [1, 2, 3]

    def test_collect_with_err(self):
        """Test collecting with error returns first error."""
        results = [Ok(1), Err("error"), Ok(3)]
        collected = collect_results(results)
        assert collected.is_err()
        assert collected.get_error() == "error"

    def test_collect_empty_list(self):
        """Test collecting empty list."""
        results: list = []
        collected = collect_results(results)
        assert collected.is_ok()
        assert collected.get_value() == []

    def test_collect_all_err(self):
        """Test collecting with first error."""
        results = [Err("error1"), Err("error2")]
        collected = collect_results(results)
        assert collected.is_err()
        assert collected.get_error() == "error1"


class TestPartitionResults:
    """Tests for partition_results() utility."""

    def test_partition_mixed(self):
        """Test partitioning mixed results."""
        results = [Ok(1), Err("err1"), Ok(2), Err("err2")]
        successes, errors = partition_results(results)
        assert successes == [1, 2]
        assert errors == ["err1", "err2"]

    def test_partition_all_ok(self):
        """Test partitioning all Ok."""
        results = [Ok(1), Ok(2), Ok(3)]
        successes, errors = partition_results(results)
        assert successes == [1, 2, 3]
        assert errors == []

    def test_partition_all_err(self):
        """Test partitioning all Err."""
        results = [Err("e1"), Err("e2")]
        successes, errors = partition_results(results)
        assert successes == []
        assert errors == ["e1", "e2"]

    def test_partition_empty(self):
        """Test partitioning empty list."""
        successes, errors = partition_results([])
        assert successes == []
        assert errors == []


class TestTryCatch:
    """Tests for try_catch() utility."""

    def test_try_catch_success(self):
        """Test try_catch() with successful function."""

        def add(a, b):
            return a + b

        result = try_catch(add, 2, 3)
        assert result.is_ok()
        assert result.get_value() == 5

    def test_try_catch_exception(self):
        """Test try_catch() with exception."""

        def divide(a, b):
            return a / b

        result = try_catch(divide, 1, 0)
        assert result.is_err()
        assert "division by zero" in result.get_error().lower()

    def test_try_catch_with_kwargs(self):
        """Test try_catch() with keyword arguments."""

        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = try_catch(greet, "Alice", greeting="Hi")
        assert result.is_ok()
        assert result.get_value() == "Hi, Alice!"

    def test_try_catch_custom_exception(self):
        """Test try_catch() with custom exception."""

        def validate(value):
            if value < 0:
                raise ValueError("Negative value")
            return value * 2

        result = try_catch(validate, -5)
        assert result.is_err()
        assert "Negative value" in result.get_error()


class TestRealWorldScenarios:
    """Tests for real-world use cases."""

    def test_user_registration_validation_chain(self):
        """Test user registration with validation chain."""

        def validate_email(email: str) -> Result[str, str]:
            return Ok(email) if "@" in email else Err("Invalid email")

        def validate_password(password: str) -> Result[str, str]:
            return Ok(password) if len(password) >= 8 else Err("Password too short")

        def validate_age(age: int) -> Result[int, str]:
            return Ok(age) if age >= 18 else Err("Too young")

        # Success path
        result = (
            Ok(("user@example.com", "secure123", 25))
            .map(lambda x: validate_email(x[0]).unwrap())
            .map(lambda _: validate_password("secure123").unwrap())
            .then(lambda _: validate_age(25))
        )
        assert result.is_ok()

        # Failure path
        result = Ok(("not-an-email", "short", 16)).then(lambda x: validate_email(x[0]))
        assert result.is_err()

    def test_api_response_handling(self):
        """Test API response handling with Result."""

        def fetch_api_data(endpoint: str) -> Result[dict, str]:
            return Ok({"status": "ok"}) if endpoint.startswith("/api") else Err("Invalid endpoint")

        def parse_response(data: dict) -> Result[str, str]:
            return (
                Ok(data.get("status", "unknown"))
                if "status" in data
                else Err("Missing status field")
            )

        # Success
        result = fetch_api_data("/api/users").then(parse_response)
        assert result.is_ok()
        assert result.get_value() == "ok"

        # Recovery
        result = fetch_api_data("/invalid").or_else(lambda e: Ok("default_status"))
        assert result.is_ok()


class TestCoreResultAlias:
    """Tests for CoreResult alias."""

    def test_core_result_is_result(self):
        """Test CoreResult is alias for Result."""
        assert CoreResult is Result

    def test_core_result_usage(self):
        """Test CoreResult can be used like Result."""
        result = CoreResult.error("test") if hasattr(CoreResult, "error") else Ok(42)
        # Just verify it works with standard constructors
        result = Ok(42) if isinstance(Ok(42), Result) else None
        assert isinstance(result, Result)
