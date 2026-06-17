# @!testing

"""
Unit tests for the loggers module.

Run with: pytest tests/test_loggers.py -v
"""

import logging
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from axiompy.loggers import (
    TQDM_AVAILABLE,
    BaseLogHandler,
    ConsoleLogHandler,
    FileLogHandler,
    LoggerFactory,
    SplunkLogHandler,
    TqdmLoggingHandler,
    TqdmLogHandler,
)


class TestBaseLogHandler:
    """Test BaseLogHandler abstract class"""

    def test_cannot_instantiate_abstract_class(self):
        """Should not be able to instantiate abstract base class"""
        with pytest.raises(TypeError):
            BaseLogHandler()

    def test_subclass_must_implement_create_handler(self):
        """Subclass must implement create_handler method"""

        class IncompleteHandler(BaseLogHandler):
            pass

        with pytest.raises(TypeError):
            IncompleteHandler()

    def test_get_extra_format_with_no_extra(self):
        """Should return empty string when no extra fields"""

        class TestHandler(BaseLogHandler):
            def create_handler(self):
                return Mock()

        handler = TestHandler()
        result = handler._get_extra_format(None)
        assert result == ""

        result = handler._get_extra_format({})
        assert result == ""

    def test_get_extra_format_with_extra_fields(self):
        """Should format extra fields correctly"""

        class TestHandler(BaseLogHandler):
            def create_handler(self):
                return Mock()

        handler = TestHandler()
        extra = {"service": "api", "env": "prod"}
        result = handler._get_extra_format(extra)

        assert "service: %(service)s" in result
        assert "env: %(env)s" in result
        assert result.startswith(" - ")

    def test_set_handler_properties_adds_formatter(self):
        """Should add formatter to handler"""

        class TestHandler(BaseLogHandler):
            def create_handler(self):
                return Mock()

        handler_instance = TestHandler()
        mock_handler = Mock()
        mock_logger = Mock()
        mock_logger.handlers = []

        handler_instance.set_handler_properties(mock_handler, mock_logger, None)

        # Verify formatter was set
        assert mock_handler.setFormatter.called

    def test_set_handler_properties_adds_handler_to_logger(self):
        """Should add handler to logger"""

        class TestHandler(BaseLogHandler):
            def create_handler(self):
                return Mock()

        handler_instance = TestHandler()
        mock_handler = Mock()
        mock_logger = Mock()
        mock_logger.handlers = []

        handler_instance.set_handler_properties(mock_handler, mock_logger, None)

        # Verify handler was added to logger
        mock_logger.addHandler.assert_called_once_with(mock_handler)

    def test_set_handler_properties_prevents_duplicate_handlers(self):
        """Should not add duplicate handler types"""

        class TestHandler(BaseLogHandler):
            def create_handler(self):
                return Mock()

        handler_instance = TestHandler()
        # Use actual handler instances instead of mocks for isinstance check
        mock_handler = logging.StreamHandler()
        existing_handler = logging.StreamHandler()
        mock_logger = Mock()
        mock_logger.handlers = [existing_handler]

        handler_instance.set_handler_properties(mock_handler, mock_logger, None)

        # Should not add handler since same type already exists
        assert not mock_logger.addHandler.called


class TestConsoleLogHandler:
    """Test ConsoleLogHandler class"""

    def test_create_handler_returns_stream_handler(self):
        """Should create a StreamHandler"""
        handler_creator = ConsoleLogHandler()
        handler = handler_creator.create_handler()

        assert isinstance(handler, logging.StreamHandler)

    def test_create_handler_uses_stdout(self):
        """Should use sys.stdout for output"""
        handler_creator = ConsoleLogHandler()
        handler = handler_creator.create_handler()

        import sys

        assert handler.stream == sys.stdout


class TestFileLogHandler:
    """Test FileLogHandler class"""

    def test_init_stores_file_path(self):
        """Should store file path on initialization"""
        file_path = "/tmp/test.log"
        handler_creator = FileLogHandler(file_path)

        assert handler_creator.file_path == file_path

    def test_create_handler_returns_file_handler(self):
        """Should create a FileHandler"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            handler_creator = FileLogHandler(tmp_path)
            handler = handler_creator.create_handler()

            assert isinstance(handler, logging.FileHandler)
            assert handler.baseFilename == tmp_path

            handler.close()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_create_handler_creates_file(self):
        """Should create log file if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.log")
            handler_creator = FileLogHandler(file_path)
            handler = handler_creator.create_handler()

            assert os.path.exists(file_path)
            handler.close()


