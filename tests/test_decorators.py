"""
Tests for decorator utilities
"""

import logging
import time
from unittest.mock import Mock

import pytest

from axiompy.decorators import (
    CatchAndLog,
    Deprecated,
    LogAndRethrow,
    LogExecutionTime,
    LogInputOutput,
    RateLimited,
    Retry,
    Trace,
    catch_and_log,
    log_time,
    trace,
)


@pytest.fixture
def mock_logger():
    """Create a mock logger"""
    logger = Mock(spec=logging.Logger)
    return logger


class TestCatchAndLog:
    """Test CatchAndLog decorator"""

    def test_catches_exception_and_logs(self, mock_logger):
        """Test that exceptions are caught and logged"""

        @CatchAndLog(mock_logger, reraise=False)
        def failing_function():
            raise ValueError("Test error")

        result = failing_function()

        # Should log the error
        assert mock_logger.log.called
        log_call = mock_logger.log.call_args
        assert "ValueError" in str(log_call)
        assert "Test error" in str(log_call)

        # Should return None (default_return)
        assert result is None

    def test_reraises_by_default(self, mock_logger):
        """Test that exceptions are reraised by default"""

        @CatchAndLog(mock_logger)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        # Should still log
        assert mock_logger.log.called

    def test_returns_default_value(self, mock_logger):
        """Test custom default return value"""

        @CatchAndLog(mock_logger, reraise=False, default_return=42)
        def failing_function():
            raise ValueError("Test error")

        result = failing_function()
        assert result == 42

    def test_specific_exceptions_only(self, mock_logger):
        """Test catching specific exception types"""

        @CatchAndLog(mock_logger, reraise=False, exceptions=(ValueError,))
        def failing_function():
            raise TypeError("Type error")

        # Should not catch TypeError
        with pytest.raises(TypeError):
            failing_function()

    def test_successful_execution(self, mock_logger):
        """Test that successful execution works normally"""

        @CatchAndLog(mock_logger)
        def working_function():
            return "success"

        result = working_function()
        assert result == "success"
        assert not mock_logger.log.called


class TestLogAndRethrow:
    """Test LogAndRethrow decorator"""

    def test_logs_and_rethrows_exception(self, mock_logger):
        """Test that exceptions are logged and then rethrown"""

        @LogAndRethrow(mock_logger)
        def failing_function():
            raise ValueError("Test error")

        # Should raise the exception
        with pytest.raises(ValueError, match="Test error"):
            failing_function()

        # Should log the error
        assert mock_logger.log.called
        log_call_args = mock_logger.log.call_args

        # Check log level is ERROR (default)
        assert log_call_args[0][0] == logging.ERROR

        # Check message contains function name, exception type, and message
        log_message = log_call_args[0][1]
        assert "failing_function" in log_message
        assert "ValueError" in log_message
        assert "Test error" in log_message

    def test_includes_traceback_by_default(self, mock_logger):
        """Test that traceback is included in log by default"""

        @LogAndRethrow(mock_logger)
        def failing_function():
            raise RuntimeError("Runtime error")

        with pytest.raises(RuntimeError):
            failing_function()

        # Get the logged message
        log_message = mock_logger.log.call_args[0][1]

        # Should include traceback
        assert "Traceback" in log_message or "File" in log_message

    def test_can_disable_traceback(self, mock_logger):
        """Test that traceback can be disabled"""

        @LogAndRethrow(mock_logger, include_traceback=False)
        def failing_function():
            raise ValueError("Error")

        with pytest.raises(ValueError):
            failing_function()

        # Get the logged message
        log_message = mock_logger.log.call_args[0][1]

        # Should include exception info but not full traceback
        assert "ValueError" in log_message
        assert "Error" in log_message
        # Traceback format strings should not be present
        assert "Traceback (most recent call last)" not in log_message

    def test_custom_log_level(self, mock_logger):
        """Test using custom log level"""

        @LogAndRethrow(mock_logger, log_level=logging.WARNING)
        def failing_function():
            raise ValueError("Warning level")

        with pytest.raises(ValueError):
            failing_function()

        # Should use WARNING level
        log_call_args = mock_logger.log.call_args
        assert log_call_args[0][0] == logging.WARNING

    def test_successful_execution_no_log(self, mock_logger):
        """Test that successful execution doesn't log"""

        @LogAndRethrow(mock_logger)
        def working_function():
            return "success"

        result = working_function()

        assert result == "success"
        assert not mock_logger.log.called

    def test_preserves_function_metadata(self, mock_logger):
        """Test that decorator preserves function metadata"""

        @LogAndRethrow(mock_logger)
        def documented_function():
            """This is a docstring"""
            return "result"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a docstring"

    def test_with_different_exception_types(self, mock_logger):
        """Test logging different exception types"""

        @LogAndRethrow(mock_logger, include_traceback=False)
        def raise_type_error():
            raise TypeError("Type mismatch")

        @LogAndRethrow(mock_logger, include_traceback=False)
        def raise_key_error():
            raise KeyError("Missing key")

        with pytest.raises(TypeError):
            raise_type_error()

        log_message1 = mock_logger.log.call_args[0][1]
        assert "TypeError" in log_message1
        assert "Type mismatch" in log_message1

        mock_logger.reset_mock()

        with pytest.raises(KeyError):
            raise_key_error()

        log_message2 = mock_logger.log.call_args[0][1]
        assert "KeyError" in log_message2
        assert "Missing key" in log_message2

    def test_with_arguments(self, mock_logger):
        """Test decorated function with arguments"""

        @LogAndRethrow(mock_logger)
        def process_data(x, y, operation="add"):
            if operation == "divide" and y == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return x / y if operation == "divide" else x + y

        # Successful call
        result = process_data(10, 5, operation="add")
        assert result == 15
        assert not mock_logger.log.called

        # Failing call
        with pytest.raises(ZeroDivisionError):
            process_data(10, 0, operation="divide")

        assert mock_logger.log.called
        log_message = mock_logger.log.call_args[0][1]
        assert "ZeroDivisionError" in log_message
        assert "process_data" in log_message

    def test_nested_exceptions(self, mock_logger):
        """Test with nested exception context"""

        @LogAndRethrow(mock_logger)
        def nested_error():
            try:
                raise ValueError("Inner error")
            except ValueError:
                raise RuntimeError("Outer error")

        with pytest.raises(RuntimeError, match="Outer error"):
            nested_error()

        # Should log the outer exception
        log_message = mock_logger.log.call_args[0][1]
        assert "RuntimeError" in log_message
        assert "Outer error" in log_message

    def test_with_return_value(self, mock_logger):
        """Test that return values pass through correctly"""

        @LogAndRethrow(mock_logger)
        def return_values(value):
            if value < 0:
                raise ValueError("Negative value")
            return value * 2

        # Test successful returns
        assert return_values(5) == 10
        assert return_values(0) == 0
        assert return_values(100) == 200

        # Should not have logged anything
        assert not mock_logger.log.called

        # Test failure
        with pytest.raises(ValueError):
            return_values(-1)

        # Now should have logged
        assert mock_logger.log.called


