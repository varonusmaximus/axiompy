"""
Tests for file I/O utilities
"""

import json
import logging

import pytest

from axiompy.io.file import (
    CachedReader,
    read_binary,
    read_csv,
    read_json,
    read_lines,
    read_multiple,
    read_text,
    read_with_path_expansion,
    safe_read,
    set_default_logger,
)


class TestSetDefaultLogger:
    """Tests for set_default_logger function"""

    def test_set_default_logger(self):
        """Test setting default logger"""
        custom_logger = logging.getLogger("test_logger")
        set_default_logger(custom_logger)
        # Logger is set successfully (tested by other functions using it)


class TestReadText:
    """Tests for read_text function"""

    def test_read_text_basic(self, tmp_path):
        """Test basic text file reading"""
        test_file = tmp_path / "test.txt"
        content = "Hello, World!"
        test_file.write_text(content)

        result = read_text(test_file)
        assert result == content

    def test_read_text_encoding(self, tmp_path):
        """Test reading with different encodings"""
        test_file = tmp_path / "test_utf8.txt"
        content = "Hello 世界 🌍"
        test_file.write_text(content, encoding="utf-8")

        result = read_text(test_file, encoding="utf-8")
        assert result == content

    def test_read_text_not_found_with_default(self, tmp_path):
        """Test reading non-existent file with default"""
        result = read_text(tmp_path / "nonexistent.txt", default="default content")
        assert result == "default content"

    def test_read_text_not_found_without_default(self, tmp_path):
        """Test reading non-existent file without default raises exception"""
        with pytest.raises(FileNotFoundError):
            read_text(tmp_path / "nonexistent.txt")

    def test_read_text_io_error_with_default(self, tmp_path):
        """Test reading file with IO error and default"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        # Make file unreadable by opening it exclusively
        with test_file.open("r") as f:
            # Try reading with strict encoding on non-UTF8 data
            binary_file = tmp_path / "binary.txt"
            binary_file.write_bytes(b"\x80\x81\x82")
            result = read_text(binary_file, encoding="utf-8", errors="strict", default="default")
            assert result == "default"

    def test_read_text_io_error_without_default(self, tmp_path):
        """Test reading file with IO error without default raises exception"""
        binary_file = tmp_path / "binary.txt"
        binary_file.write_bytes(b"\x80\x81\x82")
        with pytest.raises(UnicodeDecodeError):
            read_text(binary_file, encoding="utf-8", errors="strict")


class TestReadJson:
    """Tests for read_json function"""

    def test_read_json_dict(self, tmp_path):
        """Test reading JSON object"""
        test_file = tmp_path / "test.json"
        data = {"name": "John", "age": 30, "city": "New York"}
        test_file.write_text(json.dumps(data))

        result = read_json(test_file)
        assert result == data

    def test_read_json_list(self, tmp_path):
        """Test reading JSON array"""
        test_file = tmp_path / "test.json"
        data = [1, 2, 3, 4, 5]
        test_file.write_text(json.dumps(data))

        result = read_json(test_file)
        assert result == data

    def test_read_json_invalid_with_default(self, tmp_path):
        """Test reading invalid JSON with default"""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{invalid json")

        result = read_json(test_file, default={}, raise_on_error=False)
        assert result == {}

    def test_read_json_invalid_with_raise(self, tmp_path):
        """Test reading invalid JSON with raise"""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            read_json(test_file, raise_on_error=True)

    def test_read_json_file_not_found_raise(self, tmp_path):
        """Test reading non-existent JSON with raise_on_error"""
        with pytest.raises(FileNotFoundError):
            read_json(tmp_path / "nonexistent.json", raise_on_error=True)

    def test_read_json_file_not_found_no_raise(self, tmp_path):
        """Test reading non-existent JSON without raise_on_error"""
        result = read_json(tmp_path / "nonexistent.json", default={}, raise_on_error=False)
        assert result == {}

    def test_read_json_general_error_no_raise(self, tmp_path):
        """Test general error handling in read_json"""
        # This tests the general Exception handler
        test_file = tmp_path / "test.json"
        test_file.write_text('{"valid": "json"}')
        # We'll simulate an error by passing invalid encoding
        result = read_json(
            test_file, encoding="invalid-encoding", default={"error": True}, raise_on_error=False
        )
        assert result == {"error": True}

    def test_read_json_general_error_with_raise(self, tmp_path):
        """Test general error handling in read_json with raise_on_error=True"""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"valid": "json"}')
        # Simulate error with invalid encoding
        with pytest.raises(LookupError):  # Invalid encoding raises LookupError
            read_json(test_file, encoding="invalid-encoding", raise_on_error=True)


class TestReadLines:
    """Tests for read_lines function"""

    def test_read_lines_basic(self, tmp_path):
        """Test basic line reading"""
        test_file = tmp_path / "test.txt"
        lines = ["line 1", "line 2", "line 3"]
        test_file.write_text("\n".join(lines))

        result = list(read_lines(test_file))
        assert result == lines

    def test_read_lines_with_whitespace(self, tmp_path):
        """Test line reading with strip"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("  line 1  \n  line 2  \n  line 3  ")

        result = list(read_lines(test_file, strip=True))
        assert result == ["line 1", "line 2", "line 3"]

    def test_read_lines_skip_empty(self, tmp_path):
        """Test skipping empty lines"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line 1\n\nline 2\n\nline 3")

        result = list(read_lines(test_file, skip_empty=True))
        assert result == ["line 1", "line 2", "line 3"]

    def test_read_lines_memory_efficient(self, tmp_path):
        """Test that read_lines returns a generator"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line 1\nline 2")

        result = read_lines(test_file)
        # Should be a generator
        assert hasattr(result, "__next__")

    def test_read_lines_error(self, tmp_path):
        """Test error handling in read_lines"""
        with pytest.raises(FileNotFoundError):
            # Force evaluation of generator to trigger error
            list(read_lines(tmp_path / "nonexistent.txt"))


