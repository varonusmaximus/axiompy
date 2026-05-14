"""
Unit tests for the validators module.

Run with: pytest test_validators.py -v
"""

from datetime import date, datetime, timedelta, timezone, UTC

import pytest

from axiompy.validators import (
    ValidationError,
    ensure_all_items_in_choices,
    ensure_all_items_type,
    ensure_between_exclusive,
    ensure_callable,
    ensure_contains,
    ensure_date,
    ensure_date_not_in_future,
    ensure_date_not_in_past,
    ensure_datetime,
    ensure_datetime_tz_aware,
    ensure_datetime_tz_naive,
    ensure_dict_has_keys,
    ensure_dict_keys_type,
    ensure_dict_values_type,
    ensure_email,
    ensure_ends_with,
    ensure_exact_length,
    ensure_equal,
    ensure_finite,
    ensure_gt,
    ensure_gte,
    ensure_in_choices,
    ensure_in_range,
    ensure_instance_of,
    ensure_length,
    ensure_list_contains,
    ensure_lt,
    ensure_lte,
    ensure_matches_any,
    ensure_max_length,
    ensure_min_length,
    ensure_negative,
    ensure_non_empty_iterable,
    ensure_non_negative,
    ensure_none_or,
    ensure_not_blank,
    ensure_not_empty,
    ensure_not_equal,
    ensure_not_none,
    ensure_positive,
    ensure_regex_match,
    ensure_starts_with,
    ensure_subclass_of,
    ensure_type,
    ensure_unique_items,
    ensure_url,
)


class TestEnsureNotNone:
    def test_valid_value(self):
        """Should not raise for non-None values"""
        ensure_not_none(0)
        ensure_not_none("")
        ensure_not_none([])
        ensure_not_none("value")

    def test_none_value(self):
        """Should raise for None"""
        with pytest.raises(ValidationError, match="Value cannot be None"):
            ensure_not_none(None)

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Custom error"):
            ensure_not_none(None, "Custom error")


class TestEnsureNotEmpty:
    def test_valid_values(self):
        """Should not raise for non-empty values"""
        ensure_not_empty("hello")
        ensure_not_empty([1, 2, 3])
        ensure_not_empty({"key": "value"})
        ensure_not_empty((1, 2))
        ensure_not_empty({1, 2, 3})

    def test_empty_string(self):
        """Should raise for empty string"""
        with pytest.raises(ValidationError, match="Value cannot be empty"):
            ensure_not_empty("")

    def test_empty_list(self):
        """Should raise for empty list"""
        with pytest.raises(ValidationError, match="Value cannot be empty"):
            ensure_not_empty([])

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="My custom message"):
            ensure_not_empty([], "My custom message")


class TestEnsureType:
    def test_correct_type(self):
        """Should not raise for correct type"""
        ensure_type("hello", str)
        ensure_type(42, int)
        ensure_type(3.14, float)
        ensure_type([1, 2], list)

    def test_wrong_type(self):
        """Should raise for wrong type"""
        with pytest.raises(ValidationError, match="Expected type str, got int"):
            ensure_type(42, str)

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Wrong type provided"):
            ensure_type(42, str, "Wrong type provided")


class TestEnsureInstanceOf:
    def test_correct_instance(self):
        """Should not raise for correct instance"""
        ensure_instance_of("hello", str)
        ensure_instance_of(42, int)
        ensure_instance_of([], list)

    def test_wrong_instance(self):
        """Should raise for wrong instance"""
        with pytest.raises(ValidationError, match="Value must be an instance of"):
            ensure_instance_of(42, str)

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Not the right class"):
            ensure_instance_of(42, str, "Not the right class")


class TestEnsureInRange:
    def test_value_in_range(self):
        """Should not raise for value in range"""
        ensure_in_range(5, 1, 10)
        ensure_in_range(1, 1, 10)
        ensure_in_range(10, 1, 10)
        ensure_in_range(5.5, 1.0, 10.0)

    def test_value_below_range(self):
        """Should raise for value below range"""
        with pytest.raises(ValidationError, match="not within range"):
            ensure_in_range(0, 1, 10)

    def test_value_above_range(self):
        """Should raise for value above range"""
        with pytest.raises(ValidationError, match="not within range"):
            ensure_in_range(11, 1, 10)

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Out of bounds"):
            ensure_in_range(0, 1, 10, "Out of bounds")


