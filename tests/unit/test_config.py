"""Unit tests for configuration management."""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, "src")

from cdnbestip.config import Config, load_config_from_env, merge_config
from cdnbestip.exceptions import ConfigurationError


class TestConfig:
    """Test Config class validation."""

    def test_valid_config_creation(self):
        """Test creating a valid configuration."""
        config = Config(
            cloudflare_email="test@example.com",
            cloudflare_api_key="test_key",
            domain="example.com",
            prefix="cf",
            speed_threshold=5.0,
        )
        assert config.cloudflare_email == "test@example.com"
        assert config.speed_threshold == 5.0
        assert config.zone_type == "A"

    def test_config_without_dns_update_no_validation_error(self):
        """Test that config without DNS update doesn't require credentials."""
        config = Config(update_dns=False)
        # Should not raise any validation errors
        assert not config.update_dns

    def test_dns_update_requires_credentials(self):
        """Test that DNS update requires valid credentials."""
        with pytest.raises(ConfigurationError, match="CloudFlare credentials required"):
            Config(update_dns=True, domain="example.com", prefix="cf")

    def test_dns_update_requires_domain_and_prefix(self):
        """Test that DNS update requires domain and prefix."""
        with pytest.raises(ConfigurationError, match="Domain is required"):
            Config(update_dns=True, cloudflare_api_token="test_token", prefix="cf")

        with pytest.raises(ConfigurationError, match="Prefix is required"):
            Config(update_dns=True, cloudflare_api_token="test_token", domain="example.com")

    def test_invalid_email_format(self):
        """Test invalid email format validation."""
        with pytest.raises(ConfigurationError, match="Invalid email format"):
            Config(
                cloudflare_email="invalid-email",
                cloudflare_api_key="test_key",
                update_dns=True,
                domain="example.com",
                prefix="cf",
            )

    def test_invalid_domain_format(self):
        """Test invalid domain format validation."""
        with pytest.raises(ConfigurationError, match="Invalid domain format"):
            Config(
                cloudflare_api_token="test_token",
                update_dns=True,
                domain="invalid_domain_no_dot",
                prefix="cf",
            )

    def test_invalid_zone_type(self):
        """Test invalid zone type validation."""
        with pytest.raises(ConfigurationError, match="Invalid zone type"):
            Config(zone_type="INVALID")

    def test_zone_type_normalization(self):
        """Test zone type is normalized to uppercase."""
        config = Config(zone_type="a")
        assert config.zone_type == "A"

    def test_negative_speed_threshold(self):
        """Test negative speed threshold validation."""
        with pytest.raises(
            ConfigurationError, match="Speed threshold must be greater than or equal to 0"
        ):
            Config(speed_threshold=-1.0)

    def test_invalid_port_range(self):
        """Test invalid port range validation."""
        with pytest.raises(ConfigurationError, match="Speed port must be between 0 and 65535"):
            Config(speed_port=-1)

        with pytest.raises(ConfigurationError, match="Speed port must be between 0 and 65535"):
            Config(speed_port=65536)

    def test_negative_quantity(self):
        """Test negative quantity validation."""
        with pytest.raises(ConfigurationError, match="Quantity must be greater than or equal to 0"):
            Config(quantity=-1)

    def test_invalid_speed_url(self):
        """Test invalid speed URL validation."""
        with pytest.raises(ConfigurationError, match="Invalid speed test URL"):
            Config(speed_url="not-a-url")

    def test_invalid_cdn_url(self):
        """Test invalid CDN URL validation."""
        with pytest.raises(ConfigurationError, match="Invalid CDN URL"):
            Config(cdn_url="not-a-url")

    def test_invalid_ip_data_url(self):
        """Test invalid IP data URL validation."""
        with pytest.raises(ConfigurationError, match="Invalid IP data URL"):
            Config(ip_data_url="not-a-url")

    def test_predefined_ip_sources_valid(self):
        """Test that predefined IP sources don't require URL validation."""
        for source in ["cf", "gc", "aws", "ct", "CF", "GC", "AWS", "CT"]:
            config = Config(ip_data_url=source)
            assert config.ip_data_url == source

    def test_valid_urls(self):
        """Test valid URL formats."""
        config = Config(
            speed_url="https://example.com/test",
            cdn_url="https://cdn.example.com/",
            ip_data_url="https://api.example.com/ips",
        )
        assert config.speed_url == "https://example.com/test"
        assert config.cdn_url == "https://cdn.example.com/"
        assert config.ip_data_url == "https://api.example.com/ips"

    def test_get_cloudflare_credentials(self):
        """Test getting CloudFlare credentials."""
        config = Config(
            cloudflare_email="test@example.com",
            cloudflare_api_key="test_key",
            cloudflare_api_token="test_token",
        )
        email, key, token = config.get_cloudflare_credentials()
        assert email == "test@example.com"
        assert key == "test_key"
        assert token == "test_token"

    def test_has_valid_credentials(self):
        """Test credential validation methods."""
        # Test with API token
        config1 = Config(cloudflare_api_token="test_token")
        assert config1.has_valid_credentials()

        # Test with API key + email
        config2 = Config(cloudflare_email="test@example.com", cloudflare_api_key="test_key")
        assert config2.has_valid_credentials()

        # Test with no credentials
        config3 = Config()
        assert not config3.has_valid_credentials()

        # Test with incomplete credentials
        config4 = Config(cloudflare_email="test@example.com")
        assert not config4.has_valid_credentials()

    def test_requires_dns_update(self):
        """Test DNS update requirement check."""
        config = Config(
            update_dns=True, cloudflare_api_token="test_token", domain="example.com", prefix="cf"
        )
        assert config.requires_dns_update()

        # Test without DNS update flag
        config2 = Config(
            update_dns=False, cloudflare_api_token="test_token", domain="example.com", prefix="cf"
        )
        assert not config2.requires_dns_update()

        # Test with credentials but no domain (create without validation)
        config3 = Config()
        config3._skip_validation = True
        config3.update_dns = True
        config3.cloudflare_api_token = "test_token"
        config3.domain = None
        config3.prefix = None
        assert not config3.requires_dns_update()


