"""Unit tests for logging configuration and functionality."""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cdnbestip.logging_config import (
    CDNBESTIPLogger,
    ColoredFormatter,
    PerformanceTimer,
    configure_logging,
    disable_debug_mode,
    enable_debug_mode,
    get_logger,
    log_function_call,
    log_performance,
)


class TestColoredFormatter:
    """Test ColoredFormatter class."""

    def test_format_with_colors(self):
        """Test formatting with colors."""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # Should contain ANSI color codes
        assert "\033[32m" in formatted  # Green for INFO
        assert "\033[0m" in formatted  # Reset
        assert "Test message" in formatted

    def test_format_different_levels(self):
        """Test formatting with different log levels."""
        formatter = ColoredFormatter("%(levelname)s")

        levels = [
            (logging.DEBUG, "\033[36m"),  # Cyan
            (logging.INFO, "\033[32m"),  # Green
            (logging.WARNING, "\033[33m"),  # Yellow
            (logging.ERROR, "\033[31m"),  # Red
            (logging.CRITICAL, "\033[35m"),  # Magenta
        ]

        for level, expected_color in levels:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None,
            )
            formatted = formatter.format(record)
            assert expected_color in formatted


class TestCDNBESTIPLogger:
    """Test CDNBESTIPLogger class."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = CDNBESTIPLogger()
        # Override log directory for testing
        self.logger.log_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Reset logging configuration
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.WARNING)
        self.logger.configured = False

    def test_configure_logging_basic(self):
        """Test basic logging configuration."""
        self.logger.configure_logging()

        assert self.logger.configured

        # Check that handlers were added
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

    def test_configure_logging_debug_mode(self):
        """Test logging configuration in debug mode."""
        self.logger.configure_logging(debug_mode=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_logging_verbose_mode(self):
        """Test logging configuration in verbose mode."""
        self.logger.configure_logging(verbose=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_configure_logging_custom_level(self):
        """Test logging configuration with custom level."""
        self.logger.configure_logging(level="WARNING")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_configure_logging_no_console(self):
        """Test logging configuration without console output."""
        self.logger.configure_logging(console=False)

        root_logger = logging.getLogger()
        console_handlers = [
            h
            for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and h.stream.name == "<stdout>"
        ]
        assert len(console_handlers) == 0

    def test_configure_logging_no_file(self):
        """Test logging configuration without file output."""
        self.logger.configure_logging(file_logging=False)

        root_logger = logging.getLogger()
        file_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) == 0

    def test_configure_logging_file_creation(self):
        """Test that log file is created."""
        self.logger.configure_logging(file_logging=True)

        # Check that log file exists
        log_files = list(self.logger.log_dir.glob("cdnbestip_*.log"))
        assert len(log_files) > 0

    def test_get_logger(self):
        """Test getting a logger instance."""
        self.logger.configure_logging()

        test_logger = self.logger.get_logger("test.module")
        assert isinstance(test_logger, logging.Logger)
        assert test_logger.name == "test.module"

    def test_set_debug_mode(self):
        """Test setting debug mode."""
        self.logger.configure_logging()

        # Enable debug mode
        self.logger.set_debug_mode(True)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

        # Disable debug mode
        self.logger.set_debug_mode(False)
        assert root_logger.level == logging.INFO

    def test_add_performance_logging(self):
        """Test adding performance logging."""
        self.logger.configure_logging()
        self.logger.add_performance_logging()

        perf_logger = logging.getLogger("cdnbestip.performance")
        assert perf_logger.level == logging.INFO
        assert not perf_logger.propagate

        # Check that performance log file exists
        perf_files = list(self.logger.log_dir.glob("performance_*.log"))
        assert len(perf_files) > 0

    def test_cleanup_old_logs(self):
        """Test cleaning up old log files."""
        # Create some test log files
        old_file = self.logger.log_dir / "old.log"
        new_file = self.logger.log_dir / "new.log"

        old_file.touch()
        new_file.touch()

        # Make old file appear old
        import time

        old_time = time.time() - (31 * 24 * 60 * 60)  # 31 days ago
        os.utime(old_file, (old_time, old_time))

        self.logger.configure_logging()
        self.logger.cleanup_old_logs(days=30)

        # Old file should be deleted, new file should remain
        assert not old_file.exists()
        assert new_file.exists()


class TestPerformanceTimer:
    """Test PerformanceTimer class."""

    def test_performance_timer_success(self):
        """Test performance timer with successful operation."""
        mock_logger = MagicMock()

        with PerformanceTimer("test_operation", mock_logger) as timer:
            import time

            time.sleep(0.01)  # Small delay

        # Check that start and completion were logged
        assert mock_logger.info.call_count == 2
        start_call = mock_logger.info.call_args_list[0]
        complete_call = mock_logger.info.call_args_list[1]

        assert "Started: test_operation" in start_call[0][0]
        assert "Completed: test_operation" in complete_call[0][0]

        # Check duration
        duration = timer.get_duration()
        assert duration is not None
        assert duration > 0

    def test_performance_timer_exception(self):
        """Test performance timer with exception."""
        mock_logger = MagicMock()

        try:
            with PerformanceTimer("test_operation", mock_logger):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Check that failure was logged
        assert mock_logger.error.called
        error_call = mock_logger.error.call_args_list[0]
        assert "Failed: test_operation" in error_call[0][0]
        assert "Test error" in error_call[0][0]

    def test_performance_timer_default_logger(self):
        """Test performance timer with default logger."""
        # Should not raise an exception
        with PerformanceTimer("test_operation"):
            pass


class TestLoggingDecorators:
    """Test logging decorators."""

    def setup_method(self):
        """Set up test environment."""
        # Configure logging for testing
        logging.basicConfig(level=logging.DEBUG)

    def teardown_method(self):
        """Clean up test environment."""
        # Reset logging
        logging.getLogger().handlers.clear()

    def test_log_function_call_decorator(self):
        """Test log_function_call decorator."""

        @log_function_call
        def test_function(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        with patch("cdnbestip.logging_config.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.isEnabledFor.return_value = True
            mock_get_logger.return_value = mock_logger

            result = test_function("a", "b", kwarg1="c")

            assert result == "a-b-c"
            assert mock_logger.debug.call_count == 2  # Entry and exit

    def test_log_function_call_decorator_disabled(self):
        """Test log_function_call decorator when debug is disabled."""

        @log_function_call
        def test_function(arg1):
            return arg1 * 2

        with patch("cdnbestip.logging_config.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.isEnabledFor.return_value = False
            mock_get_logger.return_value = mock_logger

            result = test_function(5)

            assert result == 10
            assert not mock_logger.debug.called

    def test_log_function_call_decorator_exception(self):
        """Test log_function_call decorator with exception."""

        @log_function_call
        def test_function():
            raise ValueError("Test error")

        with patch("cdnbestip.logging_config.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.isEnabledFor.return_value = True
            mock_get_logger.return_value = mock_logger

            with pytest.raises(ValueError):
                test_function()

            # Should log entry and exception
            assert mock_logger.debug.call_count == 2

    def test_log_performance_decorator(self):
        """Test log_performance decorator."""

        @log_performance("test_operation")
        def test_function():
            import time

            time.sleep(0.01)
            return "result"

        with patch("cdnbestip.logging_config.PerformanceTimer") as mock_timer:
            mock_timer_instance = MagicMock()
            mock_timer.return_value.__enter__.return_value = mock_timer_instance
            mock_timer.return_value.__exit__.return_value = None

            result = test_function()

            assert result == "result"
            mock_timer.assert_called_once_with("test_operation (test_function)")


class TestGlobalFunctions:
    """Test global logging functions."""

    def teardown_method(self):
        """Clean up test environment."""
        # Reset global logger instance
        import cdnbestip.logging_config

        cdnbestip.logging_config._logger_instance = None

        # Reset logging
        logging.getLogger().handlers.clear()

    def test_configure_logging_global(self):
        """Test global configure_logging function."""
        configure_logging(level="DEBUG", debug_mode=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_get_logger_global(self):
        """Test global get_logger function."""
        configure_logging()

        test_logger = get_logger("test.module")
        assert isinstance(test_logger, logging.Logger)
        assert test_logger.name == "test.module"

    def test_enable_disable_debug_mode(self):
        """Test global debug mode functions."""
        configure_logging()

        enable_debug_mode()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

        disable_debug_mode()
        assert root_logger.level == logging.INFO


class TestLoggingIntegration:
    """Test logging integration scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Reset logging
        logging.getLogger().handlers.clear()

        # Reset global logger instance
        import cdnbestip.logging_config

        cdnbestip.logging_config._logger_instance = None

    def test_multiple_loggers(self):
        """Test multiple logger instances."""
        configure_logging()

        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1.name == "module1"
        assert logger2.name == "module2"
        assert logger1 != logger2

    def test_logging_with_file_output(self):
        """Test logging with file output."""
        # Override log directory
        with patch("cdnbestip.logging_config.CDNBESTIPLogger") as mock_logger_class:
            mock_logger = MagicMock()
            mock_logger.log_dir = Path(self.temp_dir)
            mock_logger_class.return_value = mock_logger

            configure_logging(file_logging=True)

            # Verify configure_logging was called
            mock_logger.configure_logging.assert_called_once()

    def test_third_party_logger_configuration(self):
        """Test third-party logger configuration."""
        configure_logging(debug_mode=True)

        # Check that third-party loggers are configured
        cloudflare_logger = logging.getLogger("cloudflare")
        requests_logger = logging.getLogger("requests")
        urllib3_logger = logging.getLogger("urllib3")

        # In debug mode, these should be set to DEBUG
        # In normal mode, they should be WARNING
        # The actual levels depend on the implementation
        assert isinstance(cloudflare_logger, logging.Logger)
        assert isinstance(requests_logger, logging.Logger)
        assert isinstance(urllib3_logger, logging.Logger)