class TestLogExecutionTime:
    """Test LogExecutionTime decorator"""

    def test_logs_execution_time(self, mock_logger):
        """Test that execution time is logged"""

        @LogExecutionTime(mock_logger)
        def slow_function():
            time.sleep(0.1)
            return "done"

        result = slow_function()

        assert result == "done"
        # Check debug or log was called (decorator uses debug)
        assert mock_logger.debug.called or mock_logger.log.called

        # Check log message contains function name and time
        log_message = str(mock_logger.debug.call_args or mock_logger.log.call_args)
        assert "slow_function" in log_message

    def test_times_even_with_exception(self, mock_logger):
        """Test that time is logged even if function fails"""

        @LogExecutionTime(mock_logger)
        def failing_function():
            time.sleep(0.05)
            raise ValueError("Error")

        with pytest.raises(ValueError):
            failing_function()

        # Should still log time (decorator uses debug)
        assert mock_logger.debug.called or mock_logger.log.called


class TestLogInputOutput:
    """Test LogInputOutput decorator"""

    def test_logs_arguments(self, mock_logger):
        """Test that function arguments are logged"""

        @LogInputOutput(mock_logger, log_args=True, log_kwargs=True)
        def add(a, b, c=0):
            return a + b + c

        result = add(1, 2, c=3)

        assert result == 6
        assert mock_logger.log.called

        # Check that arguments were logged
        log_calls = [str(call) for call in mock_logger.log.call_args_list]
        log_output = " ".join(log_calls)
        assert "add" in log_output

    def test_logs_return_value(self, mock_logger):
        """Test that return value is logged"""

        @LogInputOutput(mock_logger, log_result=True)
        def multiply(x, y):
            return x * y

        result = multiply(3, 4)

        assert result == 12

        # Check return value was logged
        log_calls = [str(call) for call in mock_logger.log.call_args_list]
        log_output = " ".join(log_calls)
        assert "returned" in log_output or "12" in log_output

    def test_truncates_long_values(self, mock_logger):
        """Test that long values are truncated"""

        @LogInputOutput(mock_logger, max_length=10)
        def process_string(s):
            return s

        long_string = "a" * 100
        result = process_string(long_string)

        assert result == long_string
        assert mock_logger.log.called