class TestReadCsv:
    """Tests for read_csv function"""

    def test_read_csv_with_header(self, tmp_path):
        """Test reading CSV with header"""
        test_file = tmp_path / "test.csv"
        test_file.write_text("name,age,city\nJohn,30,NYC\nJane,25,LA")

        result = read_csv(test_file)
        assert len(result) == 2
        assert result[0] == {"name": "John", "age": "30", "city": "NYC"}
        assert result[1] == {"name": "Jane", "age": "25", "city": "LA"}

    def test_read_csv_without_header(self, tmp_path):
        """Test reading CSV without header"""
        test_file = tmp_path / "test.csv"
        test_file.write_text("John,30,NYC\nJane,25,LA")

        result = read_csv(test_file, has_header=False)
        assert len(result) == 2
        assert result[0] == {"column_0": "John", "column_1": "30", "column_2": "NYC"}
        assert result[1] == {"column_0": "Jane", "column_1": "25", "column_2": "LA"}

    def test_read_csv_custom_delimiter(self, tmp_path):
        """Test reading CSV with custom delimiter"""
        test_file = tmp_path / "test.tsv"
        test_file.write_text("name\tage\tcity\nJohn\t30\tNYC")

        result = read_csv(test_file, delimiter="\t")
        assert result[0] == {"name": "John", "age": "30", "city": "NYC"}

    def test_read_csv_empty_file_no_header(self, tmp_path):
        """Test reading empty CSV without header"""
        test_file = tmp_path / "empty.csv"
        test_file.write_text("")

        result = read_csv(test_file, has_header=False)
        assert result == []

    def test_read_csv_error(self, tmp_path):
        """Test error handling in read_csv"""
        with pytest.raises(FileNotFoundError):
            read_csv(tmp_path / "nonexistent.csv")