class TestEnsureComparison:
    def test_gt(self):
        ensure_gt(5, 1)
        with pytest.raises(ValidationError, match="greater than"):
            ensure_gt(1, 1)

    def test_gte(self):
        ensure_gte(1, 1)
        with pytest.raises(ValidationError, match="must be >="):
            ensure_gte(0, 1)

    def test_lt(self):
        ensure_lt(1, 5)
        with pytest.raises(ValidationError, match="less than"):
            ensure_lt(5, 5)

    def test_lte(self):
        ensure_lte(5, 5)
        with pytest.raises(ValidationError, match="must be <="):
            ensure_lte(6, 5)

    def test_between_exclusive(self):
        ensure_between_exclusive(5, 1, 10)
        with pytest.raises(ValidationError, match="not within range"):
            ensure_between_exclusive(1, 1, 10)


class TestEnsureFinite:
    def test_finite_values(self):
        ensure_finite(1.0)
        ensure_finite(0)

    def test_non_finite_values(self):
        with pytest.raises(ValidationError, match="finite"):
            ensure_finite(float("inf"))
        with pytest.raises(ValidationError, match="finite"):
            ensure_finite(float("nan"))


class TestEnsurePositive:
    def test_positive_value(self):
        """Should not raise for positive values"""
        ensure_positive(1)
        ensure_positive(0.1)
        ensure_positive(1000)

    def test_zero(self):
        """Should raise for zero"""
        with pytest.raises(ValidationError, match="Value must be positive"):
            ensure_positive(0)

    def test_negative_value(self):
        """Should raise for negative values"""
        with pytest.raises(ValidationError, match="Value must be positive"):
            ensure_positive(-1)

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Must be > 0"):
            ensure_positive(0, "Must be > 0")


class TestEnsureNonNegative:
    def test_non_negative_values(self):
        """Should not raise for non-negative values"""
        ensure_non_negative(0)
        ensure_non_negative(1)
        ensure_non_negative(100.5)

    def test_negative_value(self):
        """Should raise for negative values"""
        with pytest.raises(ValidationError, match="Value must be non-negative"):
            ensure_non_negative(-1)

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Cannot be negative"):
            ensure_non_negative(-1, "Cannot be negative")


class TestEnsureNegative:
    def test_negative_value(self):
        """Should not raise for negative values"""
        ensure_negative(-1)
        ensure_negative(-0.1)
        ensure_negative(-1000)

    def test_zero(self):
        """Should raise for zero"""
        with pytest.raises(ValidationError, match="Value must be negative"):
            ensure_negative(0)

    def test_positive_value(self):
        """Should raise for positive values"""
        with pytest.raises(ValidationError, match="Value must be negative"):
            ensure_negative(1)

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Must be < 0"):
            ensure_negative(0, "Must be < 0")


class TestEnsureLength:
    def test_valid_length(self):
        """Should not raise for valid lengths"""
        ensure_length("hello", min_length=3, max_length=10)
        ensure_length([1, 2, 3], min_length=1, max_length=5)
        ensure_length("test", min_length=4)
        ensure_length("test", max_length=10)

    def test_length_too_short(self):
        """Should raise when length is too short"""
        with pytest.raises(ValidationError, match="less than minimum"):
            ensure_length("hi", min_length=3)

    def test_length_too_long(self):
        """Should raise when length is too long"""
        with pytest.raises(ValidationError, match="exceeds maximum"):
            ensure_length("hello world", max_length=5)

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Invalid length"):
            ensure_length("hi", min_length=3, message="Invalid length")


class TestEnsureLengthHelpers:
    def test_min_length(self):
        ensure_min_length("hello", 3)
        with pytest.raises(ValidationError, match="less than minimum"):
            ensure_min_length("hi", 3)

    def test_max_length(self):
        ensure_max_length("hello", 5)
        with pytest.raises(ValidationError, match="exceeds maximum"):
            ensure_max_length("hello!", 5)

    def test_exact_length(self):
        ensure_exact_length("abc", 3)
        with pytest.raises(ValidationError, match="does not equal"):
            ensure_exact_length("ab", 3)