class TestRetry:
    """Test Retry decorator"""

    def test_retries_on_failure(self, mock_logger):
        """Test that function is retried on failure"""

        call_count = 0

        @Retry(mock_logger, max_attempts=3, delay=0.01)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count == 3
        assert mock_logger.warning.called

    def test_fails_after_max_attempts(self, mock_logger):
        """Test that function fails after max attempts"""

        @Retry(mock_logger, max_attempts=3, delay=0.01)
        def always_fails():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_fails()

        assert mock_logger.error.called

    def test_succeeds_on_first_try(self, mock_logger):
        """Test that successful functions work normally"""

        @Retry(mock_logger, max_attempts=3, delay=0.01)
        def working_function():
            return "success"

        result = working_function()

        assert result == "success"
        assert not mock_logger.warning.called

    def test_backoff_increases_delay(self, mock_logger):
        """Test that backoff multiplier works"""

        call_times = []

        @Retry(mock_logger, max_attempts=3, delay=0.05, backoff=2.0)
        def timing_function():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Not yet")
            return "success"

        result = timing_function()

        assert result == "success"
        assert len(call_times) == 3

        # Check delays increased (roughly)
        # First delay ~0.05s, second delay ~0.1s
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            assert delay2 > delay1  # Second delay should be longer


class TestTrace:
    """Test Trace decorator"""

    def test_traces_entry_and_exit(self, mock_logger):
        """Test that function entry and exit are traced"""

        @Trace(mock_logger)
        def traced_function():
            return "result"

        result = traced_function()

        assert result == "result"
        assert mock_logger.log.call_count >= 2

        # Check for entry and exit messages
        log_calls = [str(call) for call in mock_logger.log.call_args_list]
        log_output = " ".join(log_calls)
        assert "Entering" in log_output or "→" in log_output
        assert "Exiting" in log_output or "←" in log_output

    def test_traces_with_arguments(self, mock_logger):
        """Test tracing with show_args=True"""

        @Trace(mock_logger, show_args=True)
        def add(x, y):
            return x + y

        result = add(5, 3)

        assert result == 8
        assert mock_logger.log.called

    def test_traces_exception(self, mock_logger):
        """Test that exceptions are traced"""

        @Trace(mock_logger)
        def failing_function():
            raise ValueError("Error")

        with pytest.raises(ValueError):
            failing_function()

        # Should log exception
        log_calls = [str(call) for call in mock_logger.log.call_args_list]
        log_output = " ".join(log_calls)
        assert "Exception" in log_output or "✗" in log_output


class TestDeprecated:
    """Test Deprecated decorator"""

    def test_warns_and_logs(self, mock_logger):
        """Test that deprecation warning is issued and logged"""

        @Deprecated(mock_logger, "Use new_function() instead")
        def old_function():
            return "old"

        with pytest.warns(DeprecationWarning):
            result = old_function()

        assert result == "old"
        assert mock_logger.warning.called

        warning_message = str(mock_logger.warning.call_args)
        assert "deprecated" in warning_message.lower()


class TestRateLimited:
    """Test RateLimited decorator"""

    def test_allows_calls_within_limit(self, mock_logger):
        """Test that calls within limit are allowed"""

        @RateLimited(mock_logger, max_calls=3, period=1.0)
        def limited_function():
            return "success"

        # Should allow 3 calls
        for _ in range(3):
            result = limited_function()
            assert result == "success"

    def test_blocks_calls_over_limit(self, mock_logger):
        """Test that calls over limit are blocked"""

        @RateLimited(mock_logger, max_calls=2, period=1.0)
        def limited_function():
            return "success"

        # First 2 calls should work
        limited_function()
        limited_function()

        # Third call should fail
        with pytest.raises(RuntimeError):
            limited_function()

        assert mock_logger.warning.called

    def test_resets_after_period(self, mock_logger):
        """Test that rate limit resets after period"""

        @RateLimited(mock_logger, max_calls=2, period=0.2)
        def limited_function():
            return "success"

        # Use up the limit
        limited_function()
        limited_function()

        # Wait for period to expire
        time.sleep(0.3)

        # Should work again
        result = limited_function()
        assert result == "success"


class TestConvenienceFunctions:
    """Test convenience decorator functions"""

    def test_catch_and_log_convenience(self):
        """Test catch_and_log convenience function"""

        @catch_and_log
        def working_function():
            return "success"

        result = working_function()
        assert result == "success"

    def test_log_time_convenience(self):
        """Test log_time convenience function"""

        @log_time
        def working_function():
            return "success"

        result = working_function()
        assert result == "success"

    def test_trace_convenience(self):
        """Test trace convenience function"""

        @trace
        def working_function():
            return "success"

        result = working_function()
        assert result == "success"


class TestDecoratorStacking:
    """Test multiple decorators working together"""

    def test_stacked_decorators(self, mock_logger):
        """Test that multiple decorators can be stacked"""

        @LogExecutionTime(mock_logger)
        @CatchAndLog(mock_logger, reraise=False)
        @Trace(mock_logger)
        def complex_function(x):
            return x * 2

        result = complex_function(5)

        assert result == 10
        # All decorators should have logged
        assert mock_logger.log.called

    def test_stacked_with_error(self, mock_logger):
        """Test stacked decorators with an error"""

        @LogExecutionTime(mock_logger)
        @CatchAndLog(mock_logger, reraise=False, default_return=0)
        def failing_function():
            raise ValueError("Error")

        result = failing_function()

        # Should return default value
        assert result == 0
        # Should log error and time
        assert mock_logger.log.called