class TestConfigLoading:
    """Test configuration loading functions."""

    @patch.dict(
        os.environ,
        {
            "cloudflare_email": "test@example.com",
            "CLOUDFLARE_API_KEY": "test_key",
            "CLOUDFLARE_API_TOKEN": "test_token",
            "CDN": "https://custom-cdn.com/",
        },
    )
    def test_load_config_from_env(self):
        """Test loading configuration from environment variables."""
        config = load_config_from_env()
        assert config.cloudflare_email == "test@example.com"
        assert config.cloudflare_api_key == "test_key"
        assert config.cloudflare_api_token == "test_token"
        assert config.cdn_url == "https://custom-cdn.com/"

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_from_env_empty(self):
        """Test loading configuration with no environment variables."""
        config = load_config_from_env()
        assert config.cloudflare_email is None
        assert config.cloudflare_api_key is None
        assert config.cloudflare_api_token is None
        assert config.cdn_url == "https://fastfile.asfd.cn/"

    def test_merge_config(self):
        """Test merging configurations."""
        base_config = Config(
            cloudflare_email="base@example.com", domain="base.com", speed_threshold=2.0
        )

        merged_config = merge_config(
            base_config, domain="override.com", prefix="cf", speed_threshold=5.0
        )

        # Check overridden values
        assert merged_config.domain == "override.com"
        assert merged_config.prefix == "cf"
        assert merged_config.speed_threshold == 5.0

        # Check preserved values
        assert merged_config.cloudflare_email == "base@example.com"

    def test_merge_config_none_values(self):
        """Test that None values in overrides don't override base values."""
        base_config = Config(cloudflare_email="base@example.com", domain="base.com")

        merged_config = merge_config(
            base_config,
            cloudflare_email=None,  # Should not override
            prefix="cf",  # Should set new value
        )

        assert merged_config.cloudflare_email == "base@example.com"
        assert merged_config.prefix == "cf"
        assert merged_config.domain == "base.com"