class TestEnsureStringAssertions:
    def test_not_blank(self):
        ensure_not_blank("hello")
        with pytest.raises(ValidationError, match="blank"):
            ensure_not_blank("   ")

    def test_starts_with(self):
        ensure_starts_with("hello", "he")
        with pytest.raises(ValidationError, match="start"):
            ensure_starts_with("hello", "no")

    def test_ends_with(self):
        ensure_ends_with("hello", "lo")
        with pytest.raises(ValidationError, match="end"):
            ensure_ends_with("hello", "no")

    def test_contains(self):
        ensure_contains("hello", "ell")
        with pytest.raises(ValidationError, match="contain"):
            ensure_contains("hello", "xyz")

    def test_matches_any(self):
        ensure_matches_any("abc123", [r"^[a-z]+$", r"^[a-z]+\d+$"])
        with pytest.raises(ValidationError, match="any allowed pattern"):
            ensure_matches_any("123", [r"^[a-z]+$"])


class TestEnsureEmail:
    def test_valid_emails(self):
        """Should not raise for valid email formats"""
        ensure_email("test@example.com")
        ensure_email("user.name+tag@example.co.uk")
        ensure_email("test123@test-domain.com")

    def test_invalid_emails(self):
        """Should raise for invalid email formats"""
        with pytest.raises(ValidationError, match="not a valid email format"):
            ensure_email("invalid")

        with pytest.raises(ValidationError, match="not a valid email format"):
            ensure_email("@example.com")

        with pytest.raises(ValidationError, match="not a valid email format"):
            ensure_email("test@")

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Bad email"):
            ensure_email("invalid", "Bad email")


class TestEnsureUrl:
    def test_valid_urls(self):
        """Should not raise for valid URL formats"""
        ensure_url("http://example.com")
        ensure_url("https://www.example.com/path")
        ensure_url("https://example.com:8080/path?query=value")

    def test_invalid_urls(self):
        """Should raise for invalid URL formats"""
        with pytest.raises(ValidationError, match="not a valid URL format"):
            ensure_url("invalid")

        with pytest.raises(ValidationError, match="not a valid URL format"):
            ensure_url("example.com")

        with pytest.raises(ValidationError, match="not a valid URL format"):
            ensure_url("ftp://example.com")

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Bad URL"):
            ensure_url("invalid", "Bad URL")


class TestEnsureDate:
    def test_valid_dates(self):
        """Should not raise for valid date formats"""
        ensure_date("2025-10-22")
        ensure_date("2024-01-01")
        ensure_date("10/22/2025", date_format="%m/%d/%Y")

    def test_invalid_dates(self):
        """Should raise for invalid date formats"""
        with pytest.raises(ValidationError, match="not a valid date format"):
            ensure_date("invalid")

        with pytest.raises(ValidationError, match="not a valid date format"):
            ensure_date("2025-13-01")  # Invalid month

        with pytest.raises(ValidationError, match="not a valid date format"):
            ensure_date("10/22/2025")  # Wrong format (default is YYYY-MM-DD)

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Custom date error"):
            ensure_date("invalid", message="Custom date error")


class TestEnsureDateTime:
    def test_datetime_type(self):
        ensure_datetime(datetime.utcnow())
        with pytest.raises(ValidationError, match="datetime"):
            ensure_datetime(date.today())

    def test_tz_aware(self):
        ensure_datetime_tz_aware(datetime.now(UTC))
        with pytest.raises(ValidationError, match="timezone-aware"):
            ensure_datetime_tz_aware(datetime.utcnow())

    def test_tz_naive(self):
        ensure_datetime_tz_naive(datetime.utcnow())
        with pytest.raises(ValidationError, match="timezone-naive"):
            ensure_datetime_tz_naive(datetime.now(UTC))

    def test_not_in_future(self):
        ensure_date_not_in_future(date.today())
        with pytest.raises(ValidationError, match="future"):
            ensure_date_not_in_future(date.today() + timedelta(days=1))

    def test_not_in_past(self):
        ensure_date_not_in_past(date.today())
        with pytest.raises(ValidationError, match="past"):
            ensure_date_not_in_past(date.today() - timedelta(days=1))


