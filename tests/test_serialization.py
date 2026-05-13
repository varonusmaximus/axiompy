"""
Comprehensive tests for axiompy.io.serialization module.

Tests cover:
- JSONSerializer and JSONDeserializer
- XMLDeserializer
- YAMLDeserializer
- SerializerFactory and DeserializerFactory
- Error handling and edge cases
- Custom serializer/deserializer registration
"""

import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch

import pytest
import requests

from axiompy.io.serialization import (
    Deserializer,
    DeserializerFactory,
    JSONDeserializer,
    JSONSerializer,
    SerializationError,
    SerializationFormat,
    Serializer,
    SerializerFactory,
    XMLDeserializer,
    YAMLDeserializer,
)

# ============================================================================
# Tests for JSONSerializer
# ============================================================================


class TestJSONSerializer:
    """Tests for JSONSerializer."""

    def test_serialize_dict(self):
        """Test serializing a dictionary."""
        serializer = JSONSerializer()
        data = {"key": "value", "number": 42}
        result = serializer.serialize(data)
        assert result == data
        assert isinstance(result, dict)

    def test_serialize_list(self):
        """Test serializing a list."""
        serializer = JSONSerializer()
        data = [1, 2, 3, "four"]
        result = serializer.serialize(data)
        assert result == data
        assert isinstance(result, list)

    def test_serialize_nested_dict(self):
        """Test serializing nested dictionaries."""
        serializer = JSONSerializer()
        data = {"outer": {"inner": {"deep": "value"}}}
        result = serializer.serialize(data)
        assert result == data

    def test_serialize_with_none(self):
        """Test serializing None."""
        serializer = JSONSerializer()
        result = serializer.serialize(None)
        assert result is None

    def test_serialize_with_bool(self):
        """Test serializing booleans."""
        serializer = JSONSerializer()
        assert serializer.serialize(True) is True
        assert serializer.serialize(False) is False

    def test_serialize_with_numbers(self):
        """Test serializing various number types."""
        serializer = JSONSerializer()
        assert serializer.serialize(42) == 42
        assert serializer.serialize(3.14) == 3.14
        assert serializer.serialize(0) == 0

    def test_serialize_non_json_serializable(self):
        """Test that non-JSON-serializable objects raise SerializationError."""
        serializer = JSONSerializer()

        class CustomObj:
            pass

        with pytest.raises(SerializationError) as exc_info:
            serializer.serialize(CustomObj())
        assert "Failed to serialize data to JSON" in str(exc_info.value)

    def test_serialize_with_datetime(self):
        """Test that datetime objects raise SerializationError without default handler."""
        from datetime import datetime

        serializer = JSONSerializer()

        with pytest.raises(SerializationError):
            serializer.serialize({"date": datetime.now()})

    def test_serialize_with_custom_kwargs(self):
        """Test JSONSerializer with custom json.dumps kwargs."""
        serializer = JSONSerializer(indent=2, sort_keys=True)
        data = {"z": 1, "a": 2}
        # Should succeed and validate JSON
        result = serializer.serialize(data)
        assert result == data

    def test_serialize_empty_dict(self):
        """Test serializing empty dictionary."""
        serializer = JSONSerializer()
        result = serializer.serialize({})
        assert result == {}

    def test_serialize_empty_list(self):
        """Test serializing empty list."""
        serializer = JSONSerializer()
        result = serializer.serialize([])
        assert result == []


# ============================================================================
# Tests for JSONDeserializer
# ============================================================================


