"""Tests for proxy support functionality."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.cdnbestip.config import Config
from src.cdnbestip.dns import DNSManager
from src.cdnbestip.exceptions import ConfigurationError
from src.cdnbestip.ip_sources import IPSourceManager


class TestProxyConfiguration:
    """Test proxy configuration in Config class."""

    def test_valid_proxy_urls(self):
        """Test that valid proxy URLs are accepted."""
        valid_proxies = [
            "http://proxy.example.com:8080",
            "https://proxy.example.com:8080",
            "http://user:pass@proxy.example.com:8080",
            "https://user:pass@proxy.example.com:8080",
        ]

        for proxy_url in valid_proxies:
            config = Config()
            config._skip_validation = True
            config.proxy_url = proxy_url
            config._skip_validation = False
            # Should not raise an exception
            config._validate_urls()

    def test_invalid_proxy_urls(self):
        """Test that invalid proxy URLs are rejected."""
        invalid_proxies = [
            "ftp://proxy.example.com:8080",  # Unsupported protocol
            "socks4://proxy.example.com:1080",  # SOCKS not supported
            "socks5://proxy.example.com:1080",  # SOCKS not supported
            "proxy.example.com:8080",  # Missing protocol
            "http://",  # Incomplete URL
            "http:// proxy.example.com:8080",  # Space in URL
            "invalid-url",  # Not a URL
        ]

        for proxy_url in invalid_proxies:
            config = Config()
            config._skip_validation = True
            config.proxy_url = proxy_url
            config._skip_validation = False

            with pytest.raises(ConfigurationError):
                config._validate_urls()

    def test_no_proxy_configuration(self):
        """Test that no proxy configuration is valid."""
        config = Config()
        config._skip_validation = True
        config.proxy_url = None
        config._skip_validation = False
        # Should not raise an exception
        config._validate_urls()


class TestIPSourceManagerProxy:
    """Test proxy support in IPSourceManager."""

    @patch("src.cdnbestip.ip_sources.requests.get")
    def test_download_with_proxy(self, mock_get):
        """Test that proxy is used when downloading IP lists."""
        # Setup
        config = Config()
        config._skip_validation = True
        config.proxy_url = "http://proxy.example.com:8080"
        config._skip_validation = False

        manager = IPSourceManager(config)

        # Mock response
        mock_response = Mock()
        mock_response.text = "1.1.1.1\n2.2.2.2\n"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Test download
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            manager.download_ip_list("cf", "test_output.txt", force_refresh=True)

        # Verify proxy was used
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "proxies" in call_args[1]
        assert call_args[1]["proxies"] == {
            "http": "http://proxy.example.com:8080",
            "https": "http://proxy.example.com:8080",
        }

    @patch("src.cdnbestip.ip_sources.requests.get")
    def test_download_without_proxy(self, mock_get):
        """Test that no proxy is used when not configured."""
        # Setup
        config = Config()
        config._skip_validation = True
        config.proxy_url = None
        config._skip_validation = False

        manager = IPSourceManager(config)

        # Mock response
        mock_response = Mock()
        mock_response.text = "1.1.1.1\n2.2.2.2\n"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Test download
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            manager.download_ip_list("cf", "test_output.txt", force_refresh=True)

        # Verify no proxy was used
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "proxies" not in call_args[1]


class TestDNSManagerProxy:
    """Test proxy support in DNSManager."""

    @patch("src.cdnbestip.dns.Cloudflare")
    def test_authenticate_with_proxy(self, mock_cloudflare):
        """Test that proxy is used when authenticating with Cloudflare API."""
        # Setup
        config = Config()
        config._skip_validation = True
        config.cloudflare_api_token = "test_token"
        config.proxy_url = "http://proxy.example.com:8080"
        config._skip_validation = False

        manager = DNSManager(config)

        # Mock Cloudflare client
        mock_client = Mock()
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_client.user.get.return_value = mock_user
        mock_cloudflare.return_value = mock_client

        # Test authentication
        manager.authenticate()

        # Verify proxy was used
        mock_cloudflare.assert_called_once()
        call_args = mock_cloudflare.call_args
        assert call_args[1]["api_token"] == "test_token"
        assert "http_client" in call_args[1]

    @patch("src.cdnbestip.dns.Cloudflare")
    def test_authenticate_without_proxy(self, mock_cloudflare):
        """Test that no proxy is used when not configured."""
        # Setup
        config = Config()
        config._skip_validation = True
        config.cloudflare_api_token = "test_token"
        config.proxy_url = None
        config._skip_validation = False

        manager = DNSManager(config)

        # Mock Cloudflare client
        mock_client = Mock()
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_client.user.get.return_value = mock_user
        mock_cloudflare.return_value = mock_client

        # Test authentication
        manager.authenticate()

        # Verify no proxy was used
        mock_cloudflare.assert_called_once()
        call_args = mock_cloudflare.call_args
        assert call_args[1]["api_token"] == "test_token"
        assert "http_client" not in call_args[1]


class TestProxyURLValidation:
    """Test proxy URL validation functions."""

    def test_valid_proxy_url_patterns(self):
        """Test various valid proxy URL patterns."""
        from src.cdnbestip.cli import _is_valid_proxy_url

        valid_urls = [
            "http://proxy.example.com:8080",
            "https://secure-proxy.example.com:8080",
            "http://user:password@proxy.example.com:8080",
            "https://user:password@proxy.example.com:8080",
            "http://192.168.1.100:8080",
            "https://127.0.0.1:8080",
        ]

        for url in valid_urls:
            assert _is_valid_proxy_url(url), f"URL should be valid: {url}"

    def test_invalid_proxy_url_patterns(self):
        """Test various invalid proxy URL patterns."""
        from src.cdnbestip.cli import _is_valid_proxy_url

        invalid_urls = [
            "ftp://proxy.example.com:8080",  # Unsupported protocol
            "socks4://proxy.example.com:1080",  # SOCKS not supported
            "socks5://proxy.example.com:1080",  # SOCKS not supported
            "proxy.example.com:8080",  # Missing protocol
            "http://",  # Incomplete
            "http:// proxy.example.com:8080",  # Space in URL
            "not-a-url",  # Not a URL
            "",  # Empty string
        ]

        for url in invalid_urls:
            assert not _is_valid_proxy_url(url), f"URL should be invalid: {url}"