class TestCLIArgumentLoading:
    """Test CLI argument loading functionality."""

    def test_load_config_from_args(self):
        """Test loading configuration from CLI arguments."""
        from argparse import Namespace

        from cdnbestip.config import load_config_from_args

        args = Namespace(
            email="cli@example.com",
            key="cli_key",
            token="cli_token",
            domain="cli.com",
            prefix="cli",
            zone_type="AAAA",
            speed=5.0,
            port=443,
            url="https://cli.example.com/test",
            quantity=10,
            refresh=True,
            dns=True,
            only=True,
            cdn="https://cli-cdn.com/",
            ipurl="https://cli-ip.com/list",
            extend="--extra-param",
        )

        config = load_config_from_args(args)
        assert config.cloudflare_email == "cli@example.com"
        assert config.cloudflare_api_key == "cli_key"
        assert config.cloudflare_api_token == "cli_token"
        assert config.domain == "cli.com"
        assert config.prefix == "cli"
        assert config.zone_type == "AAAA"
        assert config.speed_threshold == 5.0
        assert config.speed_port == 443
        assert config.speed_url == "https://cli.example.com/test"
        assert config.quantity == 10
        assert config.refresh is True
        assert config.update_dns is True
        assert config.only_one is True
        assert config.cdn_url == "https://cli-cdn.com/"
        assert config.ip_data_url == "https://cli-ip.com/list"
        assert config.extend_string == "--extra-param"

    def test_load_config_from_args_minimal(self):
        """Test loading configuration from minimal CLI arguments."""
        from argparse import Namespace

        from cdnbestip.config import load_config_from_args

        args = Namespace(
            email=None,
            key=None,
            token=None,
            domain=None,
            prefix=None,
            type="A",
            speed=2.0,
            port=None,
            url=None,
            quantity=0,
            refresh=False,
            dns=False,
            only=False,
            cdn="https://fastfile.asfd.cn/",
            ipurl=None,
            extend=None,
        )

        config = load_config_from_args(args)
        assert config.cloudflare_email is None
        assert config.cloudflare_api_key is None
        assert config.cloudflare_api_token is None
        assert config.domain is None
        assert config.prefix is None
        assert config.zone_type == "A"
        assert config.speed_threshold == 2.0
        assert config.speed_port is None
        assert config.speed_url is None
        assert config.quantity == 0
        assert config.refresh is False
        assert config.update_dns is False
        assert config.only_one is False
        assert config.cdn_url == "https://fastfile.asfd.cn/"
        assert config.ip_data_url is None
        assert config.extend_string is None

    @patch.dict(
        os.environ,
        {
            "cloudflare_email": "env@example.com",
            "CLOUDFLARE_API_KEY": "env_key",
            "CDN": "https://env-cdn.com/",
        },
    )
    def test_load_config_cli_overrides_env(self):
        """Test that CLI arguments override environment variables."""
        from argparse import Namespace

        from cdnbestip.config import load_config

        args = Namespace(
            email="cli@example.com",  # Should override env
            key=None,  # Should use env value
            token="cli_token",  # Should use cli value
            domain="cli.com",
            prefix="cli",
            type="A",
            speed=3.0,
            port=None,
            url=None,
            quantity=0,
            refresh=False,
            dns=True,
            only=False,
            cdn=None,  # Should use env value
            ipurl=None,
            extend=None,
        )

        config = load_config(args)
        assert config.cloudflare_email == "cli@example.com"  # CLI override
        assert config.cloudflare_api_key == "env_key"  # From env
        assert config.cloudflare_api_token == "cli_token"  # From CLI
        assert config.domain == "cli.com"
        assert config.prefix == "cli"
        assert config.speed_threshold == 3.0
        assert config.update_dns is True
        assert config.cdn_url == "https://env-cdn.com/"  # From env

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_no_env_with_args(self):
        """Test loading config with CLI args but no environment variables."""
        from argparse import Namespace

        from cdnbestip.config import load_config

        args = Namespace(
            email="cli@example.com",
            key="cli_key",
            token=None,
            domain="cli.com",
            prefix="cli",
            type="A",
            speed=2.0,
            port=None,
            url=None,
            quantity=0,
            refresh=False,
            dns=True,
            only=False,
            cdn="https://fastfile.asfd.cn/",
            ipurl=None,
            extend=None,
        )

        config = load_config(args)
        assert config.cloudflare_email == "cli@example.com"
        assert config.cloudflare_api_key == "cli_key"
        assert config.cloudflare_api_token is None
        assert config.domain == "cli.com"
        assert config.prefix == "cli"
        assert config.update_dns is True
        assert config.cdn_url == "https://fastfile.asfd.cn/"

    @patch.dict(
        os.environ, {"cloudflare_email": "env@example.com", "CLOUDFLARE_API_KEY": "env_key"}
    )
    def test_load_config_no_args(self):
        """Test loading config with no CLI args (env only)."""
        from cdnbestip.config import load_config

        config = load_config(None)
        assert config.cloudflare_email == "env@example.com"
        assert config.cloudflare_api_key == "env_key"
        assert config.cloudflare_api_token is None
        assert config.domain is None
        assert config.prefix is None
        assert config.update_dns is False
        assert config.cdn_url == "https://fastfile.asfd.cn/"

    def test_load_config_boolean_flags(self):
        """Test that boolean flags are handled correctly."""
        from argparse import Namespace

        from cdnbestip.config import load_config

        # Test with flags set (but no DNS update to avoid credential validation)
        args = Namespace(
            email=None,
            key=None,
            token=None,
            domain=None,
            prefix=None,
            type="A",
            speed=2.0,
            port=None,
            url=None,
            quantity=0,
            refresh=True,
            dns=False,
            only=True,  # dns=False to avoid credential validation
            cdn="https://fastfile.asfd.cn/",
            ipurl=None,
            extend=None,
        )

        config = load_config(args)
        assert config.refresh is True
        assert config.update_dns is False
        assert config.only_one is True

        # Test with flags not set
        args.refresh = False
        args.dns = False
        args.only = False

        config = load_config(args)
        assert config.refresh is False
        assert config.update_dns is False
        assert config.only_one is False

        # Test DNS flag with proper credentials
        args.dns = True
        args.token = "test_token"
        args.domain = "example.com"
        args.prefix = "cf"

        config = load_config(args)
        assert config.update_dns is True