class TestSplunkLogHandler:
    """Test SplunkLogHandler class"""

    def test_create_handler_returns_none(self):
        """Should return None (not implemented)"""
        handler_creator = SplunkLogHandler()
        handler = handler_creator.create_handler()

        assert handler is None


class TestLoggerFactory:
    """Test LoggerFactory class"""

    def test_create_logger_returns_logger_adapter(self):
        """Should return a LoggerAdapter instance"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            logger = LoggerFactory.create_logger("test_logger", settings=settings)

            assert isinstance(logger, logging.LoggerAdapter)

    def test_create_logger_with_default_level(self):
        """Should use DEBUG level by default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            logger = LoggerFactory.create_logger("test_logger", settings=settings)

            assert logger.logger.level == logging.DEBUG

    def test_create_logger_with_custom_level(self):
        """Should use specified log level"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            logger = LoggerFactory.create_logger(
                "test_logger", level=logging.INFO, settings=settings
            )

            assert logger.logger.level == logging.INFO

    def test_create_logger_without_file_path_is_console_only(self):
        """Should not create a file handler when no file_path is provided"""
        logger_name = "test_no_file_path"

        # Clean up any existing logger
        if logger_name in logging.Logger.manager.loggerDict:
            del logging.Logger.manager.loggerDict[logger_name]

        logger = LoggerFactory.create_logger(logger_name)

        file_handlers = [h for h in logger.logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 0

        # Clean up
        for handler in logger.logger.handlers[:]:
            handler.close()
            logger.logger.removeHandler(handler)

    def test_create_logger_creates_log_directory(self):
        """Should create log directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "nested", "dir", "test.log")
            settings = {"file_path": log_path}

            logger = LoggerFactory.create_logger("test_logger", settings=settings)

            assert os.path.exists(os.path.dirname(log_path))

            # Clean up
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_create_logger_with_custom_file_path(self):
        """Should use custom file path when provided"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = os.path.join(tmpdir, "custom.log")
            settings = {"file_path": custom_path}

            logger = LoggerFactory.create_logger("test_logger", settings=settings)

            file_handlers = [
                h for h in logger.logger.handlers if isinstance(h, logging.FileHandler)
            ]
            assert len(file_handlers) == 1
            assert file_handlers[0].baseFilename == custom_path

            # Clean up
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_create_logger_with_extra_fields(self):
        """Should include extra fields in logger adapter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {
                "file_path": os.path.join(tmpdir, "test.log"),
                "extra": {"service": "api", "env": "prod"},
            }

            logger = LoggerFactory.create_logger("test_logger", settings=settings)

            assert logger.extra == {"service": "api", "env": "prod"}

            # Clean up
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_create_logger_adds_console_handler(self):
        """Should add console handler by default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            logger = LoggerFactory.create_logger("test_logger", settings=settings)

            stream_handlers = [
                h for h in logger.logger.handlers if isinstance(h, logging.StreamHandler)
            ]
            # Should have at least one StreamHandler (console)
            assert len(stream_handlers) >= 1

            # Clean up
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_create_logger_adds_file_handler(self):
        """Should add file handler"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            logger = LoggerFactory.create_logger("test_logger", settings=settings)

            file_handlers = [
                h for h in logger.logger.handlers if isinstance(h, logging.FileHandler)
            ]
            assert len(file_handlers) == 1

            # Clean up
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_create_logger_disables_propagation(self):
        """Should disable log propagation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            logger = LoggerFactory.create_logger("test_logger", settings=settings)

            assert logger.logger.propagate is False

            # Clean up
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_logger_can_write_messages(self):
        """Should be able to write log messages"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            settings = {"file_path": log_path}

            logger = LoggerFactory.create_logger(
                "test_logger", level=logging.INFO, settings=settings
            )

            logger.info("Test message")
            logger.warning("Warning message")
            logger.error("Error message")

            # Clean up and flush handlers
            for handler in logger.logger.handlers[:]:
                handler.flush()
                handler.close()
                logger.logger.removeHandler(handler)

            # Verify log file was created and has content
            assert os.path.exists(log_path)
            with open(log_path) as f:
                content = f.read()
                assert "Test message" in content
                assert "Warning message" in content
                assert "Error message" in content

    def test_logger_with_extra_fields_in_output(self):
        """Should include extra fields in log output"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            settings = {
                "file_path": log_path,
                "extra": {"service": "test-service", "env": "testing"},
            }

            logger = LoggerFactory.create_logger(
                "test_logger", level=logging.INFO, settings=settings
            )

            logger.info("Test with extra fields")

            # Clean up and flush handlers
            for handler in logger.logger.handlers[:]:
                handler.flush()
                handler.close()
                logger.logger.removeHandler(handler)

            # Verify extra fields are in log output
            with open(log_path) as f:
                content = f.read()
                assert "service: test-service" in content
                assert "env: testing" in content

    def test_multiple_loggers_are_independent(self):
        """Should create independent loggers"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings1 = {"file_path": os.path.join(tmpdir, "logger1.log")}
            settings2 = {"file_path": os.path.join(tmpdir, "logger2.log")}

            logger1 = LoggerFactory.create_logger("logger1", settings=settings1)
            logger2 = LoggerFactory.create_logger("logger2", settings=settings2)

            assert logger1.logger.name == "logger1"
            assert logger2.logger.name == "logger2"
            assert logger1.logger is not logger2.logger

            # Clean up
            for logger in [logger1, logger2]:
                for handler in logger.logger.handlers[:]:
                    handler.close()
                    logger.logger.removeHandler(handler)


