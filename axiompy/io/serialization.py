# @!code-style

"""
Serialization and deserialization utilities for HTTP clients.

This module provides pluggable serializers and deserializers for converting
Python objects to various formats (JSON, etc.) and parsing responses back into
Python objects.

Features:
    - **Abstract Base Classes**: Extensible Serializer and Deserializer interfaces
    - **Format Support**: JSON, XML, YAML, and custom formats
    - **Factory Pattern**: Simple factory methods for common formats
    - **Type-Safe**: Generic typing support

Examples:
    >>> from axiompy.io import HTTPClientFactory
    >>> from axiompy.io.serialization import SerializerFactory, DeserializerFactory
    >>>
    >>> # Get JSON deserializer
    >>> deserializer = DeserializerFactory.create_json()
    >>> client = HTTPClientFactory.create()
    >>> data = client.get("https://api.example.com/data", deserializer=deserializer)
    >>>
    >>> # Get JSON serializer
    >>> serializer = SerializerFactory.create_json()
    >>> response = client.post(
    ...     "https://api.example.com/data",
    ...     json={"key": "value"},
    ...     serializer=serializer
    ... )
"""

import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Type, TypeVar

import requests

from axiompy.loggers import LoggerFactory

logger = LoggerFactory.create_logger(__name__)

T = TypeVar("T")


class SerializationFormat(Enum):
    """Supported serialization formats."""

    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    PROTOBUF = "protobuf"


class Serializer(ABC):
    """
    Abstract base class for serializers.

    Serializers convert Python objects to sendable formats (typically for request bodies).
    """

    @abstractmethod
    def serialize(self, data: Any) -> Any:
        """
        Serialize data to sendable format.

        Args:
            data: Python object to serialize

        Returns:
            Serialized data (typically dict, string, or bytes)

        Raises:
            SerializationError: If serialization fails
        """
        pass


class Deserializer(ABC):
    """
    Abstract base class for deserializers.

    Deserializers convert HTTP responses to Python objects.
    """

    @abstractmethod
    def deserialize(self, response: requests.Response) -> Any:
        """
        Deserialize HTTP response to Python object.

        Args:
            response: HTTP response object

        Returns:
            Deserialized Python object

        Raises:
            SerializationError: If deserialization fails
        """
        pass


class SerializationError(Exception):
    """Error during serialization/deserialization."""

    pass


class JSONSerializer(Serializer):
    """JSON serializer implementation."""

    def __init__(self, **kwargs):
        """
        Initialize JSON serializer.

        Args:
            **kwargs: Additional arguments to pass to json.dumps()
        """
        self.kwargs = kwargs

    def serialize(self, data: Any) -> Any:
        """
        Serialize data to JSON-compatible format.

        Args:
            data: Python object to serialize

        Returns:
            Data in JSON-serializable format (typically a dict)

        Raises:
            SerializationError: If serialization fails
        """
        try:
            # Validate that the data is JSON-serializable
            json.dumps(data, **self.kwargs)
            # Return the original data; requests will handle JSON encoding
            return data
        except (TypeError, ValueError) as e:
            raise SerializationError(f"Failed to serialize data to JSON: {str(e)}")


class JSONDeserializer(Deserializer):
    """JSON deserializer implementation."""

    def __init__(self, **kwargs):
        """
        Initialize JSON deserializer.

        Args:
            **kwargs: Additional arguments to pass to response.json()
        """
        self.kwargs = kwargs

    def deserialize(self, response: requests.Response) -> Dict[str, Any]:
        """
        Deserialize JSON response.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON response

        Raises:
            SerializationError: If deserialization fails
        """
        try:
            return response.json(**self.kwargs)
        except ValueError as e:
            raise SerializationError(f"Failed to parse JSON response: {str(e)}")


class XMLDeserializer(Deserializer):
    """XML deserializer implementation (basic ElementTree)."""

    def deserialize(self, response: requests.Response) -> Any:
        """
        Deserialize XML response.

        Args:
            response: HTTP response object

        Returns:
            ElementTree Element object

        Raises:
            SerializationError: If deserialization fails
        """
        try:
            import xml.etree.ElementTree as ET

            return ET.fromstring(response.content)
        except Exception as e:
            raise SerializationError(f"Failed to parse XML response: {str(e)}")


class YAMLDeserializer(Deserializer):
    """YAML deserializer implementation."""

    def deserialize(self, response: requests.Response) -> Any:
        """
        Deserialize YAML response.

        Args:
            response: HTTP response object

        Returns:
            Parsed YAML response (typically dict)

        Raises:
            SerializationError: If deserialization fails
        """
        try:
            import yaml

            return yaml.safe_load(response.text)
        except ImportError:
            raise SerializationError("PyYAML is not installed. Install it with: pip install pyyaml")
        except Exception as e:
            raise SerializationError(f"Failed to parse YAML response: {str(e)}")


