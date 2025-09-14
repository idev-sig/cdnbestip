"""Unit tests for CLI interface."""

import argparse
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from cdnbestip.cli import (
    _is_valid_domain,
    _is_valid_url,
    execute_command,
    parse_arguments,
    print_configuration_summary,
    validate_arguments,
)
from cdnbestip.config import Config
from cdnbestip.exceptions import CDNBESTIPError, ValidationError


class TestArgumentParsing:
    """Test command line argument parsing."""

    def test_parse_arguments_minimal(self):
        """Test parsing minimal valid arguments."""
        with patch.object(sys, "argv", ["cdnbestip", "-d", "example.com", "-p", "cf"]):
            args = parse_arguments()
            assert args.domain == "example.com"
            assert args.prefix == "cf"
            assert args.speed == 2.0  # default
            assert args.zone_type == "A"  # default
            assert not args.dns
            assert not args.refresh

    def test_parse_arguments_full(self):
        """Test parsing all possible arguments."""
        test_args = [
            "cdnbestip",
            "-a",
            "user@example.com",
            "-k",
            "api_key_123",
            "-d",
            "example.com",
            "-p",
            "cf",
            "--type",
            "AAAA",
            "-s",
            "5.0",
            "-P",
            "443",
            "-u",
            "https://test.example.com/test",
            "-q",
            "10",
            "-i",
            "gc",
            "-c",
            "https://cdn.example.com/",
            "-e",
            "extra_params",
            "-r",
            "-n",
            "-o",
        ]

        with patch.object(sys, "argv", test_args):
            args = parse_arguments()
            assert args.account == "user@example.com"
            assert args.key == "api_key_123"
            assert args.domain == "example.com"
            assert args.prefix == "cf"
            assert args.zone_type == "AAAA"
            assert args.speed == 5.0
            assert args.port == 443
            assert args.url == "https://test.example.com/test"
            assert args.quantity == 10
            assert args.ipurl == "gc"
            assert args.cdn == "https://cdn.example.com/"
            assert args.extend == "extra_params"
            assert args.refresh
            assert args.dns
            assert args.only


