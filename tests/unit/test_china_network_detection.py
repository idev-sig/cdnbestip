"""Unit tests for China network detection functionality."""

import os
import socket
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, "src")

from cdnbestip.config import Config, is_china_network
from cdnbestip.speedtest import SpeedTestManager


class TestChinaNetworkDetection:
    """Test China network detection logic."""

    def test_china_detection_environment_variable_set(self):
        """Test China detection when CN environment variable is set to 1."""
        with patch.dict(os.environ, {"CN": "1"}):
            assert is_china_network() is True

    def test_china_detection_environment_variable_unset(self):
        """Test China detection when CN environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("socket.socket") as mock_socket:
                # Mock successful connection (not in China)
                mock_sock = Mock()
                mock_sock.connect_ex.return_value = 0
                mock_socket.return_value = mock_sock

                assert is_china_network() is False
                mock_sock.connect_ex.assert_called_once_with(("google.com", 80))
                mock_sock.close.assert_called_once()

    def test_china_detection_environment_variable_zero(self):
        """Test China detection when CN environment variable is set to 0."""
        with patch.dict(os.environ, {"CN": "0"}):
            with patch("socket.socket") as mock_socket:
                # Mock successful connection (not in China)
                mock_sock = Mock()
                mock_sock.connect_ex.return_value = 0
                mock_socket.return_value = mock_sock

                assert is_china_network() is False

    def test_china_detection_environment_variable_empty(self):
        """Test China detection when CN environment variable is empty."""
        with patch.dict(os.environ, {"CN": ""}):
            with patch("socket.socket") as mock_socket:
                # Mock successful connection (not in China)
                mock_sock = Mock()
                mock_sock.connect_ex.return_value = 0
                mock_socket.return_value = mock_sock

                assert is_china_network() is False

    def test_china_detection_google_accessible(self):
        """Test China detection when google.com is accessible."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("socket.socket") as mock_socket:
                # Mock successful connection (return 0)
                mock_sock = Mock()
                mock_sock.connect_ex.return_value = 0
                mock_socket.return_value = mock_sock

                assert is_china_network() is False
                mock_sock.settimeout.assert_called_once_with(3)
                mock_sock.connect_ex.assert_called_once_with(("google.com", 80))
                mock_sock.close.assert_called_once()

    def test_china_detection_google_not_accessible(self):
        """Test China detection when google.com is not accessible."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("socket.socket") as mock_socket:
                # Mock failed connection (return non-zero)
                mock_sock = Mock()
                mock_sock.connect_ex.return_value = 1
                mock_socket.return_value = mock_sock

                assert is_china_network() is True
                mock_sock.settimeout.assert_called_once_with(3)
                mock_sock.connect_ex.assert_called_once_with(("google.com", 80))
                mock_sock.close.assert_called_once()

    def test_china_detection_socket_timeout_exception(self):
        """Test China detection when socket times out."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("socket.socket") as mock_socket:
                # Mock timeout exception
                mock_sock = Mock()
                mock_sock.connect_ex.side_effect = TimeoutError("Connection timed out")
                mock_socket.return_value = mock_sock

                assert is_china_network() is True
                mock_sock.close.assert_called_once()

    def test_china_detection_socket_gaierror_exception(self):
        """Test China detection when DNS resolution fails."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("socket.socket") as mock_socket:
                # Mock DNS resolution error
                mock_sock = Mock()
                mock_sock.connect_ex.side_effect = socket.gaierror("Name resolution failed")
                mock_socket.return_value = mock_sock

                assert is_china_network() is True
                mock_sock.close.assert_called_once()

    def test_china_detection_socket_os_error_exception(self):
        """Test China detection when OS error occurs."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("socket.socket") as mock_socket:
                # Mock OS error
                mock_sock = Mock()
                mock_sock.connect_ex.side_effect = OSError("Network unreachable")
                mock_socket.return_value = mock_sock

                assert is_china_network() is True
                mock_sock.close.assert_called_once()

    def test_china_detection_socket_creation_fails(self):
        """Test China detection when socket creation fails."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("socket.socket") as mock_socket:
                # Mock socket creation failure
                mock_socket.side_effect = OSError("Cannot create socket")

                assert is_china_network() is True


class TestCDNURLUsageWithChinaDetection:
    """Test CDN URL usage based on China network detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(cdn_url="https://fastfile.asfd.cn/")

    @patch("cdnbestip.speedtest.is_china_network")
    @patch("requests.get")
    def test_cdn_url_used_in_china_network(self, mock_requests, mock_china_detection):
        """Test CDN URL is used when in China network."""
        # Mock China network detection
        mock_china_detection.return_value = True

        # Mock GitHub API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "assets": [
                {
                    "name": "CloudflareSpeedTest_linux_amd64.tar.gz",
                    "browser_download_url": "https://github.com/user/repo/releases/download/v1.0/binary.tar.gz",
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        manager = SpeedTestManager(self.config)

        with patch.object(manager, "get_system_info", return_value=("linux", "amd64")):
            download_url = manager._get_download_url("linux", "amd64")

        # Should use CDN URL
        assert download_url.startswith("https://fastfile.asfd.cn/")

        # Check API call also used CDN URL
        expected_api_url = "https://fastfile.asfd.cn/https://api.github.com/repos/XIU2/CloudflareSpeedTest/releases/latest"
        mock_requests.assert_called_once_with(expected_api_url, timeout=30)

    @patch("cdnbestip.speedtest.is_china_network")
    @patch("requests.get")
    def test_cdn_url_not_used_outside_china(self, mock_requests, mock_china_detection):
        """Test CDN URL is not used when outside China network."""
        # Mock non-China network
        mock_china_detection.return_value = False

        # Mock GitHub API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "assets": [
                {
                    "name": "CloudflareSpeedTest_linux_amd64.tar.gz",
                    "browser_download_url": "https://github.com/user/repo/releases/download/v1.0/binary.tar.gz",
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        manager = SpeedTestManager(self.config)

        with patch.object(manager, "get_system_info", return_value=("linux", "amd64")):
            download_url = manager._get_download_url("linux", "amd64")

        # Should not use CDN URL
        assert download_url == "https://github.com/user/repo/releases/download/v1.0/binary.tar.gz"

        # Check API call did not use CDN URL
        expected_api_url = "https://api.github.com/repos/XIU2/CloudflareSpeedTest/releases/latest"
        mock_requests.assert_called_once_with(expected_api_url, timeout=30)

    @patch("cdnbestip.speedtest.is_china_network")
    @patch("requests.get")
    def test_cdn_url_not_used_when_not_configured(self, mock_requests, mock_china_detection):
        """Test CDN URL is not used when not configured, even in China."""
        # Mock China network detection
        mock_china_detection.return_value = True

        # Create config without CDN URL
        config = Config()
        config.cdn_url = ""

        # Mock GitHub API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "assets": [
                {
                    "name": "CloudflareSpeedTest_linux_amd64.tar.gz",
                    "browser_download_url": "https://github.com/user/repo/releases/download/v1.0/binary.tar.gz",
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        manager = SpeedTestManager(config)

        with patch.object(manager, "get_system_info", return_value=("linux", "amd64")):
            download_url = manager._get_download_url("linux", "amd64")

        # Should not use CDN URL
        assert download_url == "https://github.com/user/repo/releases/download/v1.0/binary.tar.gz"

        # Check API call did not use CDN URL
        expected_api_url = "https://api.github.com/repos/XIU2/CloudflareSpeedTest/releases/latest"
        mock_requests.assert_called_once_with(expected_api_url, timeout=30)

    @patch("cdnbestip.speedtest.is_china_network")
    @patch("requests.get")
    def test_cdn_url_environment_variable_override(self, mock_requests, mock_china_detection):
        """Test CDN URL can be overridden by environment variable."""
        # Mock China network detection
        mock_china_detection.return_value = True

        # Set CN=1 environment variable
        with patch.dict(os.environ, {"CN": "1"}):
            # Mock GitHub API response
            mock_response = Mock()
            mock_response.json.return_value = {
                "assets": [
                    {
                        "name": "CloudflareSpeedTest_linux_amd64.tar.gz",
                        "browser_download_url": "https://github.com/user/repo/releases/download/v1.0/binary.tar.gz",
                    }
                ]
            }
            mock_response.raise_for_status.return_value = None
            mock_requests.return_value = mock_response

            manager = SpeedTestManager(self.config)

            with patch.object(manager, "get_system_info", return_value=("linux", "amd64")):
                download_url = manager._get_download_url("linux", "amd64")

            # Should use CDN URL because CN=1
            assert download_url.startswith("https://fastfile.asfd.cn/")

    @patch("cdnbestip.speedtest.is_china_network")
    def test_china_detection_called_during_download_url_generation(self, mock_china_detection):
        """Test that China detection is called during download URL generation."""
        mock_china_detection.return_value = False

        manager = SpeedTestManager(self.config)

        with patch("requests.get") as mock_requests:
            # Mock GitHub API response
            mock_response = Mock()
            mock_response.json.return_value = {"assets": []}
            mock_response.raise_for_status.return_value = None
            mock_requests.return_value = mock_response

            with patch.object(manager, "get_system_info", return_value=("linux", "amd64")):
                manager._get_download_url("linux", "amd64")

            # Verify China detection was called
            mock_china_detection.assert_called_once()