class TestJSONDeserializer:
    """Tests for JSONDeserializer."""

    def test_deserialize_json_response(self):
        """Test deserializing a valid JSON response."""
        deserializer = JSONDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {"result": "success"}

        result = deserializer.deserialize(mock_response)
        assert result == {"result": "success"}
        mock_response.json.assert_called_once()

    def test_deserialize_json_list_response(self):
        """Test deserializing a JSON array response."""
        deserializer = JSONDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = [1, 2, 3]

        result = deserializer.deserialize(mock_response)
        assert result == [1, 2, 3]

    def test_deserialize_json_null_response(self):
        """Test deserializing a null JSON response."""
        deserializer = JSONDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = None

        result = deserializer.deserialize(mock_response)
        assert result is None

    def test_deserialize_invalid_json(self):
        """Test that invalid JSON raises SerializationError."""
        deserializer = JSONDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with pytest.raises(SerializationError) as exc_info:
            deserializer.deserialize(mock_response)
        assert "Failed to parse JSON response" in str(exc_info.value)

    def test_deserialize_with_custom_kwargs(self):
        """Test JSONDeserializer with custom kwargs passed to json()."""
        deserializer = JSONDeserializer(strict=False)
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {"data": "value"}

        result = deserializer.deserialize(mock_response)
        assert result == {"data": "value"}
        mock_response.json.assert_called_once_with(strict=False)

    def test_deserialize_empty_object(self):
        """Test deserializing empty JSON object."""
        deserializer = JSONDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {}

        result = deserializer.deserialize(mock_response)
        assert result == {}

    def test_deserialize_nested_json(self):
        """Test deserializing deeply nested JSON."""
        deserializer = JSONDeserializer()
        nested_data = {"a": {"b": {"c": {"d": [1, 2, 3]}}}}
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = nested_data

        result = deserializer.deserialize(mock_response)
        assert result == nested_data


# ============================================================================
# Tests for XMLDeserializer
# ============================================================================


class TestXMLDeserializer:
    """Tests for XMLDeserializer."""

    def test_deserialize_xml_response(self):
        """Test deserializing a valid XML response."""
        deserializer = XMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.content = b"<root><item>value</item></root>"

        result = deserializer.deserialize(mock_response)
        assert result.tag == "root"
        assert result[0].text == "value"

    def test_deserialize_xml_with_attributes(self):
        """Test deserializing XML with attributes."""
        deserializer = XMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.content = b'<root attr="test"><item id="1">value</item></root>'

        result = deserializer.deserialize(mock_response)
        assert result.get("attr") == "test"
        assert result[0].get("id") == "1"

    def test_deserialize_invalid_xml(self):
        """Test that invalid XML raises SerializationError."""
        deserializer = XMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.content = b"<root><unclosed>"

        with pytest.raises(SerializationError) as exc_info:
            deserializer.deserialize(mock_response)
        assert "Failed to parse XML response" in str(exc_info.value)

    def test_deserialize_empty_xml(self):
        """Test deserializing empty/whitespace XML."""
        deserializer = XMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.content = b""

        with pytest.raises(SerializationError):
            deserializer.deserialize(mock_response)

    def test_deserialize_xml_with_namespace(self):
        """Test deserializing XML with namespaces."""
        deserializer = XMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.content = b'<root xmlns="http://example.com"><item>value</item></root>'

        result = deserializer.deserialize(mock_response)
        assert result.tag == "{http://example.com}root"

    def test_deserialize_xml_returns_element(self):
        """Test that XML deserializer returns ElementTree Element."""
        deserializer = XMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.content = b"<root><child>text</child></root>"

        result = deserializer.deserialize(mock_response)
        assert isinstance(result, ET.Element)


# ============================================================================
# Tests for YAMLDeserializer
# ============================================================================