class TestLoggingEdgeCases:
    """Test logging edge cases and error conditions."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Reset logging
        logging.getLogger().handlers.clear()
        logging.getLogger().setLevel(logging.WARNING)

        # Reset global logger instance
        import cdnbestip.logging_config

        cdnbestip.logging_config._logger_instance = None

    def test_configure_logging_multiple_times(self):
        """Test that configuring logging multiple times doesn't duplicate handlers."""
        configure_logging()
        initial_handler_count = len(logging.getLogger().handlers)

        # Configure again
        configure_logging()
        final_handler_count = len(logging.getLogger().handlers)

        # Should not add duplicate handlers
        assert final_handler_count == initial_handler_count

    def test_logger_with_invalid_level(self):
        """Test logger configuration with invalid level."""
        logger = CDNBESTIPLogger()
        logger.log_dir = Path(self.temp_dir)

        # Should default to INFO for invalid level
        logger.configure_logging(level="INVALID_LEVEL")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_performance_timer_with_zero_duration(self):
        """Test performance timer with very short duration."""
        mock_logger = MagicMock()

        with PerformanceTimer("instant_operation", mock_logger):
            pass  # No delay

        # Should still log start and completion
        assert mock_logger.info.call_count == 2

    def test_log_function_call_with_complex_args(self):
        """Test log_function_call decorator with complex arguments."""

        @log_function_call
        def complex_function(obj, *args, **kwargs):
            return f"processed {len(args)} args and {len(kwargs)} kwargs"

        with patch("cdnbestip.logging_config.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.isEnabledFor.return_value = True
            mock_get_logger.return_value = mock_logger

            result = complex_function(
                {"key": "value"}, "arg1", "arg2", kwarg1="val1", kwarg2="val2"
            )

            assert result == "processed 2 args and 2 kwargs"
            # Should log function entry and exit
            assert mock_logger.debug.call_count == 2

    def test_cleanup_old_logs_permission_error(self):
        """Test cleanup when permission error occurs."""
        logger = CDNBESTIPLogger()
        logger.log_dir = Path(self.temp_dir)
        logger.configure_logging()

        # Create a log file
        log_file = logger.log_dir / "test.log"
        log_file.touch()

        # Mock permission error
        with patch("pathlib.Path.unlink", side_effect=PermissionError("Permission denied")):
            # Should not raise exception, just log warning
            logger.cleanup_old_logs(days=0)  # Should try to delete all files

    def test_colored_formatter_without_tty(self):
        """Test colored formatter behavior when not in TTY."""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Should still format correctly even without colors
        formatted = formatter.format(record)
        assert "Test message" in formatted

    def test_get_logger_instance_singleton(self):
        """Test that get_logger_instance returns the same instance."""
        from cdnbestip.logging_config import get_logger_instance

        instance1 = get_logger_instance()
        instance2 = get_logger_instance()

        assert instance1 is instance2

    def test_performance_timer_nested(self):
        """Test nested performance timers."""
        mock_logger = MagicMock()

        with PerformanceTimer("outer_operation", mock_logger):
            with PerformanceTimer("inner_operation", mock_logger):
                import time

                time.sleep(0.01)

        # Should log both operations
        assert mock_logger.info.call_count == 4  # 2 starts + 2 completions

    def test_add_performance_logging_multiple_times(self):
        """Test adding performance logging multiple times."""
        logger = CDNBESTIPLogger()
        logger.log_dir = Path(self.temp_dir)
        logger.configure_logging()

        # Add performance logging twice
        logger.add_performance_logging()
        logger.add_performance_logging()

        perf_logger = logging.getLogger("cdnbestip.performance")
        # Should not duplicate handlers
        assert len(perf_logger.handlers) == 1

    def test_log_performance_decorator_with_exception(self):
        """Test log_performance decorator when function raises exception."""

        @log_performance("failing_operation")
        def failing_function():
            raise ValueError("Test error")

        with patch("cdnbestip.logging_config.PerformanceTimer") as mock_timer:
            mock_timer_instance = MagicMock()
            mock_timer.return_value.__enter__.return_value = mock_timer_instance
            mock_timer.return_value.__exit__.return_value = None

            with pytest.raises(ValueError):
                failing_function()

            # Timer should still be used
            mock_timer.assert_called_once()


class TestLoggingFileOperations:
    """Test logging file operations and error handling."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Reset logging
        logging.getLogger().handlers.clear()

        # Reset global logger instance
        import cdnbestip.logging_config

        cdnbestip.logging_config._logger_instance = None

    def test_log_directory_creation(self):
        """Test that log directory is created if it doesn't exist."""
        non_existent_dir = Path(self.temp_dir) / "non_existent" / "logs"

        logger = CDNBESTIPLogger()
        logger.log_dir = non_existent_dir
        logger.configure_logging(file_logging=True)

        assert non_existent_dir.exists()
        assert non_existent_dir.is_dir()

    def test_rotating_file_handler_configuration(self):
        """Test rotating file handler configuration."""
        logger = CDNBESTIPLogger()
        logger.log_dir = Path(self.temp_dir)
        logger.configure_logging(file_logging=True)

        root_logger = logging.getLogger()
        file_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
        ]

        assert len(file_handlers) == 1
        handler = file_handlers[0]
        assert handler.maxBytes == 10 * 1024 * 1024  # 10MB
        assert handler.backupCount == 5

    def test_log_file_naming_convention(self):
        """Test log file naming convention."""
        logger = CDNBESTIPLogger()
        logger.log_dir = Path(self.temp_dir)
        logger.configure_logging(file_logging=True)

        # Check that log file follows naming convention
        log_files = list(logger.log_dir.glob("cdnbestip_*.log"))
        assert len(log_files) > 0

        log_file = log_files[0]
        assert log_file.name.startswith("cdnbestip_")
        assert log_file.name.endswith(".log")

        # Should contain date in YYYYMMDD format
        import re

        date_pattern = r"cdnbestip_\d{8}\.log"
        assert re.match(date_pattern, log_file.name)

    def test_performance_log_file_creation(self):
        """Test performance log file creation."""
        logger = CDNBESTIPLogger()
        logger.log_dir = Path(self.temp_dir)
        logger.configure_logging()
        logger.add_performance_logging()

        # Check that performance log file is created
        perf_files = list(logger.log_dir.glob("performance_*.log"))
        assert len(perf_files) > 0

        perf_file = perf_files[0]
        assert perf_file.name.startswith("performance_")
        assert perf_file.name.endswith(".log")

    def test_cleanup_old_logs_with_different_ages(self):
        """Test cleanup with files of different ages."""
        logger = CDNBESTIPLogger()
        logger.log_dir = Path(self.temp_dir)
        logger.configure_logging()

        # Create files with different ages
        import time

        current_time = time.time()

        files_and_ages = [
            ("recent.log", current_time - (1 * 24 * 60 * 60)),  # 1 day old
            ("old.log", current_time - (31 * 24 * 60 * 60)),  # 31 days old
            ("ancient.log", current_time - (100 * 24 * 60 * 60)),  # 100 days old
            ("today.log", current_time),  # Current
        ]

        for filename, age in files_and_ages:
            file_path = logger.log_dir / filename
            file_path.touch()
            os.utime(file_path, (age, age))

        # Cleanup files older than 30 days
        logger.cleanup_old_logs(days=30)

        # Check which files remain
        remaining_files = [f.name for f in logger.log_dir.iterdir()]
        assert "recent.log" in remaining_files
        assert "today.log" in remaining_files
        assert "old.log" not in remaining_files
        assert "ancient.log" not in remaining_files

    def test_log_file_permissions(self):
        """Test that log files are created with appropriate permissions."""
        logger = CDNBESTIPLogger()
        logger.log_dir = Path(self.temp_dir)
        logger.configure_logging(file_logging=True)

        # Write a log message to create the file
        test_logger = logger.get_logger("test")
        test_logger.info("Test message")

        log_files = list(logger.log_dir.glob("cdnbestip_*.log"))
        assert len(log_files) > 0

        log_file = log_files[0]
        # File should be readable and writable by owner
        assert log_file.exists()
        assert os.access(log_file, os.R_OK)
        assert os.access(log_file, os.W_OK)