class TestValidationHelpers:
    """Test validation helper methods."""

    def test_email_validation(self):
        """Test email validation helper."""
        config = Config()

        # Valid emails
        assert config._is_valid_email("test@example.com")
        assert config._is_valid_email("user.name+tag@domain.co.uk")
        assert config._is_valid_email("123@test-domain.org")

        # Invalid emails
        assert not config._is_valid_email("invalid-email")
        assert not config._is_valid_email("@example.com")
        assert not config._is_valid_email("test@")
        assert not config._is_valid_email("test.example.com")

    def test_domain_validation(self):
        """Test domain validation helper."""
        config = Config()

        # Valid domains
        assert config._is_valid_domain("example.com")
        assert config._is_valid_domain("sub.example.com")
        assert config._is_valid_domain("test-domain.co.uk")
        assert config._is_valid_domain("a.b")

        # Invalid domains
        assert not config._is_valid_domain("invalid_domain")
        assert not config._is_valid_domain("example")
        assert not config._is_valid_domain(".example.com")
        assert not config._is_valid_domain("example.com.")

    def test_url_validation(self):
        """Test URL validation helper."""
        config = Config()

        # Valid URLs
        assert config._is_valid_url("https://example.com")
        assert config._is_valid_url("http://test.com/path")
        assert config._is_valid_url("https://api.example.com/v1/data?param=value")

        # Invalid URLs
        assert not config._is_valid_url("not-a-url")
        assert not config._is_valid_url("ftp://example.com")
        assert not config._is_valid_url("example.com")
        assert not config._is_valid_url("https://")


if __name__ == "__main__":
    pytest.main([__file__])