class SerializerFactory:
    """Factory for creating serializers."""

    _serializers: Dict[SerializationFormat, Type[Serializer]] = {
        SerializationFormat.JSON: JSONSerializer,
    }

    @staticmethod
    def create_json(**kwargs) -> JSONSerializer:
        """
        Create a JSON serializer.

        Args:
            **kwargs: Additional arguments to pass to json.dumps()

        Returns:
            JSONSerializer instance
        """
        logger.debug("Creating JSON serializer")
        return JSONSerializer(**kwargs)

    @staticmethod
    def create(format: SerializationFormat, **kwargs) -> Serializer:
        """
        Create a serializer for the specified format.

        Args:
            format: Serialization format
            **kwargs: Format-specific arguments

        Returns:
            Serializer instance

        Raises:
            SerializationError: If format is not supported
        """
        serializer_class = SerializerFactory._serializers.get(format)
        if not serializer_class:
            raise SerializationError(
                f"Unsupported serialization format: {format.value}. "
                f"Supported formats: {', '.join(f.value for f in SerializationFormat)}"
            )
        logger.debug(f"Creating serializer for format: {format.value}")
        return serializer_class(**kwargs)

    @staticmethod
    def register(format: SerializationFormat, serializer_class: Type[Serializer]) -> None:
        """
        Register a custom serializer.

        Args:
            format: Serialization format
            serializer_class: Serializer class to register

        Examples:
            >>> class CustomSerializer(Serializer):
            ...     def serialize(self, data):
            ...         return str(data)
            >>>
            >>> SerializerFactory.register(SerializationFormat.JSON, CustomSerializer)
        """
        SerializerFactory._serializers[format] = serializer_class
        logger.debug(f"Registered custom serializer for format: {format.value}")


class DeserializerFactory:
    """Factory for creating deserializers."""

    _deserializers: Dict[SerializationFormat, Type[Deserializer]] = {
        SerializationFormat.JSON: JSONDeserializer,
        SerializationFormat.XML: XMLDeserializer,
        SerializationFormat.YAML: YAMLDeserializer,
    }

    @staticmethod
    def create_json(**kwargs) -> JSONDeserializer:
        """
        Create a JSON deserializer.

        Args:
            **kwargs: Additional arguments to pass to response.json()

        Returns:
            JSONDeserializer instance

        Examples:
            >>> client = HTTPClientFactory.create()
            >>> deserializer = DeserializerFactory.create_json()
            >>> data = client.get("https://api.example.com/data", deserializer=deserializer)
        """
        logger.debug("Creating JSON deserializer")
        return JSONDeserializer(**kwargs)

    @staticmethod
    def create_xml() -> XMLDeserializer:
        """
        Create an XML deserializer.

        Returns:
            XMLDeserializer instance

        Examples:
            >>> client = HTTPClientFactory.create()
            >>> deserializer = DeserializerFactory.create_xml()
            >>> root = client.get("https://api.example.com/data.xml", deserializer=deserializer)
        """
        logger.debug("Creating XML deserializer")
        return XMLDeserializer()

    @staticmethod
    def create_yaml() -> YAMLDeserializer:
        """
        Create a YAML deserializer.

        Returns:
            YAMLDeserializer instance

        Examples:
            >>> client = HTTPClientFactory.create()
            >>> deserializer = DeserializerFactory.create_yaml()
            >>> data = client.get("https://api.example.com/data.yaml", deserializer=deserializer)
        """
        logger.debug("Creating YAML deserializer")
        return YAMLDeserializer()

    @staticmethod
    def create(format: SerializationFormat, **kwargs) -> Deserializer:
        """
        Create a deserializer for the specified format.

        Args:
            format: Deserialization format
            **kwargs: Format-specific arguments

        Returns:
            Deserializer instance

        Raises:
            SerializationError: If format is not supported

        Examples:
            >>> deserializer = DeserializerFactory.create(SerializationFormat.JSON)
            >>> client = HTTPClientFactory.create()
            >>> data = client.get("https://api.example.com/data", deserializer=deserializer)
        """
        deserializer_class = DeserializerFactory._deserializers.get(format)
        if not deserializer_class:
            raise SerializationError(
                f"Unsupported deserialization format: {format.value}. "
                f"Supported formats: {', '.join(f.value for f in SerializationFormat)}"
            )
        logger.debug(f"Creating deserializer for format: {format.value}")
        return deserializer_class(**kwargs)

    @staticmethod
    def register(format: SerializationFormat, deserializer_class: Type[Deserializer]) -> None:
        """
        Register a custom deserializer.

        Args:
            format: Deserialization format
            deserializer_class: Deserializer class to register

        Examples:
            >>> class CustomDeserializer(Deserializer):
            ...     def deserialize(self, response):
            ...         return response.text
            >>>
            >>> DeserializerFactory.register(SerializationFormat.JSON, CustomDeserializer)
        """
        DeserializerFactory._deserializers[format] = deserializer_class
        logger.debug(f"Registered custom deserializer for format: {format.value}")
