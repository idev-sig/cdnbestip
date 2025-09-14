"""Logging configuration for CDNBESTIP."""

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to levelname
        if record.levelname in self.COLORS:
            colored_levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            )
            record.levelname = colored_levelname

        # Format the message
        formatted = super().format(record)

        # Reset colors at the end
        return formatted + self.COLORS["RESET"]


class CDNBESTIPLogger:
    """CDNBESTIP logging configuration manager."""

    def __init__(self):
        """Initialize logging configuration."""
        self.log_dir = Path.home() / ".cdnbestip" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.configured = False

    def configure_logging(
        self,
        level: str = "INFO",
        console: bool = True,
        file_logging: bool = True,
        debug_mode: bool = False,
        verbose: bool = False,
    ) -> None:
        """
        Configure logging for CDNBESTIP.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console: Enable console logging
            file_logging: Enable file logging
            debug_mode: Enable debug mode with detailed logging
            verbose: Enable verbose output
        """
        if self.configured:
            return

        # Determine log level
        if debug_mode:
            log_level = logging.DEBUG
        elif verbose:
            log_level = logging.INFO
        else:
            log_level = getattr(logging, level.upper(), logging.INFO)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Console handler
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)

            if debug_mode:
                console_format = (
                    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
                )
            elif verbose:
                console_format = "%(asctime)s - %(levelname)s - %(message)s"
            else:
                console_format = "%(levelname)s - %(message)s"

            # Use colored formatter for console
            if sys.stdout.isatty():  # Only use colors for TTY
                console_formatter = ColoredFormatter(console_format)
            else:
                console_formatter = logging.Formatter(console_format)

            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)

        # File handler
        if file_logging:
            log_file = self.log_dir / f"cdnbestip_{datetime.now().strftime('%Y%m%d')}.log"

            # Use rotating file handler to prevent large log files
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
            )
            file_handler.setLevel(logging.DEBUG)  # Always debug level for files

            file_format = (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(filename)s:%(lineno)d - %(funcName)s - %(message)s"
            )
            file_formatter = logging.Formatter(file_format)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

        # Configure third-party loggers
        self._configure_third_party_loggers(debug_mode)

        # Log configuration info
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured - Level: {logging.getLevelName(log_level)}")
        if file_logging:
            logger.info(f"Log file: {log_file}")

        self.configured = True

    def _configure_third_party_loggers(self, debug_mode: bool) -> None:
        """Configure third-party library loggers."""
        # CloudFlare library
        cloudflare_logger = logging.getLogger("cloudflare")
        if debug_mode:
            cloudflare_logger.setLevel(logging.DEBUG)
        else:
            cloudflare_logger.setLevel(logging.WARNING)

        # Requests library
        requests_logger = logging.getLogger("requests")
        if debug_mode:
            requests_logger.setLevel(logging.DEBUG)
        else:
            requests_logger.setLevel(logging.WARNING)

        # urllib3 (used by requests)
        urllib3_logger = logging.getLogger("urllib3")
        if debug_mode:
            urllib3_logger.setLevel(logging.DEBUG)
        else:
            urllib3_logger.setLevel(logging.WARNING)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance for a module.

        Args:
            name: Logger name (usually __name__)

        Returns:
            logging.Logger: Configured logger instance
        """
        return logging.getLogger(name)

    def set_debug_mode(self, enabled: bool) -> None:
        """
        Enable or disable debug mode.

        Args:
            enabled: Whether to enable debug mode
        """
        level = logging.DEBUG if enabled else logging.INFO

        # Update all handlers
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                handler.setLevel(level)

    def add_performance_logging(self) -> None:
        """Add performance logging for operations."""
        perf_logger = logging.getLogger("cdnbestip.performance")
        perf_logger.setLevel(logging.INFO)

        # Create separate performance log file
        perf_file = self.log_dir / f"performance_{datetime.now().strftime('%Y%m%d')}.log"
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
        )

        perf_format = "%(asctime)s - %(message)s"
        perf_formatter = logging.Formatter(perf_format)
        perf_handler.setFormatter(perf_formatter)
        perf_logger.addHandler(perf_handler)

        # Don't propagate to root logger to avoid duplication
        perf_logger.propagate = False

    def cleanup_old_logs(self, days: int = 30) -> None:
        """
        Clean up log files older than specified days.

        Args:
            days: Number of days to keep logs
        """
        try:
            import time

            cutoff_time = time.time() - (days * 24 * 60 * 60)

            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    logging.getLogger(__name__).debug(f"Cleaned up old log file: {log_file}")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to clean up old logs: {e}")


# Global logger instance
_logger_instance: CDNBESTIPLogger | None = None


def get_logger_instance() -> CDNBESTIPLogger:
    """Get the global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = CDNBESTIPLogger()
    return _logger_instance


def configure_logging(
    level: str = "INFO",
    console: bool = True,
    file_logging: bool = True,
    debug_mode: bool = False,
    verbose: bool = False,
) -> None:
    """
    Configure logging for CDNBESTIP application.

    Args:
        level: Logging level
        console: Enable console logging
        file_logging: Enable file logging
        debug_mode: Enable debug mode
        verbose: Enable verbose output
    """
    logger_instance = get_logger_instance()
    logger_instance.configure_logging(level, console, file_logging, debug_mode, verbose)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module.

    Args:
        name: Module name (usually __name__)

    Returns:
        logging.Logger: Configured logger
    """
    logger_instance = get_logger_instance()
    return logger_instance.get_logger(name)


def enable_debug_mode() -> None:
    """Enable debug mode logging."""
    logger_instance = get_logger_instance()
    logger_instance.set_debug_mode(True)


def disable_debug_mode() -> None:
    """Disable debug mode logging."""
    logger_instance = get_logger_instance()
    logger_instance.set_debug_mode(False)


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, operation_name: str, logger: logging.Logger | None = None):
        """
        Initialize performance timer.

        Args:
            operation_name: Name of the operation being timed
            logger: Logger to use (defaults to performance logger)
        """
        self.operation_name = operation_name
        self.logger = logger or logging.getLogger("cdnbestip.performance")
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        """Start timing."""
        import time

        self.start_time = time.time()
        self.logger.info(f"Started: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log results."""
        import time

        self.end_time = time.time()
        duration = self.end_time - self.start_time

        if exc_type is None:
            self.logger.info(f"Completed: {self.operation_name} in {duration:.2f}s")
        else:
            self.logger.error(f"Failed: {self.operation_name} after {duration:.2f}s - {exc_val}")

    def get_duration(self) -> float | None:
        """Get the duration of the operation."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


def log_function_call(func):
    """Decorator to log function calls in debug mode."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)

        if logger.isEnabledFor(logging.DEBUG):
            # Log function entry
            args_str = ", ".join([str(arg) for arg in args])
            kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
            all_args = ", ".join(filter(None, [args_str, kwargs_str]))

            logger.debug(f"Calling {func.__name__}({all_args})")

            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} returned: {type(result).__name__}")
                return result
            except Exception as e:
                logger.debug(f"{func.__name__} raised {type(e).__name__}: {e}")
                raise
        else:
            return func(*args, **kwargs)

    return wrapper


def log_performance(operation_name: str):
    """Decorator to log performance of functions."""

    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with PerformanceTimer(f"{operation_name} ({func.__name__})"):
                return func(*args, **kwargs)

        return wrapper

    return decorator