class TestLoggerIntegration:
    """Integration tests for the logger system"""

    def test_end_to_end_logging_workflow(self):
        """Test complete logging workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "integration.log")
            settings = {
                "file_path": log_path,
                "extra": {"service_name": "integration_test", "version": "1.0"},
            }

            # Create logger
            logger = LoggerFactory.create_logger(
                "integration_test", level=logging.DEBUG, settings=settings
            )

            # Log various levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")

            # Flush and close handlers
            for handler in logger.logger.handlers[:]:
                handler.flush()
                handler.close()
                logger.logger.removeHandler(handler)

            # Verify all messages in log file
            with open(log_path) as f:
                content = f.read()
                assert "DEBUG" in content
                assert "INFO" in content
                assert "WARNING" in content
                assert "ERROR" in content
                assert "CRITICAL" in content
                assert "service_name: integration_test" in content
                assert "version: 1.0" in content


class TestTqdmLoggingHandler:
    """Tests for the TqdmLoggingHandler class."""

    def test_handler_creation(self):
        """Test that TqdmLoggingHandler can be instantiated."""
        handler = TqdmLoggingHandler()
        assert isinstance(handler, logging.Handler)

    @patch("axiompy.loggers.TQDM_AVAILABLE", True)
    @patch("axiompy.loggers.tqdm", create=True)
    def test_emit_with_tqdm_available(self, mock_tqdm):
        """Test that emit uses tqdm.write when tqdm is available."""
        handler = TqdmLoggingHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)
        mock_tqdm.write.assert_called_once()

        # Check that the message was passed correctly
        call_args = mock_tqdm.write.call_args
        assert "Test message" in call_args[0][0]

    @patch("axiompy.loggers.TQDM_AVAILABLE", False)
    @patch("builtins.print")
    def test_emit_without_tqdm_fallback(self, mock_print):
        """Test that emit falls back to print when tqdm is not available."""
        handler = TqdmLoggingHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)
        mock_print.assert_called_once()

        # Check that the message was passed correctly
        call_args = mock_print.call_args
        assert "Test message" in call_args[0][0]


class TestTqdmLogHandler:
    """Tests for the TqdmLogHandler creator class."""

    def test_create_handler(self):
        """Test that TqdmLogHandler creates a TqdmLoggingHandler."""
        creator = TqdmLogHandler()
        handler = creator.create_handler()

        assert handler is not None
        assert isinstance(handler, TqdmLoggingHandler)


class TestLoggerFactoryWithTqdm:
    """Tests for LoggerFactory with tqdm support."""

    def test_create_logger_with_tqdm_enabled(self):
        """Test creating a logger with use_tqdm=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            logger = LoggerFactory.create_logger(
                "test_tqdm_logger", use_tqdm=True, settings=settings
            )

            assert logger is not None
            assert isinstance(logger, logging.LoggerAdapter)

            # Clean up
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_create_logger_with_tqdm_disabled(self):
        """Test creating a logger with use_tqdm=False (default)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            logger = LoggerFactory.create_logger(
                "test_regular_logger", use_tqdm=False, settings=settings
            )

            assert logger is not None
            assert isinstance(logger, logging.LoggerAdapter)

            # Clean up
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_logger_has_tqdm_handler(self):
        """Test that logger created with use_tqdm=True has TqdmLoggingHandler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            logger_adapter = LoggerFactory.create_logger(
                "test_has_tqdm", use_tqdm=True, settings=settings
            )

            logger = logger_adapter.logger

            # Check if any handler is a TqdmLoggingHandler
            has_tqdm_handler = any(isinstance(h, TqdmLoggingHandler) for h in logger.handlers)
            assert has_tqdm_handler, "Logger should have a TqdmLoggingHandler"

            # Clean up
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

    def test_logger_without_tqdm_handler(self):
        """Test that logger created with use_tqdm=False doesn't have TqdmLoggingHandler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            logger_adapter = LoggerFactory.create_logger(
                "test_no_tqdm", use_tqdm=False, settings=settings
            )

            logger = logger_adapter.logger

            # Check that no handler is a TqdmLoggingHandler
            has_tqdm_handler = any(isinstance(h, TqdmLoggingHandler) for h in logger.handlers)
            assert not has_tqdm_handler, "Logger should not have a TqdmLoggingHandler"

            # Clean up
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

    @patch("axiompy.loggers.TQDM_AVAILABLE", True)
    @patch("axiompy.loggers.tqdm", create=True)
    def test_logger_logs_through_tqdm(self, mock_tqdm):
        """Test that logging actually goes through tqdm.write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            logger = LoggerFactory.create_logger(
                "test_log_through_tqdm", use_tqdm=True, level=logging.INFO, settings=settings
            )

            # Log a message
            logger.info("Test tqdm logging")

            # Verify tqdm.write was called
            mock_tqdm.write.assert_called()

            # Check that the log message contains our text
            calls = mock_tqdm.write.call_args_list
            logged_messages = [call[0][0] for call in calls]
            assert any("Test tqdm logging" in msg for msg in logged_messages)

            # Clean up
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_logger_with_tqdm_and_extra_fields(self):
        """Test that tqdm logger works with extra context fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = LoggerFactory.create_logger(
                "test_tqdm_extra",
                use_tqdm=True,
                settings={
                    "file_path": os.path.join(tmpdir, "test.log"),
                    "extra": {"service": "test", "env": "dev"},
                },
            )

            assert logger is not None
            assert logger.extra["service"] == "test"
            assert logger.extra["env"] == "dev"

            # Clean up
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_multiple_loggers_with_different_tqdm_settings(self):
        """Test creating multiple loggers with different tqdm settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings1 = {"file_path": os.path.join(tmpdir, "logger1.log")}
            settings2 = {"file_path": os.path.join(tmpdir, "logger2.log")}

            logger1 = LoggerFactory.create_logger("logger1", use_tqdm=True, settings=settings1)
            logger2 = LoggerFactory.create_logger("logger2", use_tqdm=False, settings=settings2)

            # Check logger1 has TqdmLoggingHandler
            has_tqdm1 = any(isinstance(h, TqdmLoggingHandler) for h in logger1.logger.handlers)
            assert has_tqdm1

            # Check logger2 doesn't have TqdmLoggingHandler
            has_tqdm2 = any(isinstance(h, TqdmLoggingHandler) for h in logger2.logger.handlers)
            assert not has_tqdm2

            # Clean up
            for logger in [logger1, logger2]:
                for handler in logger.logger.handlers[:]:
                    handler.close()
                    logger.logger.removeHandler(handler)


class TestTqdmAvailability:
    """Tests for tqdm availability detection."""

    def test_tqdm_availability_flag(self):
        """Test that TQDM_AVAILABLE is a boolean."""
        assert isinstance(TQDM_AVAILABLE, bool)

    @pytest.mark.skipif(not TQDM_AVAILABLE, reason="tqdm not installed")
    def test_tqdm_import_when_available(self):
        """Test that tqdm can be imported when available."""
        from axiompy.loggers import tqdm

        assert tqdm is not None

    def test_logger_works_without_tqdm(self):
        """Test that logger creation works even when tqdm is not available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = {"file_path": os.path.join(tmpdir, "test.log")}
            # This should not raise an exception
            logger = LoggerFactory.create_logger(
                "test_no_tqdm_installed",
                use_tqdm=True,  # Even with use_tqdm=True, it should work
                settings=settings,
            )
            assert logger is not None

            # Clean up
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