class TestReadYaml:
    """Tests for read_yaml function"""

    def test_read_yaml_basic(self, tmp_path):
        """Test reading YAML file"""
        pytest.importorskip("yaml")  # Skip if PyYAML not installed
        from axiompy.io.file import read_yaml

        test_file = tmp_path / "test.yaml"
        test_file.write_text("name: John\nage: 30\ncity: NYC")

        result = read_yaml(test_file)
        assert result == {"name": "John", "age": 30, "city": "NYC"}

    def test_read_yaml_file_not_found_raise(self, tmp_path):
        """Test reading non-existent YAML with raise_on_error"""
        pytest.importorskip("yaml")
        from axiompy.io.file import read_yaml

        with pytest.raises(FileNotFoundError):
            read_yaml(tmp_path / "nonexistent.yaml", raise_on_error=True)

    def test_read_yaml_file_not_found_no_raise(self, tmp_path):
        """Test reading non-existent YAML without raise_on_error"""
        pytest.importorskip("yaml")
        from axiompy.io.file import read_yaml

        result = read_yaml(tmp_path / "nonexistent.yaml", default={}, raise_on_error=False)
        assert result == {}

    def test_read_yaml_invalid_yaml_raise(self, tmp_path):
        """Test reading invalid YAML with raise_on_error"""
        pytest.importorskip("yaml")
        from axiompy.io.file import read_yaml

        test_file = tmp_path / "invalid.yaml"
        test_file.write_text("invalid: yaml: content: [")

        with pytest.raises(Exception):  # yaml.YAMLError
            read_yaml(test_file, raise_on_error=True)

    def test_read_yaml_invalid_yaml_no_raise(self, tmp_path):
        """Test reading invalid YAML without raise_on_error"""
        pytest.importorskip("yaml")
        from axiompy.io.file import read_yaml

        test_file = tmp_path / "invalid.yaml"
        test_file.write_text("invalid: yaml: content: [")

        result = read_yaml(test_file, default={"error": True}, raise_on_error=False)
        assert result == {"error": True}

    def test_read_yaml_general_error_no_raise(self, tmp_path):
        """Test general error handling in read_yaml"""
        pytest.importorskip("yaml")
        from axiompy.io.file import read_yaml

        test_file = tmp_path / "test.yaml"
        test_file.write_text("name: test")
        # Simulate error with invalid encoding
        result = read_yaml(
            test_file, encoding="invalid-encoding", default={"error": True}, raise_on_error=False
        )
        assert result == {"error": True}

    def test_read_yaml_general_error_with_raise(self, tmp_path):
        """Test general error handling in read_yaml with raise_on_error=True"""
        pytest.importorskip("yaml")
        from axiompy.io.file import read_yaml

        test_file = tmp_path / "test.yaml"
        test_file.write_text("name: test")
        # Simulate error with invalid encoding
        with pytest.raises(LookupError):  # Invalid encoding raises LookupError
            read_yaml(test_file, encoding="invalid-encoding", raise_on_error=True)

    def test_read_yaml_no_pyyaml(self, monkeypatch):
        """Test read_yaml when PyYAML is not installed"""
        # Mock the import to fail
        import axiompy.io.file as file_module

        # Save original value
        original_has_yaml = file_module.HAS_YAML

        # Set HAS_YAML to False
        monkeypatch.setattr(file_module, "HAS_YAML", False)

        from axiompy.io.file import read_yaml

        with pytest.raises(ImportError, match="PyYAML is required"):
            read_yaml("dummy.yaml")

        # Restore original value
        monkeypatch.setattr(file_module, "HAS_YAML", original_has_yaml)


class TestReadBinary:
    """Tests for read_binary function"""

    def test_read_binary_complete(self, tmp_path):
        """Test reading complete binary file"""
        test_file = tmp_path / "test.bin"
        data = b"\x00\x01\x02\x03\x04\x05"
        test_file.write_bytes(data)

        result = read_binary(test_file)
        assert result == data

    def test_read_binary_chunked(self, tmp_path):
        """Test reading binary file in chunks"""
        test_file = tmp_path / "test.bin"
        data = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09"
        test_file.write_bytes(data)

        chunks = list(read_binary(test_file, chunk_size=3))
        assert chunks == [b"\x00\x01\x02", b"\x03\x04\x05", b"\x06\x07\x08", b"\x09"]

    def test_read_binary_error(self, tmp_path):
        """Test error handling in read_binary"""
        with pytest.raises(FileNotFoundError):
            read_binary(tmp_path / "nonexistent.bin")


class TestSafeRead:
    """Tests for safe_read function"""

    def test_safe_read_success(self, tmp_path):
        """Test successful safe read"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = safe_read(test_file)
        assert result == "content"

    def test_safe_read_with_parser(self, tmp_path):
        """Test safe read with parser"""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"key": "value"}')

        result = safe_read(test_file, parser=json.loads)
        assert result == {"key": "value"}

    def test_safe_read_not_found_returns_default(self, tmp_path):
        """Test that safe_read returns default on error"""
        result = safe_read(tmp_path / "nonexistent.txt", default="default")
        assert result == "default"

    def test_safe_read_parser_error_returns_default(self, tmp_path):
        """Test that safe_read returns default on parser error"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("not a number")

        result = safe_read(test_file, parser=int, default=0)
        assert result == 0


