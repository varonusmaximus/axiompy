"""
Railway-Oriented Programming Examples with CoreResult.

This module demonstrates how to use the Result type for elegant error handling
and operation chaining in axiompy.
"""

from axiompy.result import Err, Ok, Result, collect_results, partition_results, try_catch

# ============================================================================
# EXAMPLE 1: User Registration with Validation Chain
# ============================================================================


def validate_email(email: str) -> Result[str, str]:
    """Validate email format."""
    if "@" in email and "." in email:
        return Ok(email)
    return Err("Invalid email format")


def validate_password(password: str) -> Result[str, str]:
    """Validate password strength."""
    if len(password) >= 8:
        return Ok(password)
    return Err("Password must be at least 8 characters")


def validate_age(age: int) -> Result[int, str]:
    """Validate age requirement."""
    if age >= 18:
        return Ok(age)
    return Err("Must be 18 or older to register")


def check_user_exists(email: str) -> Result[str, str]:
    """Check if user already exists (simulated)."""
    existing_users = ["admin@example.com", "user@example.com"]
    if email not in existing_users:
        return Ok(email)
    return Err("User already exists")


def register_user_example():
    """Example: User registration with validation chain."""
    print("\n=== User Registration Example ===\n")

    # Successful registration
    print("Scenario 1: Valid registration")
    result = Ok(("john@example.com", "securepass123", 25)).then(
        lambda data: validate_email(data[0]).then(
            lambda e: validate_password(data[1]).then(lambda p: validate_age(data[2]))
        )
    )

    if result.is_ok():
        print(f"✓ Registration successful for {result.get_value()}")
    else:
        print(f"✗ Registration failed: {result.get_error()}")

    # Invalid email
    print("\nScenario 2: Invalid email")
    result = Ok(("invalid-email", "securepass123", 25)).then(lambda data: validate_email(data[0]))
    print(f"✗ {result.get_error()}")

    # Password too short
    print("\nScenario 3: Password too short")
    result = Ok(("jane@example.com", "short", 30)).then(
        lambda data: validate_email(data[0]).then(lambda _: validate_password(data[1]))
    )
    print(f"✗ {result.get_error()}")

    # User already exists
    print("\nScenario 4: User already exists")
    result = Ok(("admin@example.com", "securepass123", 25)).then(
        lambda data: validate_email(data[0]).then(lambda _: check_user_exists(data[0]))
    )
    print(f"✗ {result.get_error()}")


# ============================================================================
# EXAMPLE 2: Data Processing Pipeline
# ============================================================================


def load_csv(filename: str) -> Result[list, str]:
    """Simulate loading a CSV file."""
    if filename.endswith(".csv"):
        return Ok([1, 2, 3, 4, 5])
    return Err(f"Invalid file format: {filename}")


def parse_numbers(data: list) -> Result[list, str]:
    """Parse and validate that all items are numbers."""
    try:
        return Ok([float(x) for x in data])
    except (ValueError, TypeError) as e:
        return Err(f"Parse error: {str(e)}")


def filter_outliers(data: list) -> Result[list, str]:
    """Remove values outside 1-10 range."""
    if not data:
        return Err("Empty data")
    filtered = [x for x in data if 1 <= x <= 10]
    return Ok(filtered)


def calculate_statistics(data: list) -> Result[dict, str]:
    """Calculate mean and std dev."""
    if not data:
        return Err("Cannot calculate stats on empty data")
    mean = sum(data) / len(data)
    return Ok({"mean": mean, "count": len(data), "values": data})


def data_pipeline_example():
    """Example: Data processing pipeline with error handling."""
    print("\n=== Data Processing Pipeline Example ===\n")

    # Successful pipeline
    print("Scenario 1: Successful pipeline")
    result = (
        load_csv("data.csv").then(parse_numbers).then(filter_outliers).then(calculate_statistics)
    )

    if result.is_ok():
        stats = result.get_value()
        print("✓ Statistics calculated:")
        print(f"  Mean: {stats['mean']:.2f}")
        print(f"  Count: {stats['count']}")
        print(f"  Values: {stats['values']}")
    else:
        print(f"✗ Pipeline failed: {result.get_error()}")

    # Failed at first step
    print("\nScenario 2: Invalid file format")
    result = load_csv("data.txt").then(parse_numbers)
    print(f"✗ {result.get_error()}")

    # Recovery with fallback
    print("\nScenario 3: Recovery with fallback")
    result = load_csv("data.txt").or_else(lambda _: Ok([2.5, 3.5, 4.5]))  # Use default data
    print(f"✓ Recovered with fallback data: {result.get_value()}")


# ============================================================================
# EXAMPLE 3: API Response Handling
# ============================================================================


def fetch_user_data(user_id: int) -> Result[dict, str]:
    """Simulate fetching user data from API."""
    if user_id > 0:
        return Ok({"id": user_id, "name": f"User {user_id}", "active": True})
    return Err(f"Invalid user ID: {user_id}")