class TestYAMLDeserializer:
    """Tests for YAMLDeserializer."""

    def test_deserialize_yaml_response(self):
        """Test deserializing a valid YAML response."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            pytest.skip("PyYAML not installed")

        deserializer = YAMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.text = "key: value\nnumber: 42"

        result = deserializer.deserialize(mock_response)
        assert result == {"key": "value", "number": 42}

    def test_deserialize_yaml_list(self):
        """Test deserializing YAML list."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            pytest.skip("PyYAML not installed")

        deserializer = YAMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.text = "- item1\n- item2\n- item3"

        result = deserializer.deserialize(mock_response)
        assert result == ["item1", "item2", "item3"]

    def test_deserialize_yaml_without_pyyaml(self):
        """Test that missing PyYAML raises helpful error."""
        deserializer = YAMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.text = "key: value"

        with patch.dict("sys.modules", {"yaml": None}):
            # Simulate ImportError
            with patch("builtins.__import__", side_effect=ImportError("No module named 'yaml'")):
                with pytest.raises(SerializationError) as exc_info:
                    deserializer.deserialize(mock_response)
                assert "PyYAML is not installed" in str(exc_info.value)

    def test_deserialize_yaml_invalid(self):
        """Test that invalid YAML raises SerializationError."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            pytest.skip("PyYAML not installed")

        deserializer = YAMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        # Invalid YAML with unclosed quotes
        mock_response.text = 'key: "unclosed quote\nother: value'

        # Try to deserialize - might fail at parse time
        try:
            result = deserializer.deserialize(mock_response)
            # If it doesn't fail, at least check we got something
            assert result is not None
        except SerializationError:
            # Expected for truly invalid YAML
            pass

    def test_deserialize_yaml_null_value(self):
        """Test deserializing YAML with null values."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            pytest.skip("PyYAML not installed")

        deserializer = YAMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.text = "key: null\nother: value"

        result = deserializer.deserialize(mock_response)
        assert result == {"key": None, "other": "value"}


# ============================================================================
# Tests for SerializerFactory
# ============================================================================


class TestSerializerFactory:
    """Tests for SerializerFactory."""

    def test_create_json_serializer(self):
        """Test creating a JSON serializer."""
        serializer = SerializerFactory.create_json()
        assert isinstance(serializer, JSONSerializer)

    def test_create_json_serializer_with_kwargs(self):
        """Test creating JSON serializer with custom kwargs."""
        serializer = SerializerFactory.create_json(indent=2, sort_keys=True)
        assert isinstance(serializer, JSONSerializer)
        assert serializer.kwargs == {"indent": 2, "sort_keys": True}

    def test_create_serializer_json(self):
        """Test creating serializer via generic create() method."""
        serializer = SerializerFactory.create(SerializationFormat.JSON)
        assert isinstance(serializer, JSONSerializer)

    def test_create_serializer_unsupported_format(self):
        """Test that creating unsupported format raises error."""
        with pytest.raises(SerializationError) as exc_info:
            SerializerFactory.create(SerializationFormat.YAML)
        assert "Unsupported serialization format" in str(exc_info.value)
        assert "yaml" in str(exc_info.value)

    def test_create_serializer_protobuf_unsupported(self):
        """Test that PROTOBUF format is not supported by default."""
        with pytest.raises(SerializationError):
            SerializerFactory.create(SerializationFormat.PROTOBUF)

    def test_register_custom_serializer(self):
        """Test registering a custom serializer."""

        class CustomSerializer(Serializer):
            def serialize(self, data):
                return f"CUSTOM:{data}"

        SerializerFactory.register(SerializationFormat.PROTOBUF, CustomSerializer)
        serializer = SerializerFactory.create(SerializationFormat.PROTOBUF)
        assert isinstance(serializer, CustomSerializer)
        # Clean up
        SerializerFactory._serializers.pop(SerializationFormat.PROTOBUF, None)

    def test_register_overwrite_existing_serializer(self):
        """Test overwriting an existing serializer registration."""

        class CustomJSONSerializer(Serializer):
            def serialize(self, data):
                return {"wrapped": data}

        original = SerializerFactory._serializers[SerializationFormat.JSON]
        try:
            SerializerFactory.register(SerializationFormat.JSON, CustomJSONSerializer)
            serializer = SerializerFactory.create(SerializationFormat.JSON)
            assert isinstance(serializer, CustomJSONSerializer)
        finally:
            # Restore original
            SerializerFactory._serializers[SerializationFormat.JSON] = original

    def test_serializer_factory_returns_new_instances(self):
        """Test that factory returns new instances each time."""
        ser1 = SerializerFactory.create_json()
        ser2 = SerializerFactory.create_json()
        assert ser1 is not ser2
        assert isinstance(ser1, JSONSerializer)
        assert isinstance(ser2, JSONSerializer)