class TestReadMultiple:
    """Tests for read_multiple function"""

    def test_read_multiple_success(self, tmp_path):
        """Test reading multiple files successfully"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")

        result = read_multiple([file1, file2])
        assert result[str(file1)] == "content 1"
        assert result[str(file2)] == "content 2"

    def test_read_multiple_with_errors_no_fail_fast(self, tmp_path):
        """Test reading multiple files with errors (no fail fast)"""
        file1 = tmp_path / "file1.txt"
        file1.write_text("content 1")

        result = read_multiple([file1, tmp_path / "nonexistent.txt"], fail_fast=False)
        assert str(file1) in result
        assert result[str(file1)] == "content 1"
        # Non-existent file should not be in results
        assert str(tmp_path / "nonexistent.txt") not in result

    def test_read_multiple_with_errors_fail_fast(self, tmp_path):
        """Test reading multiple files with errors (fail fast)"""
        file1 = tmp_path / "file1.txt"
        file1.write_text("content 1")

        with pytest.raises(FileNotFoundError):
            read_multiple([file1, tmp_path / "nonexistent.txt"], fail_fast=True)

    def test_read_multiple_with_custom_reader(self, tmp_path):
        """Test reading multiple files with custom reader function"""
        file1 = tmp_path / "file1.json"
        file2 = tmp_path / "file2.json"
        file1.write_text('{"a": 1}')
        file2.write_text('{"b": 2}')

        result = read_multiple([file1, file2], reader_func=read_json)
        assert result[str(file1)] == {"a": 1}
        assert result[str(file2)] == {"b": 2}


class TestReadWithPathExpansion:
    """Tests for read_with_path_expansion function"""

    def test_read_with_home_expansion(self, tmp_path, monkeypatch):
        """Test reading with ~ expansion"""
        # Create a test file in a known location
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Mock home directory
        monkeypatch.setenv("HOME", str(tmp_path))

        result = read_with_path_expansion("~/test.txt")
        assert result == "content"

    def test_read_with_env_var_expansion(self, tmp_path, monkeypatch):
        """Test reading with environment variable expansion"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        monkeypatch.setenv("TEST_DIR", str(tmp_path))

        result = read_with_path_expansion("$TEST_DIR/test.txt")
        assert result == "content"


class TestCachedReader:
    """Tests for CachedReader class"""

    def test_cached_reader_basic(self, tmp_path):
        """Test basic caching functionality"""
        reader = CachedReader()

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # First read - from disk
        result1 = reader.read(test_file)
        assert result1 == "content"

        # Modify file
        test_file.write_text("modified")

        # Second read - from cache (should be old content)
        result2 = reader.read(test_file)
        assert result2 == "content"

    def test_cached_reader_with_parser(self, tmp_path):
        """Test cached reader with parser"""
        reader = CachedReader()

        test_file = tmp_path / "test.json"
        test_file.write_text('{"key": "value"}')

        result = reader.read(test_file, parser=json.loads)
        assert result == {"key": "value"}

    def test_cached_reader_ttl(self, tmp_path):
        """Test cache expiration with TTL"""
        import time

        reader = CachedReader(ttl=1)  # 1 second TTL

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # First read
        result1 = reader.read(test_file)
        assert result1 == "content"

        # Modify file
        test_file.write_text("modified")

        # Wait for cache to expire
        time.sleep(1.1)

        # Second read - should get new content
        result2 = reader.read(test_file)
        assert result2 == "modified"

    def test_cached_reader_clear_cache(self, tmp_path):
        """Test clearing specific file from cache"""
        reader = CachedReader()

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # First read
        result1 = reader.read(test_file)
        assert result1 == "content"

        # Modify file
        test_file.write_text("modified")

        # Clear cache
        reader.clear_cache(test_file)

        # Second read - should get new content
        result2 = reader.read(test_file)
        assert result2 == "modified"

    def test_cached_reader_clear_all_cache(self, tmp_path):
        """Test clearing all cache entries"""
        import logging

        # Create a logger with DEBUG level to ensure debug statements are executed
        test_logger = logging.getLogger("test_cache_logger")
        test_logger.setLevel(logging.DEBUG)

        reader = CachedReader(logger=test_logger)

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")

        # Read both files
        reader.read(file1)
        reader.read(file2)

        # Clear all cache
        reader.clear_cache()  # No argument = clear all

        stats = reader.get_cache_stats()
        assert stats["num_entries"] == 0

    def test_cached_reader_stats(self, tmp_path):
        """Test cache statistics"""
        reader = CachedReader()

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")

        reader.read(file1)
        reader.read(file2)

        stats = reader.get_cache_stats()
        assert stats["num_entries"] == 2
        assert len(stats["files"]) == 2

    def test_cached_reader_clear_specific_file(self, tmp_path):
        """Test clearing cache for specific file"""
        reader = CachedReader()

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")

        reader.read(file1)
        reader.read(file2)

        # Clear only file1
        reader.clear_cache(file1)

        stats = reader.get_cache_stats()
        assert stats["num_entries"] == 1
        assert str(file2.absolute()) in stats["files"]
        assert str(file1.absolute()) not in stats["files"]

    def test_cached_reader_clear_nonexistent_file(self, tmp_path):
        """Test clearing cache for file that was never cached"""
        reader = CachedReader()

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content 1")

        reader.read(file1)

        # Try to clear file2 which was never read
        reader.clear_cache(file2)  # Should not raise error

        stats = reader.get_cache_stats()
        assert stats["num_entries"] == 1  # Still has file1