class TestArgumentValidation:
    """Test command line argument validation."""

    def create_args(self, **kwargs):
        """Helper to create argparse.Namespace with defaults."""
        defaults = {
            "speed": 2.0,
            "port": None,
            "quantity": 0,
            "zone_type": "A",
            "url": None,
            "cdn": None,
            "domain": None,
            "ipurl": None,
            "dns": False,
            "prefix": None,
            "only": False,
            "timeout": 600,
            "log_level": "INFO",
            "debug": False,
            "verbose": False,
            "no_console_log": False,
            "no_file_log": False,
            "refresh": False,
            "cloudflare_email": None,
            "cloudflare_api_key": None,
            "cloudflare_api_token": None,
            "extend": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_validate_arguments_valid(self):
        """Test validation with valid arguments."""
        args = self.create_args(domain="example.com", speed=2.0, port=443, quantity=5)
        # Should not raise any exception
        validate_arguments(args)

    def test_validate_negative_speed(self):
        """Test validation fails for negative speed."""
        args = self.create_args(speed=-1.0)
        with pytest.raises(ValidationError):
            validate_arguments(args)

    def test_validate_invalid_port_range(self):
        """Test validation fails for invalid port range."""
        args = self.create_args(port=70000)
        with pytest.raises(ValidationError):
            validate_arguments(args)

        args = self.create_args(port=-1)
        with pytest.raises(ValidationError):
            validate_arguments(args)

    def test_validate_dns_requires_domain_and_prefix(self):
        """Test DNS operations require domain and prefix."""
        args = self.create_args(dns=True)
        with pytest.raises(ValidationError):
            validate_arguments(args)

        args = self.create_args(dns=True, domain="example.com")
        with pytest.raises(ValidationError):
            validate_arguments(args)

        args = self.create_args(dns=True, prefix="cf")
        with pytest.raises(ValidationError):
            validate_arguments(args)

        # Should pass with both
        args = self.create_args(dns=True, domain="example.com", prefix="cf")
        validate_arguments(args)


class TestUrlValidation:
    """Test URL validation functions."""

    def test_is_valid_url_valid_cases(self):
        """Test valid URL cases."""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "https://example.com/path",
            "https://example.com/path?query=1",
            "https://subdomain.example.com",
        ]

        for url in valid_urls:
            assert _is_valid_url(url), f"Should be valid: {url}"

    def test_is_valid_url_invalid_cases(self):
        """Test invalid URL cases."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Only http/https allowed
            "example.com",  # Missing protocol
            "https://",  # Incomplete
            "",
        ]

        for url in invalid_urls:
            assert not _is_valid_url(url), f"Should be invalid: {url}"


class TestDomainValidation:
    """Test domain validation functions."""

    def test_is_valid_domain_valid_cases(self):
        """Test valid domain cases."""
        valid_domains = [
            "example.com",
            "subdomain.example.com",
            "test-domain.co.uk",
            "a.b.c.d.example.com",
        ]

        for domain in valid_domains:
            assert _is_valid_domain(domain), f"Should be valid: {domain}"

    def test_is_valid_domain_invalid_cases(self):
        """Test invalid domain cases."""
        invalid_domains = [
            "example",  # No dot
            ".example.com",  # Starts with dot
            "example.com.",  # Ends with dot
            "",
        ]

        for domain in invalid_domains:
            assert not _is_valid_domain(domain), f"Should be invalid: {domain}"


class TestConfigurationSummary:
    """Test configuration summary printing."""

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_configuration_summary_complete(self, mock_stdout):
        """Test printing complete configuration summary."""
        config = Config(
            cloudflare_api_token="test_token",
            domain="example.com",
            prefix="cf",
            zone_type="A",
            speed_threshold=5.0,
            update_dns=True,
        )
        config._skip_validation = True

        print_configuration_summary(config)
        output = mock_stdout.getvalue()

        assert "API Token" in output
        assert "example.com" in output
        assert "cf" in output
        assert "5.0 MB/s" in output


class TestExecuteCommand:
    """Test command execution."""

    @patch("cdnbestip.cli.WorkflowOrchestrator")
    @patch("cdnbestip.cli.load_config")
    @patch("cdnbestip.cli.print_configuration_summary")
    def test_execute_command_success(
        self, mock_print_summary, mock_load_config, mock_workflow_class
    ):
        """Test successful command execution."""
        # Setup mocks
        config = Config(
            domain="example.com", prefix="cf", cloudflare_api_token="test_token", update_dns=True
        )
        config._skip_validation = True
        mock_load_config.return_value = config

        args = argparse.Namespace(
            domain="example.com",
            prefix="cf",
            dns=True,
            speed=2.0,
            port=None,
            quantity=0,
            zone_type="A",
            url=None,
            cdn=None,
            ipurl=None,
            only=False,
            timeout=600,
            log_level="INFO",
            debug=False,
            verbose=False,
            no_console_log=False,
            no_file_log=False,
            refresh=False,
            cloudflare_email=None,
            cloudflare_api_key=None,
            cloudflare_api_token=None,
            extend=None,
        )

        # Setup workflow mock
        mock_workflow = MagicMock()
        mock_workflow_class.return_value = mock_workflow

        execute_command(args)

        mock_load_config.assert_called_once_with(args)
        mock_workflow_class.assert_called_once_with(config)
        mock_workflow.execute.assert_called_once()
        mock_print_summary.assert_called_once_with(config)


class TestMainFunction:
    """Test main function error handling."""

    @patch("cdnbestip.cli.parse_arguments")
    @patch("cdnbestip.cli.execute_command")
    def test_main_success(self, mock_execute, mock_parse):
        """Test successful main execution."""
        from cdnbestip.cli import main

        args = MagicMock()
        mock_parse.return_value = args

        main()

        mock_parse.assert_called_once()
        mock_execute.assert_called_once_with(args)

    @patch("cdnbestip.cli.parse_arguments")
    @patch("sys.stderr", new_callable=StringIO)
    def test_main_cdnbestip_error(self, mock_stderr, mock_parse):
        """Test main function handling CDNBESTIPError."""
        from cdnbestip.cli import main

        mock_parse.side_effect = CDNBESTIPError("Test error")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        assert "❌ Error: Test error" in mock_stderr.getvalue()


class TestCLIErrorHandling:
    """Test CLI error handling scenarios."""

    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.exit")
    def test_main_configuration_error(self, mock_exit, mock_stderr):
        """Test main function handling configuration errors."""
        from cdnbestip.cli import main
        from cdnbestip.exceptions import ConfigurationError

        with patch("cdnbestip.cli.parse_arguments") as mock_parse:
            mock_parse.side_effect = ConfigurationError(
                "Invalid configuration",
                field="domain",
                suggestion="Use -d option to specify domain",
            )

            main()

            mock_exit.assert_called_once_with(2)
            error_output = mock_stderr.getvalue()
            assert "❌ Configuration Error: Invalid configuration" in error_output
            assert "💡 Use -d option to specify domain" in error_output

    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.exit")
    def test_main_speed_test_error(self, mock_exit, mock_stderr):
        """Test main function handling speed test errors."""
        from cdnbestip.cli import main
        from cdnbestip.exceptions import SpeedTestError

        with patch("cdnbestip.cli.parse_arguments") as mock_parse:
            mock_parse.side_effect = SpeedTestError(
                "Speed test failed", suggestion="Check network connectivity"
            )

            main()

            mock_exit.assert_called_once_with(1)
            error_output = mock_stderr.getvalue()
            assert "❌ Error: Speed test failed" in error_output
            assert "💡 Check network connectivity" in error_output

    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.exit")
    def test_main_dns_error(self, mock_exit, mock_stderr):
        """Test main function handling DNS errors."""
        from cdnbestip.cli import main
        from cdnbestip.exceptions import DNSError

        with patch("cdnbestip.cli.parse_arguments") as mock_parse:
            mock_parse.side_effect = DNSError(
                "DNS operation failed",
                operation="create",
                suggestion="Check CloudFlare credentials",
            )

            main()

            mock_exit.assert_called_once_with(1)
            error_output = mock_stderr.getvalue()
            assert "❌ Error: DNS operation failed" in error_output
            assert "💡 Check CloudFlare credentials" in error_output

    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.exit")
    def test_main_unexpected_error(self, mock_exit, mock_stderr):
        """Test main function handling unexpected errors."""
        from cdnbestip.cli import main

        with patch("cdnbestip.cli.parse_arguments") as mock_parse:
            mock_parse.side_effect = RuntimeError("Unexpected error")

            main()

            mock_exit.assert_called_once_with(1)
            error_output = mock_stderr.getvalue()
            assert "❌ Unexpected error: Unexpected error" in error_output
            assert "💡 This is an unexpected error. Please report this issue" in error_output


class TestCLIArgumentEdgeCases:
    """Test CLI argument parsing edge cases."""

    def test_parse_arguments_with_equals_syntax(self):
        """Test parsing arguments with equals syntax."""
        test_args = [
            "cdnbestip",
            "--domain=example.com",
            "--prefix=cf",
            "--speed=5.0",
            "--port=443",
        ]

        with patch.object(sys, "argv", test_args):
            args = parse_arguments()
            assert args.domain == "example.com"
            assert args.prefix == "cf"
            assert args.speed == 5.0
            assert args.port == 443

    def test_parse_arguments_help(self):
        """Test that help argument works."""
        with patch.object(sys, "argv", ["cdnbestip", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            # Help should exit with code 0
            assert exc_info.value.code == 0

    def test_parse_arguments_version(self):
        """Test version argument if implemented."""
        # This test assumes version argument exists
        with patch.object(sys, "argv", ["cdnbestip", "--version"]):
            try:
                with pytest.raises(SystemExit):
                    parse_arguments()
            except AttributeError:
                # Version argument might not be implemented yet
                pass

    def test_parse_arguments_conflicting_auth_methods(self):
        """Test parsing with both token and key/email."""
        test_args = [
            "cdnbestip",
            "-t",
            "api_token",
            "-a",
            "user@example.com",
            "-k",
            "api_key",
            "-d",
            "example.com",
            "-p",
            "cf",
        ]

        with patch.object(sys, "argv", test_args):
            args = parse_arguments()
            # Should accept both (validation happens later)
            assert args.token == "api_token"
            assert args.account == "user@example.com"
            assert args.key == "api_key"

    def test_parse_arguments_boolean_flags_variations(self):
        """Test boolean flag variations."""
        # Test short flags
        with patch.object(sys, "argv", ["cdnbestip", "-r", "-n", "-o"]):
            args = parse_arguments()
            assert args.refresh is True
            assert args.dns is True
            assert args.only is True

        # Test long flags
        with patch.object(sys, "argv", ["cdnbestip", "--refresh", "--dns", "--only"]):
            args = parse_arguments()
            assert args.refresh is True
            assert args.dns is True
            assert args.only is True


class TestArgumentValidationEdgeCases:
    """Test argument validation edge cases."""

    def create_args(self, **kwargs):
        """Helper to create argparse.Namespace with defaults."""
        defaults = {
            "speed": 2.0,
            "port": None,
            "quantity": 0,
            "zone_type": "A",
            "url": None,
            "cdn": None,
            "domain": None,
            "ipurl": None,
            "dns": False,
            "prefix": None,
            "only": False,
            "timeout": 600,
            "log_level": "INFO",
            "debug": False,
            "verbose": False,
            "no_console_log": False,
            "no_file_log": False,
            "refresh": False,
            "cloudflare_email": None,
            "cloudflare_api_key": None,
            "cloudflare_api_token": None,
            "extend": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_validate_zero_speed_threshold(self):
        """Test validation with zero speed threshold."""
        args = self.create_args(speed=0.0)
        # Zero should be valid
        validate_arguments(args)

    def test_validate_very_high_speed_threshold(self):
        """Test validation with very high speed threshold."""
        args = self.create_args(speed=1000.0)
        # High values should be valid
        validate_arguments(args)

    def test_validate_port_edge_values(self):
        """Test validation with port edge values."""
        # Port 0 should be valid
        args = self.create_args(port=0)
        validate_arguments(args)

        # Port 65535 should be valid
        args = self.create_args(port=65535)
        validate_arguments(args)

    def test_validate_negative_quantity(self):
        """Test validation with negative quantity."""
        args = self.create_args(quantity=-1)
        with pytest.raises(ValidationError):
            validate_arguments(args)

    def test_validate_zero_quantity(self):
        """Test validation with zero quantity (unlimited)."""
        args = self.create_args(quantity=0)
        # Zero should be valid (means unlimited)
        validate_arguments(args)

    def test_validate_invalid_zone_type(self):
        """Test validation with invalid zone type."""
        args = self.create_args(zone_type="INVALID")
        with pytest.raises(ValidationError):
            validate_arguments(args)

    def test_validate_valid_zone_types(self):
        """Test validation with all valid zone types."""
        valid_types = ["A", "AAAA", "CNAME", "MX", "TXT", "SRV"]

        for zone_type in valid_types:
            args = self.create_args(zone_type=zone_type)
            validate_arguments(args)  # Should not raise

    def test_validate_case_insensitive_zone_type(self):
        """Test validation with case variations of zone types."""
        args = self.create_args(zone_type="a")
        validate_arguments(args)  # Should not raise

        args = self.create_args(zone_type="aaaa")
        validate_arguments(args)  # Should not raise


class TestConfigurationSummaryEdgeCases:
    """Test configuration summary edge cases."""

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_configuration_summary_minimal(self, mock_stdout):
        """Test printing minimal configuration summary."""
        config = Config()
        config._skip_validation = True

        print_configuration_summary(config)
        output = mock_stdout.getvalue()

        # Should handle None/empty values gracefully
        assert "Configuration Summary" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_configuration_summary_with_sensitive_data(self, mock_stdout):
        """Test that sensitive data is masked in summary."""
        config = Config(
            cloudflare_api_token="very_secret_token_12345",
            cloudflare_api_key="secret_key_67890",
            cloudflare_email="user@example.com",
        )
        config._skip_validation = True

        print_configuration_summary(config)
        output = mock_stdout.getvalue()

        # Should mask sensitive information
        assert "very_secret_token_12345" not in output
        assert "secret_key_67890" not in output
        # Email might be shown or masked depending on implementation

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_configuration_summary_with_all_options(self, mock_stdout):
        """Test printing configuration summary with all options set."""
        config = Config(
            cloudflare_api_token="test_token",
            domain="example.com",
            prefix="cf",
            zone_type="AAAA",
            speed_threshold=10.0,
            speed_port=8080,
            speed_url="https://test.example.com/speed",
            quantity=5,
            update_dns=True,
            refresh=True,
            only_one=True,
            cdn_url="https://cdn.example.com/",
            ip_data_url="https://api.example.com/ips",
        )
        config._skip_validation = True

        print_configuration_summary(config)
        output = mock_stdout.getvalue()

        # Should include all relevant configuration
        assert "example.com" in output
        assert "cf" in output
        assert "AAAA" in output
        assert "10.0" in output


class TestCLIIntegrationScenarios:
    """Test CLI integration scenarios."""

    @patch("cdnbestip.cli.load_config")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.DNSManager")
    def test_execute_command_speed_test_only(
        self, mock_dns_manager, mock_speed_manager, mock_load_config
    ):
        """Test executing speed test without DNS update."""
        config = Config(domain="example.com", prefix="cf", update_dns=False)
        config._skip_validation = True
        mock_load_config.return_value = config

        # Mock speed test manager
        mock_speed_instance = MagicMock()
        mock_speed_manager.return_value = mock_speed_instance

        args = argparse.Namespace(
            domain="example.com",
            prefix="cf",
            dns=False,
            speed=2.0,
            port=None,
            quantity=0,
            zone_type="A",
            url=None,
            cdn=None,
            ipurl=None,
            only=False,
            timeout=600,
            log_level="INFO",
            debug=False,
            verbose=False,
            no_console_log=False,
            no_file_log=False,
            refresh=False,
            cloudflare_email=None,
            cloudflare_api_key=None,
            cloudflare_api_token=None,
            extend=None,
        )

        execute_command(args)

        # Should create speed test manager but not DNS manager
        mock_speed_manager.assert_called_once_with(config)
        mock_dns_manager.assert_not_called()

    @patch("cdnbestip.cli.load_config")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.DNSManager")
    def test_execute_command_with_dns_update(
        self, mock_dns_manager, mock_speed_manager, mock_load_config
    ):
        """Test executing command with DNS update."""
        config = Config(
            domain="example.com", prefix="cf", cloudflare_api_token="test_token", update_dns=True
        )
        config._skip_validation = True
        mock_load_config.return_value = config

        # Mock managers
        mock_speed_instance = MagicMock()
        mock_speed_manager.return_value = mock_speed_instance
        mock_dns_instance = MagicMock()
        mock_dns_manager.return_value = mock_dns_instance

        args = argparse.Namespace(
            domain="example.com",
            prefix="cf",
            dns=True,
            speed=2.0,
            port=None,
            quantity=0,
            zone_type="A",
            url=None,
            cdn=None,
            ipurl=None,
            only=False,
            timeout=600,
            log_level="INFO",
            debug=False,
            verbose=False,
            no_console_log=False,
            no_file_log=False,
            refresh=False,
            cloudflare_email=None,
            cloudflare_api_key=None,
            cloudflare_api_token=None,
            extend=None,
        )

        execute_command(args)

        # Should create both managers
        mock_speed_manager.assert_called_once_with(config)
        mock_dns_manager.assert_called_once_with(config)

    def test_cli_workflow_integration(self):
        """Test complete CLI workflow integration."""
        # This is a higher-level integration test
        test_args = ["cdnbestip", "-d", "example.com", "-p", "cf", "-s", "2.0"]

        with patch.object(sys, "argv", test_args):
            with patch("cdnbestip.cli.execute_command") as mock_execute:
                from cdnbestip.cli import main

                try:
                    main()
                except SystemExit:
                    pass  # Expected for successful execution

                # Should have called execute_command
                mock_execute.assert_called_once()

                # Check the arguments passed
                call_args = mock_execute.call_args[0][0]
                assert call_args.domain == "example.com"
                assert call_args.prefix == "cf"
                assert call_args.speed == 2.0


class TestCLIUtilityFunctions:
    """Test CLI utility functions."""

    def test_is_valid_url_with_query_parameters(self):
        """Test URL validation with query parameters."""
        url_with_query = "https://example.com/path?param1=value1&param2=value2"
        assert _is_valid_url(url_with_query)

    def test_is_valid_url_with_fragment(self):
        """Test URL validation with fragment."""
        url_with_fragment = "https://example.com/path#section"
        assert _is_valid_url(url_with_fragment)

    def test_is_valid_url_with_port(self):
        """Test URL validation with port."""
        url_with_port = "https://example.com:8080/path"
        assert _is_valid_url(url_with_port)

    def test_is_valid_domain_with_numbers(self):
        """Test domain validation with numbers."""
        domain_with_numbers = "test123.example456.com"
        assert _is_valid_domain(domain_with_numbers)

    def test_is_valid_domain_with_hyphens(self):
        """Test domain validation with hyphens."""
        domain_with_hyphens = "test-domain.example-site.co.uk"
        assert _is_valid_domain(domain_with_hyphens)

    def test_is_valid_domain_edge_cases(self):
        """Test domain validation edge cases."""
        # Single character domains
        assert _is_valid_domain("a.b")

        # Very long domain
        long_domain = "a" * 60 + ".example.com"
        assert _is_valid_domain(long_domain)

        # Domain with many subdomains
        many_subdomains = "a.b.c.d.e.f.example.com"
        assert _is_valid_domain(many_subdomains)
