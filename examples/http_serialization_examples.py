# @!documentation

"""
Examples demonstrating the new flexible HTTPClient with serializers/deserializers.

This example shows how to use the refactored HTTPClient with optional
serializers for requests and deserializers for responses.
"""

from axiompy.io import (
    DeserializerFactory,
    HTTPClientFactory,
    RetryConfig,
    SerializerFactory,
)


def example_basic_get():
    """Example: Basic GET request returning raw response."""
    print("=" * 60)
    print("Example 1: Basic GET request")
    print("=" * 60)

    client = HTTPClientFactory.create(timeout_secs=30)

    # Get raw response object
    # response = client.get("https://jsonplaceholder.typicode.com/posts/1")
    # print(f"Status: {response.status_code}")
    # print(f"Content-Type: {response.headers.get('content-type')}")

    print("✓ Raw response approach (no deserializer)")
    print()


def example_get_with_json_deserializer():
    """Example: GET request with JSON deserialization."""
    print("=" * 60)
    print("Example 2: GET request with JSON deserializer")
    print("=" * 60)

    client = HTTPClientFactory.create(timeout_secs=30)
    deserializer = DeserializerFactory.create_json()

    # Using factory-created JSON deserializer
    # data = client.get(
    #     "https://jsonplaceholder.typicode.com/posts/1",
    #     deserializer=deserializer
    # )
    # print(f"Post title: {data.get('title')}")
    # print(f"User ID: {data.get('userId')}")

    print("✓ Using DeserializerFactory.create_json()")
    print()


def example_get_with_factory_deserializer():
    """Example: GET request using factory-created deserializer."""
    print("=" * 60)
    print("Example 3: GET request with factory deserializer")
    print("=" * 60)

    client = HTTPClientFactory.create(timeout_secs=30)
    deserializer = DeserializerFactory.create_json()

    # Using factory to create deserializer
    # data = client.get(
    #     "https://jsonplaceholder.typicode.com/posts/1",
    #     deserializer=deserializer
    # )
    # print(f"Deserialized post: {data}")

    print("✓ Using DeserializerFactory to create JSON deserializer")
    print()


def example_post_with_serializer_and_deserializer():
    """Example: POST with custom serializer and deserializer."""
    print("=" * 60)
    print("Example 4: POST with serializer and deserializer")
    print("=" * 60)

    client = HTTPClientFactory.create(timeout_secs=30)
    serializer = SerializerFactory.create_json()
    deserializer = DeserializerFactory.create_json()

    payload = {
        "title": "New Post",
        "body": "This is a new post created with axiompy",
        "userId": 1,
    }

    # POST with both serializer and deserializer
    # response = client.post(
    #     "https://jsonplaceholder.typicode.com/posts",
    #     json=payload,
    #     serializer=serializer,
    #     deserializer=deserializer
    # )
    # print(f"Created post: {response}")

    print("✓ POST with serializer and deserializer")
    print()


def example_get_with_retry_and_deserializer():
    """Example: GET request with retry logic and deserialization."""
    print("=" * 60)
    print("Example 5: GET with retry and deserializer")
    print("=" * 60)

    client = HTTPClientFactory.create(timeout_secs=30)
    retry_config = RetryConfig().with_max_attempts(3)
    deserializer = DeserializerFactory.create_json()

    # GET with retry and deserialization
    # data = client.get_with_retry(
    #     "https://jsonplaceholder.typicode.com/posts/1",
    #     retry_config=retry_config,
    #     deserializer=deserializer
    # )
    # print(f"Retrieved post with retry: {data}")

    print("✓ GET with retry and deserialization")
    print()


def example_custom_deserializer():
    """Example: Using a custom deserializer."""
    print("=" * 60)
    print("Example 6: Custom deserializer")
    print("=" * 60)

    from axiompy.io import Deserializer

    class CountingDeserializer(Deserializer):
        """Custom deserializer that adds a character count."""

        def deserialize(self, response):
            data = response.json()
            if isinstance(data, dict):
                data["_response_length"] = len(response.text)
            return data

    client = HTTPClientFactory.create(timeout_secs=30)
    custom_deserializer = CountingDeserializer()

    # Use custom deserializer
    # data = client.get(
    #     "https://jsonplaceholder.typicode.com/posts/1",
    #     deserializer=custom_deserializer
    # )
    # print(f"Post with response length: {data.get('_response_length')} chars")

    print("✓ Custom deserializer implementation")
    print()


def example_xml_deserialization():
    """Example: XML deserialization."""
    print("=" * 60)
    print("Example 7: XML deserialization")
    print("=" * 60)

    client = HTTPClientFactory.create(timeout_secs=30)
    xml_deserializer = DeserializerFactory.create_xml()

    # Deserialize XML response
    # root = client.get(
    #     "https://example.com/feed.xml",
    #     deserializer=xml_deserializer
    # )
    # print(f"XML root tag: {root.tag}")

    print("✓ XML deserialization using factory")
    print()


def example_authorization_with_serialization():
    """Example: Using authentication with serialization."""
    print("=" * 60)
    print("Example 8: Authentication with serialization")
    print("=" * 60)

    client = (
        HTTPClientFactory.create(timeout_secs=30)
        .bearer_token("my-api-token")
        .add_header("X-API-Version", "v2")
    )

    serializer = SerializerFactory.create_json()
    deserializer = DeserializerFactory.create_json()

    payload = {"data": "authenticated request"}

    # POST with auth and serialization
    # response = client.post(
    #     "https://api.example.com/secure-endpoint",
    #     json=payload,
    #     serializer=serializer,
    #     deserializer=deserializer,
    # )

    print("✓ Authenticated request with serialization")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  HTTP Client Serialization Examples".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    example_basic_get()
    example_get_with_json_deserializer()
    example_get_with_factory_deserializer()
    example_post_with_serializer_and_deserializer()
    example_get_with_retry_and_deserializer()
    example_custom_deserializer()
    example_xml_deserialization()
    example_authorization_with_serialization()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print()
    print("Key takeaways:")
    print("  1. No more get_json() - use deserializer parameter instead")
    print("  2. No more post_json_for_json() - use both serializer & deserializer")
    print("  3. Create custom serializers/deserializers by extending abstract classes")
    print("  4. Use factories for common formats: JSON, XML, YAML")
    print("  5. Works with all HTTP methods and retry logic")
    print()


if __name__ == "__main__":
    main()
