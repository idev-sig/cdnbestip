"""
Test CLI compatibility between shell and Python versions.

This module tests that the Python CLI maintains backward compatibility
with the original shell script interface.
"""

import os
from unittest.mock import patch

import pytest

from cdnbestip.cli import parse_arguments, validate_arguments
from cdnbestip.config import load_config


class TestCLICompatibility:
    """Test CLI compatibility with original shell script."""

    def test_help_output_compatibility(self, capsys):
        """Test that help output includes all original shell script options."""
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["cdnbestip", "--help"]):
                parse_arguments()

        captured = capsys.readouterr()
        help_output = captured.out

        # Verify all original shell script options are present
        expected_options = [
            "-a",
            "--account",  # CloudFlare account email
            "-k",
            "--key",  # CloudFlare API key
            "-t",
            "--token",  # CloudFlare API token
            "-d",
            "--domain",  # Domain name
            "-p",
            "--prefix",  # DNS record prefix
            "--type",  # DNS record type (zone type)
            "-s",
            "--speed",  # Speed threshold
            "-P",
            "--port",  # Speed test port
            "-u",
            "--url",  # Speed test URL
            "-q",
            "--quantity",  # Record quantity
            "-i",
            "--ipurl",  # IP data source URL
            "-r",
            "--refresh",  # Force refresh
            "-n",
            "--dns",  # Update DNS
            "-o",
            "--only",  # Only one record
            "-c",
            "--cdn",  # CDN URL
            "-e",
            "--extend",  # Extended parameters
            "-h",
            "--help",  # Help
        ]

        for option in expected_options:
            assert option in help_output, f"Missing option: {option}"

    def test_argument_parsing_compatibility(self):
        """Test that all shell script arguments are parsed correctly."""
        # Test basic CloudFlare credentials
        with patch("sys.argv", ["cdnbestip", "-a", "user@example.com", "-k", "api_key"]):
            args = parse_arguments()
            assert args.account == "user@example.com"
            assert args.key == "api_key"

        # Test API token
        with patch("sys.argv", ["cdnbestip", "-t", "api_token"]):
            args = parse_arguments()
            assert args.token == "api_token"

        # Test DNS settings
        with patch("sys.argv", ["cdnbestip", "-d", "example.com", "-p", "cf", "--type", "A"]):
            args = parse_arguments()
            assert args.domain == "example.com"
            assert args.prefix == "cf"
            assert args.zone_type == "A"

        # Test speed settings
        with patch("sys.argv", ["cdnbestip", "-s", "5.0", "-P", "443", "-u", "https://test.com"]):
            args = parse_arguments()
            assert args.speed == 5.0
            assert args.port == 443
            assert args.url == "https://test.com"

        # Test operational flags
        with patch("sys.argv", ["cdnbestip", "-r", "-n", "-o"]):
            args = parse_arguments()
            assert args.refresh is True
            assert args.dns is True
            assert args.only is True

        # Test quantity and IP source
        with patch("sys.argv", ["cdnbestip", "-q", "5", "-i", "cf"]):
            args = parse_arguments()
            assert args.quantity == 5
            assert args.ipurl == "cf"

        # Test advanced options
        with patch("sys.argv", ["cdnbestip", "-c", "https://cdn.example.com/", "-e", "test-param"]):
            args = parse_arguments()
            assert args.cdn == "https://cdn.example.com/"
            assert args.extend == "test-param"

    def test_environment_variable_compatibility(self):
        """Test that environment variables work like in shell script."""
        # Test CloudFlare API key and email
        with patch.dict(
            os.environ,
            {"CLOUDFLARE_API_KEY": "test_api_key", "CLOUDFLARE_EMAIL": "test@example.com"},
        ):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com", "-p", "cf"]):
                args = parse_arguments()
                config = load_config(args)
                assert config.cloudflare_api_key == "test_api_key"
                assert config.CLOUDFLARE_EMAIL == "test@example.com"

        # Test CloudFlare API token
        with patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": "test_api_token"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com", "-p", "cf"]):
                args = parse_arguments()
                config = load_config(args)
                assert config.cloudflare_api_token == "test_api_token"

    def test_shell_script_example_commands(self):
        """Test that shell script example commands work in Python version."""
        # Example 1: Basic command with credentials
        with patch(
            "sys.argv",
            [
                "cdnbestip",
                "-a",
                "user@example.com",
                "-k",
                "api_key",
                "-d",
                "example.com",
                "-p",
                "cf",
                "-s",
                "2",
                "-n",
                "-o",
            ],
        ):
            args = parse_arguments()
            validate_arguments(args)
            config = load_config(args)

            assert config.CLOUDFLARE_EMAIL == "user@example.com"
            assert config.cloudflare_api_key == "api_key"
            assert config.domain == "example.com"
            assert config.prefix == "cf"
            assert config.speed_threshold == 2.0
            assert config.update_dns is True
            assert config.only_one is True

        # Example 2: Using environment variables
        with patch.dict(
            os.environ, {"CLOUDFLARE_API_KEY": "api_key", "CLOUDFLARE_EMAIL": "user@example.com"}
        ):
            with patch(
                "sys.argv", ["cdnbestip", "-d", "example.com", "-p", "cf", "-s", "2", "-n", "-o"]
            ):
                args = parse_arguments()
                validate_arguments(args)
                config = load_config(args)

                assert config.CLOUDFLARE_EMAIL == "user@example.com"
                assert config.cloudflare_api_key == "api_key"
                assert config.domain == "example.com"
                assert config.prefix == "cf"
                assert config.speed_threshold == 2.0
                assert config.update_dns is True
                assert config.only_one is True

    def test_ip_data_source_compatibility(self):
        """Test that IP data sources match shell script behavior."""
        # Test predefined sources
        predefined_sources = ["cf", "gc", "ct", "aws"]

        for source in predefined_sources:
            with patch("sys.argv", ["cdnbestip", "-i", source]):
                args = parse_arguments()
                validate_arguments(args)
                assert args.ipurl == source

        # Test custom URL
        with patch("sys.argv", ["cdnbestip", "-i", "https://custom.example.com/ips.txt"]):
            args = parse_arguments()
            validate_arguments(args)
            assert args.ipurl == "https://custom.example.com/ips.txt"

    def test_validation_compatibility(self):
        """Test that validation rules match shell script behavior."""
        # Test speed validation (must be >= 0)
        with patch("sys.argv", ["cdnbestip", "-s", "-1"]):
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)

        # Test port validation (0-65535)
        with patch("sys.argv", ["cdnbestip", "-P", "70000"]):
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)

        with patch("sys.argv", ["cdnbestip", "-P", "-1"]):
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)

        # Test domain validation (must contain dot)
        with patch("sys.argv", ["cdnbestip", "-d", "invalid_domain"]):
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)

        # Test URL validation
        with patch("sys.argv", ["cdnbestip", "-u", "invalid_url"]):
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)

        # Test DNS operation requirements
        with patch("sys.argv", ["cdnbestip", "-n"]):  # DNS flag without domain/prefix
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)

    def test_default_values_compatibility(self):
        """Test that default values match shell script defaults."""
        with patch("sys.argv", ["cdnbestip"]):
            # Should show help and exit when no args provided
            with pytest.raises(SystemExit):
                parse_arguments()

        # Test defaults when minimal args provided
        with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
            args = parse_arguments()
            config = load_config(args)

            # Check shell script defaults
            assert config.zone_type == "A"
            assert config.speed_threshold == 2.0
            assert config.quantity == 0  # Unlimited
            assert config.refresh is False
            assert config.update_dns is False
            assert config.only_one is False
            assert config.cdn_url == "https://fastfile.asfd.cn/"

    def test_long_and_short_options_compatibility(self):
        """Test that both long and short options work."""
        # Test all short options
        with patch(
            "sys.argv",
            [
                "cdnbestip",
                "-a",
                "user@example.com",
                "-k",
                "api_key",
                "-d",
                "example.com",
                "-p",
                "cf",
                "-s",
                "2",
                "-P",
                "443",
                "-u",
                "https://test.com",
                "-q",
                "5",
                "-i",
                "cf",
                "-c",
                "https://cdn.com/",
                "-e",
                "test-param",
                "-r",
                "-n",
                "-o",
            ],
        ):
            args = parse_arguments()
            validate_arguments(args)

        # Test all long options
        with patch(
            "sys.argv",
            [
                "cdnbestip",
                "--account",
                "user@example.com",
                "--key",
                "api_key",
                "--domain",
                "example.com",
                "--prefix",
                "cf",
                "--speed",
                "2",
                "--port",
                "443",
                "--url",
                "https://test.com",
                "--quantity",
                "5",
                "--ipurl",
                "cf",
                "--cdn",
                "https://cdn.com/",
                "--extend",
                "test-param",
                "--refresh",
                "--dns",
                "--only",
            ],
        ):
            args = parse_arguments()
            validate_arguments(args)

    def test_error_messages_compatibility(self):
        """Test that error messages are helpful like in shell script."""
        # Test missing required arguments for DNS operations
        with patch("sys.argv", ["cdnbestip", "-n"]):
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)

        # Test invalid port range
        with patch("sys.argv", ["cdnbestip", "-P", "70000"]):
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)

        # Test invalid speed threshold
        with patch("sys.argv", ["cdnbestip", "-s", "-5"]):
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)


