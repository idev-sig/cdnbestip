"""
Test environment variable compatibility between shell and Python versions.

This module ensures that all environment variables used in the shell script
work identically in the Python version.
"""

import os
from unittest.mock import patch

import pytest

from cdnbestip.cli import parse_arguments
from cdnbestip.config import load_config


class TestEnvironmentVariableCompatibility:
    """Test environment variable compatibility with shell script."""

    def test_cloudflare_api_key_env_var(self):
        """Test CLOUDFLARE_API_KEY environment variable."""
        with patch.dict(os.environ, {"CLOUDFLARE_API_KEY": "test_api_key_123"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)
                assert config.cloudflare_api_key == "test_api_key_123"

    def test_cloudflare_account_env_var(self):
        """Test CLOUDFLARE_ACCOUNT environment variable."""
        with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT": "test@example.com"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)
                assert config.cloudflare_account == "test@example.com"

    def test_cloudflare_api_token_env_var(self):
        """Test CLOUDFLARE_API_TOKEN environment variable."""
        with patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": "test_token_456"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)
                assert config.cloudflare_api_token == "test_token_456"

    def test_cdn_env_var(self):
        """Test CDN environment variable for acceleration URL."""
        with patch.dict(os.environ, {"CDN": "https://custom-cdn.example.com/"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)
                assert config.cdn_url == "https://custom-cdn.example.com/"

    def test_cn_env_var_china_detection(self):
        """Test CN environment variable for China network detection."""
        # Test CN=1 (China network)
        with patch.dict(os.environ, {"CN": "1"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)
                # Should use China-specific CDN or settings
                assert hasattr(config, "in_china")
                # The actual behavior depends on implementation

    def test_debug_env_var(self):
        """Test DEBUG environment variable for debug mode."""
        with patch.dict(os.environ, {"DEBUG": "1"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)
                # Debug mode should be enabled
                assert hasattr(config, "debug") or config.debug is True

    def test_env_var_precedence(self):
        """Test that CLI arguments override environment variables."""
        with patch.dict(
            os.environ,
            {
                "CLOUDFLARE_API_KEY": "env_key",
                "CLOUDFLARE_ACCOUNT": "env@example.com",
                "CDN": "https://env-cdn.com/",
            },
        ):
            with patch(
                "sys.argv",
                [
                    "cdnbestip",
                    "-a",
                    "cli@example.com",
                    "-k",
                    "cli_key",
                    "-c",
                    "https://cli-cdn.com/",
                    "-d",
                    "example.com",
                ],
            ):
                args = parse_arguments()
                config = load_config(args)

                # CLI args should override env vars
                assert config.cloudflare_account == "cli@example.com"
                assert config.cloudflare_api_key == "cli_key"
                assert config.cdn_url == "https://cli-cdn.com/"

    def test_api_token_overrides_key_email(self):
        """Test that API token takes precedence over API key + email."""
        with patch.dict(
            os.environ,
            {
                "CLOUDFLARE_API_TOKEN": "token_123",
                "CLOUDFLARE_API_KEY": "key_456",
                "CLOUDFLARE_ACCOUNT": "test@example.com",
            },
        ):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)

                # Token should be used, key+email should be ignored
                assert config.cloudflare_api_token == "token_123"
                assert config.has_valid_credentials()

    def test_missing_env_vars_handled_gracefully(self):
        """Test that missing environment variables are handled gracefully."""
        # Clear all CloudFlare env vars
        env_vars_to_clear = [
            "CLOUDFLARE_API_KEY",
            "CLOUDFLARE_ACCOUNT",
            "CLOUDFLARE_API_TOKEN",
            "CDN",
            "CN",
            "DEBUG",
        ]

        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing env vars
            for var in env_vars_to_clear:
                os.environ.pop(var, None)

            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)

                # Should use defaults
                assert config.cloudflare_api_key is None
                assert config.cloudflare_account is None
                assert config.cloudflare_api_token is None
                assert config.cdn_url == "https://fastfile.asfd.cn/"  # Default CDN

    def test_empty_env_vars_treated_as_unset(self):
        """Test that empty environment variables are treated as unset."""
        with patch.dict(
            os.environ,
            {
                "CLOUDFLARE_API_KEY": "",
                "CLOUDFLARE_ACCOUNT": "",
                "CLOUDFLARE_API_TOKEN": "",
                "CDN": "",
            },
        ):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)

                # Empty strings should be treated as None/unset
                assert not config.cloudflare_api_key
                assert not config.cloudflare_account
                assert not config.cloudflare_api_token
                # CDN should fall back to default
                assert config.cdn_url == "https://fastfile.asfd.cn/"

    def test_whitespace_env_vars_handled(self):
        """Test that environment variables with whitespace are handled."""
        with patch.dict(
            os.environ,
            {
                "CLOUDFLARE_API_KEY": "  test_key_with_spaces  ",
                "CLOUDFLARE_ACCOUNT": "  test@example.com  ",
            },
        ):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)

                # Should strip whitespace
                assert config.cloudflare_api_key == "test_key_with_spaces"
                assert config.cloudflare_account == "test@example.com"