def validate_user_data(user: dict) -> Result[dict, str]:
    """Validate required fields in user data."""
    required_fields = ["id", "name", "active"]
    if all(field in user for field in required_fields):
        return Ok(user)
    return Err("Missing required user fields")


def enrich_user_data(user: dict) -> Result[dict, str]:
    """Add computed fields to user data."""
    user["display_name"] = user["name"].upper()
    user["is_active"] = user["active"]
    return Ok(user)


def api_example():
    """Example: API response handling with validation."""
    print("\n=== API Response Handling Example ===\n")

    # Successful API call
    print("Scenario 1: Successful API call")
    result = (
        fetch_user_data(123)
        .then(validate_user_data)
        .then(enrich_user_data)
        .map(
            lambda u: {
                "id": u["id"],
                "name": u["display_name"],
                "status": "active" if u["is_active"] else "inactive",
            }
        )
    )

    if result.is_ok():
        user = result.get_value()
        print(f"✓ User data: {user}")
    else:
        print(f"✗ {result.get_error()}")

    # Failed API call with recovery
    print("\nScenario 2: Failed API call with recovery")
    result = fetch_user_data(-1).or_else(
        lambda err: Ok({"id": 0, "name": "Guest", "active": False})
    )

    if result.is_ok():
        user = result.get_value()
        print(f"✓ Recovered with guest user: {user['name']}")


# ============================================================================
# EXAMPLE 4: Batch Processing with collect_results
# ============================================================================


def process_item(item: int) -> Result[int, str]:
    """Process a single item - fails if divisible by 5."""
    if item % 5 == 0:
        return Err(f"Cannot process {item} (divisible by 5)")
    return Ok(item * 2)


def batch_processing_example():
    """Example: Batch processing with error collection."""
    print("\n=== Batch Processing Example ===\n")

    items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    print("Scenario 1: Collect all successes (fail fast)")
    results = [process_item(x) for x in items[:4]]
    collected = collect_results(results)

    if collected.is_ok():
        print(f"✓ All items processed: {collected.get_value()}")
    else:
        print(f"✗ Failed at: {collected.get_error()}")

    print("\nScenario 2: Partition successes and failures")
    results = [process_item(x) for x in items]
    successes, failures = partition_results(results)

    print(f"✓ Processed: {successes}")
    print(f"✗ Failed: {failures}")


# ============================================================================
# EXAMPLE 5: Exception Handling with try_catch
# ============================================================================


def parse_json_string(json_str: str) -> dict:
    """Parse JSON string (will raise exception on invalid JSON)."""
    import json

    return json.loads(json_str)


def try_catch_example():
    """Example: Converting exceptions to Results."""
    print("\n=== Exception Handling Example ===\n")

    # Valid JSON
    print("Scenario 1: Valid JSON")
    result = try_catch(parse_json_string, '{"name": "Alice", "age": 30}')
    if result.is_ok():
        print(f"✓ Parsed: {result.get_value()}")
    else:
        print(f"✗ {result.get_error()}")

    # Invalid JSON
    print("\nScenario 2: Invalid JSON")
    result = try_catch(parse_json_string, "not valid json")
    if result.is_ok():
        print(f"✓ Parsed: {result.get_value()}")
    else:
        print(f"✗ Error: {result.get_error()}")

    # Chain with other operations
    print("\nScenario 3: Chain exception handling")
    result = (
        try_catch(parse_json_string, '{"name": "Bob"}')
        .map(lambda obj: obj.get("name", "Unknown"))
        .map(str.upper)
    )

    if result.is_ok():
        print(f"✓ Name (uppercase): {result.get_value()}")
    else:
        print(f"✗ {result.get_error()}")


# ============================================================================
# EXAMPLE 6: Advanced Chaining with map() and map_error()
# ============================================================================


def advanced_chaining_example():
    """Example: Advanced chaining patterns."""
    print("\n=== Advanced Chaining Example ===\n")

    # Transform both success and error paths
    print("Scenario 1: Transform both paths")
    result = (
        Ok(10).map(lambda x: x * 2).map(lambda x: x + 5).map_error(lambda e: f"Error: {e}")
    )  # Would only apply if error

    print(f"✓ Success path: {result.get_value()}")

    # Error transformation
    print("\nScenario 2: Error transformation")
    result = (
        Err("operation failed")
        .map(lambda x: x * 2)  # Not executed
        .map_error(lambda e: {"error": e, "code": 500})
    )

    error = result.get_error()
    print(f"✗ Transformed error: {error}")

    # map_or with default
    print("\nScenario 3: map_or with default")
    result1 = Ok(5)
    result2 = Err("failed")

    print(f"✓ Ok result mapped: {result1.map_or(0, lambda x: x * 10)}")
    print(f"✓ Err result defaulted: {result2.map_or(0, lambda x: x * 10)}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Railway-Oriented Programming Examples with CoreResult")
    print("=" * 70)

    register_user_example()
    data_pipeline_example()
    api_example()
    batch_processing_example()
    try_catch_example()
    advanced_chaining_example()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70 + "\n")