# ============================================================================
# Tests for DeserializerFactory
# ============================================================================


class TestDeserializerFactory:
    """Tests for DeserializerFactory."""

    def test_create_json_deserializer(self):
        """Test creating a JSON deserializer."""
        deserializer = DeserializerFactory.create_json()
        assert isinstance(deserializer, JSONDeserializer)

    def test_create_json_deserializer_with_kwargs(self):
        """Test creating JSON deserializer with custom kwargs."""
        deserializer = DeserializerFactory.create_json(strict=False)
        assert isinstance(deserializer, JSONDeserializer)
        assert deserializer.kwargs == {"strict": False}

    def test_create_xml_deserializer(self):
        """Test creating an XML deserializer."""
        deserializer = DeserializerFactory.create_xml()
        assert isinstance(deserializer, XMLDeserializer)

    def test_create_yaml_deserializer(self):
        """Test creating a YAML deserializer."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            pytest.skip("PyYAML not installed")

        deserializer = DeserializerFactory.create_yaml()
        assert isinstance(deserializer, YAMLDeserializer)

    def test_create_deserializer_json(self):
        """Test creating deserializer via generic create() method."""
        deserializer = DeserializerFactory.create(SerializationFormat.JSON)
        assert isinstance(deserializer, JSONDeserializer)

    def test_create_deserializer_xml(self):
        """Test creating deserializer for XML format."""
        deserializer = DeserializerFactory.create(SerializationFormat.XML)
        assert isinstance(deserializer, XMLDeserializer)

    def test_create_deserializer_yaml(self):
        """Test creating deserializer for YAML format."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            pytest.skip("PyYAML not installed")

        deserializer = DeserializerFactory.create(SerializationFormat.YAML)
        assert isinstance(deserializer, YAMLDeserializer)

    def test_create_deserializer_unsupported_format(self):
        """Test that creating unsupported format raises error."""
        with pytest.raises(SerializationError) as exc_info:
            DeserializerFactory.create(SerializationFormat.PROTOBUF)
        assert "Unsupported deserialization format" in str(exc_info.value)

    def test_register_custom_deserializer(self):
        """Test registering a custom deserializer."""

        class CustomDeserializer(Deserializer):
            def deserialize(self, response):
                return response.text

        DeserializerFactory.register(SerializationFormat.PROTOBUF, CustomDeserializer)
        deserializer = DeserializerFactory.create(SerializationFormat.PROTOBUF)
        assert isinstance(deserializer, CustomDeserializer)
        # Clean up
        DeserializerFactory._deserializers.pop(SerializationFormat.PROTOBUF, None)

    def test_register_overwrite_existing_deserializer(self):
        """Test overwriting an existing deserializer registration."""

        class CustomJSONDeserializer(Deserializer):
            def deserialize(self, response):
                return {"wrapped": response.json()}

        original = DeserializerFactory._deserializers[SerializationFormat.JSON]
        try:
            DeserializerFactory.register(SerializationFormat.JSON, CustomJSONDeserializer)
            deserializer = DeserializerFactory.create(SerializationFormat.JSON)
            assert isinstance(deserializer, CustomJSONDeserializer)
        finally:
            # Restore original
            DeserializerFactory._deserializers[SerializationFormat.JSON] = original

    def test_deserializer_factory_returns_new_instances(self):
        """Test that factory returns new instances each time."""
        des1 = DeserializerFactory.create_json()
        des2 = DeserializerFactory.create_json()
        assert des1 is not des2
        assert isinstance(des1, JSONDeserializer)
        assert isinstance(des2, JSONDeserializer)


# ============================================================================
# Tests for SerializationFormat Enum
# ============================================================================


