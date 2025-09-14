"""Unit tests for timeout functionality."""

import argparse
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, "src")

from cdnbestip.cli import parse_arguments, validate_arguments
from cdnbestip.config import Config
from cdnbestip.exceptions import ConfigurationError, SpeedTestError, ValidationError
from cdnbestip.speedtest import SpeedTestManager


class TestTimeoutConfiguration:
    """Test timeout parameter in configuration."""

    def test_config_default_timeout(self):
        """Test default timeout value in Config."""
        config = Config()
        assert config.timeout == 600

    def test_config_custom_timeout(self):
        """Test custom timeout value in Config."""
        config = Config(timeout=300)
        assert config.timeout == 300

    def test_config_timeout_validation_positive(self):
        """Test timeout validation accepts positive values."""
        config = Config(timeout=1)
        assert config.timeout == 1

        config = Config(timeout=3600)
        assert config.timeout == 3600

    def test_config_timeout_validation_zero_fails(self):
        """Test timeout validation fails for zero."""
        with pytest.raises(ConfigurationError, match="Timeout must be greater than 0"):
            Config(timeout=0)

    def test_config_timeout_validation_negative_fails(self):
        """Test timeout validation fails for negative values."""
        with pytest.raises(ConfigurationError, match="Timeout must be greater than 0"):
            Config(timeout=-1)


class TestTimeoutCLIArguments:
    """Test timeout parameter in CLI arguments."""

    def test_cli_default_timeout(self):
        """Test CLI default timeout value."""
        with patch.object(sys, "argv", ["cdnbestip", "-d", "example.com"]):
            args = parse_arguments()
            assert args.timeout == 600

    def test_cli_custom_timeout_short_flag(self):
        """Test CLI custom timeout with short flag."""
        with patch.object(sys, "argv", ["cdnbestip", "-d", "example.com", "-T", "300"]):
            args = parse_arguments()
            assert args.timeout == 300

    def test_cli_custom_timeout_long_flag(self):
        """Test CLI custom timeout with long flag."""
        with patch.object(sys, "argv", ["cdnbestip", "-d", "example.com", "--timeout", "900"]):
            args = parse_arguments()
            assert args.timeout == 900

    def test_cli_timeout_validation_positive(self):
        """Test CLI timeout validation accepts positive values."""
        args = argparse.Namespace(
            timeout=300,
            speed=2.0,
            port=None,
            quantity=0,
            zone_type="A",
            url=None,
            cdn=None,
            domain="example.com",
            ipurl=None,
            dns=False,
            prefix=None,
            only=False,
            log_level="INFO",
            debug=False,
            verbose=False,
            no_console_log=False,
            no_file_log=False,
            refresh=False,
            cloudflare_account=None,
            cloudflare_api_key=None,
            cloudflare_api_token=None,
            extend=None,
        )
        validate_arguments(args)  # Should not raise

    def test_cli_timeout_validation_zero_fails(self):
        """Test CLI timeout validation fails for zero."""
        args = argparse.Namespace(
            timeout=0,
            speed=2.0,
            port=None,
            quantity=0,
            zone_type="A",
            url=None,
            cdn=None,
            domain=None,
            ipurl=None,
            dns=False,
            prefix=None,
            only=False,
            log_level="INFO",
            debug=False,
            verbose=False,
            no_console_log=False,
            no_file_log=False,
            refresh=False,
            cloudflare_account=None,
            cloudflare_api_key=None,
            cloudflare_api_token=None,
            extend=None,
        )
        with pytest.raises((ValidationError, SystemExit)):
            validate_arguments(args)


class TestTimeoutInSpeedTest:
    """Test timeout parameter usage in speed test execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(timeout=300)
        self.manager = SpeedTestManager(self.config)
        self.manager.binary_path = "/usr/bin/cfst"

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_speed_test_uses_config_timeout(self, mock_exists, mock_run):
        """Test speed test uses timeout from config."""
        # Mock file existence
        mock_exists.side_effect = lambda path: path in ["/tmp/ip.txt", "result.csv"]

        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        self.manager.run_speed_test("/tmp/ip.txt")

        # Check that subprocess was called with correct timeout
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 300

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_speed_test_timeout_default_when_not_set(self, mock_exists, mock_run):
        """Test speed test uses default timeout when config doesn't have it."""
        # Create config without timeout (using default)
        config = Config()
        manager = SpeedTestManager(config)
        manager.binary_path = "/usr/bin/cfst"

        # Mock file existence
        mock_exists.side_effect = lambda path: path in ["/tmp/ip.txt", "result.csv"]

        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        manager.run_speed_test("/tmp/ip.txt")

        # Check that subprocess was called with default timeout
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 600

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_speed_test_timeout_error_message(self, mock_exists, mock_run):
        """Test speed test timeout error message uses correct timeout value."""
        # Mock file existence
        mock_exists.side_effect = lambda path: path == "/tmp/ip.txt"

        # Mock timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired(["cfst"], 300)

        with pytest.raises(SpeedTestError) as exc_info:
            self.manager.run_speed_test("/tmp/ip.txt")

        # Check error message contains correct timeout in minutes
        assert "5 minutes" in str(exc_info.value)

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_speed_test_custom_timeout_error_message(self, mock_exists, mock_run):
        """Test speed test timeout error message with custom timeout."""
        # Use custom timeout (2 minutes = 120 seconds)
        self.config.timeout = 120

        # Mock file existence
        mock_exists.side_effect = lambda path: path == "/tmp/ip.txt"

        # Mock timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired(["cfst"], 120)

        with pytest.raises(SpeedTestError) as exc_info:
            self.manager.run_speed_test("/tmp/ip.txt")

        # Check error message contains correct timeout in minutes
        assert "2 minutes" in str(exc_info.value)