class TestEnsureRegexMatch:
    def test_valid_matches(self):
        """Should not raise for strings matching pattern"""
        ensure_regex_match("hello", r"^[a-z]+$")
        ensure_regex_match("test123", r"^[a-z]+\d+$")
        ensure_regex_match("ABC", r"^[A-Z]+$")

    def test_invalid_matches(self):
        """Should raise for strings not matching pattern"""
        with pytest.raises(ValidationError, match="does not match pattern"):
            ensure_regex_match("Hello", r"^[a-z]+$")

        with pytest.raises(ValidationError, match="does not match pattern"):
            ensure_regex_match("123", r"^[a-z]+$")

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Pattern mismatch"):
            ensure_regex_match("123", r"^[a-z]+$", "Pattern mismatch")


class TestEnsureCallable:
    def test_callable_objects(self):
        """Should not raise for callable objects"""
        ensure_callable(lambda x: x)
        ensure_callable(print)
        ensure_callable(str)

        def func():
            pass

        ensure_callable(func)

    def test_non_callable_objects(self):
        """Should raise for non-callable objects"""
        with pytest.raises(ValidationError, match="is not callable"):
            ensure_callable(42)

        with pytest.raises(ValidationError, match="is not callable"):
            ensure_callable("string")

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Not a function"):
            ensure_callable(42, "Not a function")


class TestEnsureDictHasKeys:
    def test_dict_with_all_keys(self):
        """Should not raise when dict has all required keys"""
        ensure_dict_has_keys({"a": 1, "b": 2, "c": 3}, ["a", "b"])
        ensure_dict_has_keys({"key": "value"}, ["key"])

    def test_dict_missing_keys(self):
        """Should raise when dict is missing required keys"""
        with pytest.raises(ValidationError, match="missing required keys"):
            ensure_dict_has_keys({"a": 1}, ["a", "b", "c"])

    def test_not_a_dict(self):
        """Should raise when value is not a dict"""
        with pytest.raises(ValidationError, match="Expected dict"):
            ensure_dict_has_keys([1, 2, 3], ["a"])

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Keys are missing"):
            ensure_dict_has_keys({"a": 1}, ["a", "b"], "Keys are missing")


class TestEnsureDictTypes:
    def test_keys_type(self):
        ensure_dict_keys_type({"a": 1, "b": 2}, str)
        with pytest.raises(ValidationError, match="Dictionary key"):
            ensure_dict_keys_type({1: "a"}, str)

    def test_values_type(self):
        ensure_dict_values_type({"a": 1, "b": 2}, int)
        with pytest.raises(ValidationError, match="Dictionary value"):
            ensure_dict_values_type({"a": "1"}, int)


class TestEnsureListContains:
    def test_list_contains_item(self):
        """Should not raise when list contains item"""
        ensure_list_contains([1, 2, 3], 2)
        ensure_list_contains(["a", "b", "c"], "b")

    def test_list_does_not_contain_item(self):
        """Should raise when list doesn't contain item"""
        with pytest.raises(ValidationError, match="List does not contain item"):
            ensure_list_contains([1, 2, 3], 4)

    def test_not_a_list(self):
        """Should raise when value is not a list"""
        with pytest.raises(ValidationError, match="Expected list"):
            ensure_list_contains("string", "s")

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Item not found"):
            ensure_list_contains([1, 2, 3], 4, "Item not found")


class TestEnsureInChoices:
    def test_value_in_choices(self):
        """Should not raise when value is in choices"""
        ensure_in_choices("a", ["a", "b", "c"])
        ensure_in_choices(2, [1, 2, 3])
        ensure_in_choices("red", {"red", "green", "blue"})

    def test_value_not_in_choices(self):
        """Should raise when value is not in choices"""
        with pytest.raises(ValidationError, match="not in allowed choices"):
            ensure_in_choices("d", ["a", "b", "c"])

        with pytest.raises(ValidationError, match="not in allowed choices"):
            ensure_in_choices(4, [1, 2, 3])

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Invalid choice"):
            ensure_in_choices("d", ["a", "b", "c"], "Invalid choice")