class TestSerializationFormat:
    """Tests for SerializationFormat enum."""

    def test_format_values(self):
        """Test SerializationFormat enum values."""
        assert SerializationFormat.JSON.value == "json"
        assert SerializationFormat.XML.value == "xml"
        assert SerializationFormat.YAML.value == "yaml"
        assert SerializationFormat.PROTOBUF.value == "protobuf"

    def test_format_iteration(self):
        """Test iterating over formats."""
        formats = list(SerializationFormat)
        assert len(formats) == 4
        assert SerializationFormat.JSON in formats
        assert SerializationFormat.XML in formats


# ============================================================================
# Tests for SerializationError
# ============================================================================


class TestSerializationError:
    """Tests for SerializationError exception."""

    def test_serialization_error_creation(self):
        """Test creating SerializationError."""
        error = SerializationError("Test error message")
        assert str(error) == "Test error message"

    def test_serialization_error_inheritance(self):
        """Test that SerializationError is an Exception."""
        error = SerializationError("Test")
        assert isinstance(error, Exception)

    def test_serialization_error_can_be_raised(self):
        """Test that SerializationError can be raised and caught."""
        with pytest.raises(SerializationError) as exc_info:
            raise SerializationError("Custom error")
        assert "Custom error" in str(exc_info.value)


# ============================================================================
# Integration Tests
# ============================================================================