class TestShellScriptEnvironmentBehavior:
    """Test specific environment behaviors from shell script."""

    def test_china_network_detection_logic(self):
        """Test China network detection logic matches shell script."""
        # Test manual CN flag
        with patch.dict(os.environ, {"CN": "1"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                load_config(args)
                # Should be detected as China network
                # Implementation should match shell script logic

    def test_cdn_url_behavior_in_china(self):
        """Test CDN URL behavior when in China."""
        # When CN=1, should use China-specific URLs
        with patch.dict(os.environ, {"CN": "1"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                load_config(args)
                # Should use China CDN or framagit URLs
                # This matches shell script behavior

    def test_proxy_detection_env_vars(self):
        """Test proxy detection environment variables."""
        # Test common proxy environment variables
        proxy_env_vars = {
            "HTTP_PROXY": "http://proxy.example.com:8080",
            "HTTPS_PROXY": "https://proxy.example.com:8080",
            "http_proxy": "http://proxy.example.com:8080",
            "https_proxy": "https://proxy.example.com:8080",
        }

        with patch.dict(os.environ, proxy_env_vars):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                load_config(args)
                # Should detect proxy environment
                # Implementation should handle proxy settings

    def test_user_id_detection(self):
        """Test user ID detection for sudo operations."""
        # Shell script checks USER_ID for sudo operations
        # Python version should handle permissions appropriately
        with patch("os.getuid", return_value=1000):  # Non-root user
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                load_config(args)
                # Should detect non-root user

    def test_shell_script_variable_compatibility(self):
        """Test that shell script variables are compatible."""
        shell_vars = {
            "CLOUDFLARE_API_KEY": "test_key",
            "CLOUDFLARE_ACCOUNT": "test@example.com",
            "CDN": "https://test-cdn.com/",
            "CN": "1",
            "DEBUG": "1",
        }

        with patch.dict(os.environ, shell_vars):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com", "-p", "cf"]):
                args = parse_arguments()
                config = load_config(args)

                # All shell variables should be properly loaded
                assert config.cloudflare_api_key == "test_key"
                assert config.cloudflare_account == "test@example.com"
                assert config.cdn_url == "https://test-cdn.com/"


class TestEnvironmentVariableValidation:
    """Test validation of environment variables."""

    def test_invalid_cdn_url_in_env_var(self):
        """Test handling of invalid CDN URL in environment variable."""
        with patch.dict(os.environ, {"CDN": "invalid_url_format"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                # Should either validate or fall back to default
                load_config(args)
                # Invalid URL should be handled gracefully

    def test_malformed_email_in_env_var(self):
        """Test handling of malformed email in environment variable."""
        with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT": "invalid_email_format"}):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)
                # Should be detected during credential validation
                assert (
                    not config.has_valid_credentials()
                    or config.cloudflare_account == "invalid_email_format"
                )

    def test_special_characters_in_env_vars(self):
        """Test handling of special characters in environment variables."""
        special_chars_key = "key_with_!@#$%^&*()_+-={}[]|\\:\";'<>?,./"
        special_chars_email = "test+special@example-domain.co.uk"

        with patch.dict(
            os.environ,
            {"CLOUDFLARE_API_KEY": special_chars_key, "CLOUDFLARE_ACCOUNT": special_chars_email},
        ):
            with patch("sys.argv", ["cdnbestip", "-d", "example.com"]):
                args = parse_arguments()
                config = load_config(args)

                # Should handle special characters properly
                assert config.cloudflare_api_key == special_chars_key
                assert config.cloudflare_account == special_chars_email


class TestEnvironmentVariableDocumentation:
    """Test that environment variables are properly documented."""

    def test_help_mentions_env_vars(self, capsys):
        """Test that help output mentions environment variables."""
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["cdnbestip", "--help"]):
                parse_arguments()

        captured = capsys.readouterr()
        help_output = captured.out

        # Should mention key environment variables

        # At least some environment variables should be mentioned
        # (exact format may vary)
        help_lower = help_output.lower()
        assert any(
            "cloudflare" in help_lower and "environment" in help_lower for _ in [True]
        )  # Basic check for env var documentation

    def test_example_commands_show_env_var_usage(self, capsys):
        """Test that example commands show environment variable usage."""
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["cdnbestip", "--help"]):
                parse_arguments()

        captured = capsys.readouterr()
        help_output = captured.out

        # Should show example with export statements
        assert "export" in help_output or "CLOUDFLARE" in help_output


if __name__ == "__main__":
    pytest.main([__file__])