class TestEnsureAllItemsInChoices:
    def test_all_items_in_choices(self):
        ensure_all_items_in_choices(["a", "b"], ["a", "b", "c"])
        with pytest.raises(ValidationError, match="not in allowed choices"):
            ensure_all_items_in_choices(["a", "d"], ["a", "b", "c"])


class TestEnsureAllItemsType:
    def test_all_items_correct_type(self):
        """Should not raise when all items are of correct type"""
        ensure_all_items_type([1, 2, 3], int)
        ensure_all_items_type(["a", "b", "c"], str)
        ensure_all_items_type([1.0, 2.0, 3.0], float)

    def test_some_items_wrong_type(self):
        """Should raise when some items are of wrong type"""
        with pytest.raises(ValidationError, match="Item at index"):
            ensure_all_items_type([1, 2, "3"], int)

        with pytest.raises(ValidationError, match="expected int"):
            ensure_all_items_type([1, 2.5, 3], int)

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Mixed types"):
            ensure_all_items_type([1, "2"], int, "Mixed types")


class TestEnsureUniqueItems:
    def test_unique_items(self):
        """Should not raise when all items are unique"""
        ensure_unique_items([1, 2, 3])
        ensure_unique_items(["a", "b", "c"])

    def test_duplicate_items(self):
        """Should raise when there are duplicate items"""
        with pytest.raises(ValidationError, match="duplicate items"):
            ensure_unique_items([1, 2, 2, 3])

        with pytest.raises(ValidationError, match="duplicate items"):
            ensure_unique_items(["a", "b", "a"])

    def test_custom_message(self):
        """Should use custom message"""
        with pytest.raises(ValidationError, match="Duplicates found"):
            ensure_unique_items([1, 1, 2], "Duplicates found")


class TestEnsureNonEmptyIterable:
    def test_non_empty_iterable(self):
        ensure_non_empty_iterable([1])

        def gen():
            yield 1

        ensure_non_empty_iterable(gen())

    def test_empty_iterable(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            ensure_non_empty_iterable([])

    def test_not_iterable(self):
        with pytest.raises(ValidationError, match="must be iterable"):
            ensure_non_empty_iterable(42)


class TestEnsureSubclassOf:
    def test_valid_subclass(self):
        """Should not raise for valid subclass"""

        class Parent:
            pass

        class Child(Parent):
            pass

        ensure_subclass_of(Child, Parent)
        ensure_subclass_of(bool, int)  # bool is a subclass of int in Python

    def test_not_a_subclass(self):
        """Should raise when not a subclass"""

        class Parent:
            pass

        class NotChild:
            pass

        with pytest.raises(ValidationError, match="is not a subclass of"):
            ensure_subclass_of(NotChild, Parent)

    def test_not_a_class(self):
        """Should raise when first argument is not a class"""
        with pytest.raises(ValidationError, match="Expected a class"):
            ensure_subclass_of("not a class", object)

    def test_custom_message(self):
        """Should use custom message"""

        class Parent:
            pass

        class NotChild:
            pass

        with pytest.raises(ValidationError, match="Wrong inheritance"):
            ensure_subclass_of(NotChild, Parent, "Wrong inheritance")


class TestEnsureEquality:
    def test_equal(self):
        ensure_equal(1, 1)
        with pytest.raises(ValidationError, match="does not equal"):
            ensure_equal(1, 2)

    def test_not_equal(self):
        ensure_not_equal(1, 2)
        with pytest.raises(ValidationError, match="must not equal"):
            ensure_not_equal(1, 1)


class TestEnsureNoneOr:
    def test_none_allowed(self):
        ensure_none_or(None, ensure_positive)

    def test_value_valid(self):
        ensure_none_or(5, ensure_positive)

    def test_value_invalid(self):
        with pytest.raises(ValidationError, match="positive"):
            ensure_none_or(-1, ensure_positive)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