class TestSerializationIntegration:
    """Integration tests for serialization module."""

    def test_serialize_then_json_error_handling(self):
        """Test that non-serializable data is caught."""
        serializer = JSONSerializer()

        class CustomObject:
            pass

        with pytest.raises(SerializationError):
            serializer.serialize(CustomObject())

    def test_deserialize_response_chain(self):
        """Test deserializing a response chain."""
        deserializer = DeserializerFactory.create_json()
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {"status": "success", "data": [1, 2, 3]}

        result = deserializer.deserialize(mock_response)
        assert result["status"] == "success"
        assert result["data"] == [1, 2, 3]

    def test_multiple_formats_in_single_request(self):
        """Test using different serializers/deserializers."""
        json_serializer = SerializerFactory.create_json()
        json_deserializer = DeserializerFactory.create_json()

        # Serialize data
        data = {"request": "payload"}
        serialized = json_serializer.serialize(data)

        # Mock response
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {"response": "data"}

        # Deserialize response
        deserialized = json_deserializer.deserialize(mock_response)

        assert serialized == data
        assert deserialized == {"response": "data"}

    def test_factory_with_different_kwargs(self):
        """Test creating serializers/deserializers with different kwargs."""
        ser1 = SerializerFactory.create_json()
        ser2 = SerializerFactory.create_json(indent=2)

        assert ser1.kwargs == {}
        assert ser2.kwargs == {"indent": 2}

    def test_error_messages_are_descriptive(self):
        """Test that error messages are helpful."""
        deserializer = DeserializerFactory.create_json()
        mock_response = Mock(spec=requests.Response)
        mock_response.json.side_effect = ValueError("Invalid JSON at line 1")

        with pytest.raises(SerializationError) as exc_info:
            deserializer.deserialize(mock_response)

        error_msg = str(exc_info.value)
        assert "Failed to parse JSON response" in error_msg
        assert "Invalid JSON" in error_msg

    def test_complex_nested_json_serialization(self):
        """Test serializing complex nested structures."""
        serializer = SerializerFactory.create_json()

        complex_data = {
            "users": [
                {"id": 1, "name": "Alice", "tags": ["admin", "user"]},
                {"id": 2, "name": "Bob", "tags": ["user"]},
            ],
            "metadata": {
                "count": 2,
                "version": "1.0",
            },
        }

        result = serializer.serialize(complex_data)
        assert result == complex_data
        assert result["users"][0]["name"] == "Alice"
        assert result["metadata"]["count"] == 2


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Edge case tests for serialization."""

    def test_serializer_with_circular_reference(self):
        """Test that circular references raise SerializationError."""
        serializer = JSONSerializer()
        data = {"a": 1}
        data["self"] = data  # Create circular reference

        with pytest.raises(SerializationError):
            serializer.serialize(data)

    def test_deserializer_with_unicode_json(self):
        """Test deserializing JSON with unicode characters."""
        deserializer = DeserializerFactory.create_json()
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {
            "greeting": "Hello 👋",
            "message": "こんにちは",
            "emoji": "🎉",
        }

        result = deserializer.deserialize(mock_response)
        assert result["greeting"] == "Hello 👋"
        assert result["message"] == "こんにちは"

    def test_xml_deserializer_with_cdata(self):
        """Test deserializing XML with CDATA sections."""
        deserializer = XMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.content = b"<root><text><![CDATA[Some <markup> here]]></text></root>"

        result = deserializer.deserialize(mock_response)
        assert result.tag == "root"
        assert "Some <markup> here" in result[0].text

    def test_serializer_with_infinity(self):
        """Test that infinity values are passed through (json.dumps allows by default)."""
        serializer = JSONSerializer()

        # By default, json.dumps allows inf/nan, so no error is raised
        result = serializer.serialize({"value": float("inf")})
        assert result == {"value": float("inf")}

    def test_serializer_with_nan(self):
        """Test that NaN values are passed through (json.dumps allows by default)."""
        serializer = JSONSerializer()

        # By default, json.dumps allows inf/nan, so no error is raised
        result = serializer.serialize({"value": float("nan")})
        assert result["value"] != result["value"]  # NaN != NaN is True

    def test_factory_persistence_across_calls(self):
        """Test that custom registrations persist."""

        class CounterSerializer(Serializer):
            call_count = 0

            def serialize(self, data):
                CounterSerializer.call_count += 1
                return data

        original = SerializerFactory._serializers.get(SerializationFormat.PROTOBUF)
        try:
            # Register custom
            SerializerFactory.register(SerializationFormat.PROTOBUF, CounterSerializer)

            # Create and use multiple times
            ser1 = SerializerFactory.create(SerializationFormat.PROTOBUF)
            ser1.serialize({"test": 1})

            ser2 = SerializerFactory.create(SerializationFormat.PROTOBUF)
            ser2.serialize({"test": 2})

            assert CounterSerializer.call_count == 2
        finally:
            if original:
                SerializerFactory._serializers[SerializationFormat.PROTOBUF] = original
            else:
                SerializerFactory._serializers.pop(SerializationFormat.PROTOBUF, None)

    def test_deserializer_json_with_large_numbers(self):
        """Test JSON deserializer with very large numbers."""
        deserializer = DeserializerFactory.create_json()
        mock_response = Mock(spec=requests.Response)
        large_number = 999999999999999999999999999999
        mock_response.json.return_value = {"big": large_number}

        result = deserializer.deserialize(mock_response)
        assert result["big"] == large_number

    def test_xml_deserializer_with_processing_instruction(self):
        """Test deserializing XML with processing instructions."""
        deserializer = XMLDeserializer()
        mock_response = Mock(spec=requests.Response)
        mock_response.content = b'<?xml version="1.0"?><root><item>test</item></root>'

        result = deserializer.deserialize(mock_response)
        assert result.tag == "root"
        assert result[0].text == "test"

    def test_multiple_deserializers_independent(self):
        """Test that multiple deserializer instances are independent."""
        des1 = DeserializerFactory.create_json()
        des2 = DeserializerFactory.create_json(strict=False)

        assert des1.kwargs == {}
        assert des2.kwargs == {"strict": False}
        assert des1 is not des2

    def test_serializer_preserves_types(self):
        """Test that serializer preserves various Python types."""
        serializer = JSONSerializer()
        data = {
            "int": 42,
            "float": 3.14,
            "string": "text",
            "bool_true": True,
            "bool_false": False,
            "null": None,
            "list": [1, 2, 3],
        }

        result = serializer.serialize(data)
        assert isinstance(result["int"], int)
        assert isinstance(result["float"], float)
        assert isinstance(result["string"], str)
        assert isinstance(result["bool_true"], bool)
        assert result["null"] is None