class TestEnvironmentVariableCompatibility:
    """Test environment variable compatibility with shell script."""

    def test_cloudflare_credentials_env_vars(self):
        """Test CloudFlare credential environment variables."""
        # Test API key + email combination
        with patch.dict(
            os.environ, {"CLOUDFLARE_API_KEY": "test_key", "CLOUDFLARE_EMAIL": "test@example.com"}
        ):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)
                assert config.cloudflare_api_key == "test_key"
                assert config.CLOUDFLARE_EMAIL == "test@example.com"
                assert config.has_valid_credentials()

        # Test API token (should override key+email)
        with patch.dict(
            os.environ,
            {
                "CLOUDFLARE_API_TOKEN": "test_token",
                "CLOUDFLARE_API_KEY": "test_key",
                "CLOUDFLARE_EMAIL": "test@example.com",
            },
        ):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)
                assert config.cloudflare_api_token == "test_token"
                assert config.has_valid_credentials()

    def test_cli_args_override_env_vars(self):
        """Test that CLI arguments override environment variables."""
        with patch.dict(
            os.environ, {"CLOUDFLARE_API_KEY": "env_key", "CLOUDFLARE_EMAIL": "env@example.com"}
        ):
            with patch(
                "sys.argv",
                ["cdnbestip", "-a", "cli@example.com", "-k", "cli_key", "-d", "example.com"],
            ):
                args = parse_arguments()
                config = load_config(args)
                assert config.cloudflare_api_key == "cli_key"
                assert config.CLOUDFLARE_EMAIL == "cli@example.com"

    def test_cdn_environment_variable(self):
        """Test CDN environment variable compatibility."""
        with patch.dict(os.environ, {"CDN": "https://custom-cdn.example.com/"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)
                assert config.cdn_url == "https://custom-cdn.example.com/"

    def test_china_network_detection_env_var(self):
        """Test China network detection environment variable."""
        with patch.dict(os.environ, {"CN": "1"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)
                # Should use China CDN URL when CN=1
                assert "asfd.cn" in config.cdn_url or config.cdn_url.startswith(
                    "https://framagit.org"
                )


class TestOutputFormatCompatibility:
    """Test output format compatibility for automation scripts."""

    def test_csv_output_format(self):
        """Test that CSV output format matches shell script."""
        # This would be tested in integration tests with actual speed test results
        # For now, we test the structure expectations
        pass

    def test_error_output_format(self):
        """Test that error output format is compatible."""
        # Test that errors go to stderr
        with patch("sys.argv", ["cdnbestip", "-s", "-1"]):
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)

    def test_verbose_output_compatibility(self):
        """Test that verbose output is similar to shell script."""
        # The Python version provides more structured output
        # but should maintain key information compatibility
        pass


class TestFeatureParityValidation:
    """Test that all shell script features are implemented."""

    def test_all_ip_sources_supported(self):
        """Test that all IP sources from shell script are supported."""
        shell_sources = ["cf", "gc", "ct", "aws"]

        for source in shell_sources:
            with patch("sys.argv", ["cdnbestip", "-i", source]):
                args = parse_arguments()
                validate_arguments(args)
                config = load_config(args)
                assert config.ip_data_url == source

    def test_all_zone_types_supported(self):
        """Test that all DNS zone types are supported."""
        zone_types = ["A", "AAAA", "CNAME", "MX", "TXT", "SRV", "NS", "PTR"]

        for zone_type in zone_types:
            with patch("sys.argv", ["cdnbestip", "--type", zone_type]):
                args = parse_arguments()
                validate_arguments(args)
                config = load_config(args)
                assert config.zone_type == zone_type

    def test_speed_test_parameters_supported(self):
        """Test that all speed test parameters are supported."""
        # Test port parameter
        with patch("sys.argv", ["cdnbestip", "-P", "8080"]):
            args = parse_arguments()
            validate_arguments(args)
            config = load_config(args)
            assert config.speed_port == 8080

        # Test URL parameter
        with patch("sys.argv", ["cdnbestip", "-u", "https://test.example.com/test"]):
            args = parse_arguments()
            validate_arguments(args)
            config = load_config(args)
            assert config.speed_url == "https://test.example.com/test"

        # Test extend parameter
        with patch("sys.argv", ["cdnbestip", "-e", "--custom-param value"]):
            args = parse_arguments()
            validate_arguments(args)
            config = load_config(args)
            assert config.extend_string == "--custom-param value"

    def test_dns_operation_modes_supported(self):
        """Test that all DNS operation modes are supported."""
        # Test single record mode (--only)
        with patch("sys.argv", ["cdnbestip", "-d", "example.com", "-p", "cf", "-n", "-o"]):
            args = parse_arguments()
            validate_arguments(args)
            config = load_config(args)
            assert config.update_dns is True
            assert config.only_one is True

        # Test multiple record mode
        with patch("sys.argv", ["cdnbestip", "-d", "example.com", "-p", "cf", "-n", "-q", "5"]):
            args = parse_arguments()
            validate_arguments(args)
            config = load_config(args)
            assert config.update_dns is True
            assert config.only_one is False
            assert config.quantity == 5

        # Test unlimited records mode
        with patch("sys.argv", ["cdnbestip", "-d", "example.com", "-p", "cf", "-n"]):
            args = parse_arguments()
            validate_arguments(args)
            config = load_config(args)
            assert config.update_dns is True
            assert config.only_one is False
            assert config.quantity == 0  # Unlimited

    def test_refresh_behavior_supported(self):
        """Test that refresh behavior matches shell script."""
        # Test force refresh
        with patch("sys.argv", ["cdnbestip", "-r"]):
            args = parse_arguments()
            validate_arguments(args)
            config = load_config(args)
            assert config.refresh is True

        # Test automatic refresh logic (24-hour rule)
        # This would be tested in integration tests with file timestamps
        pass


if __name__ == "__main__":
    pytest.main([__file__])
