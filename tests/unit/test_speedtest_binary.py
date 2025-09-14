"""Unit tests for CloudflareSpeedTest binary management."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
import requests

from cdnbestip.config import Config
from cdnbestip.exceptions import BinaryError
from cdnbestip.speedtest import SpeedTestManager


class TestSpeedTestBinaryManagement:
    """Test CloudflareSpeedTest binary management functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.manager = SpeedTestManager(self.config)

    def test_get_system_info_linux_amd64(self):
        """Test system info detection for Linux AMD64."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="x86_64"),
        ):
            os_name, arch = self.manager.get_system_info()
            assert os_name == "linux"
            assert arch == "amd64"

    def test_get_system_info_darwin_arm64(self):
        """Test system info detection for macOS ARM64."""
        with (
            patch("platform.system", return_value="Darwin"),
            patch("platform.machine", return_value="arm64"),
        ):
            os_name, arch = self.manager.get_system_info()
            assert os_name == "darwin"
            assert arch == "arm64"

    def test_get_system_info_windows_386(self):
        """Test system info detection for Windows 386."""
        with (
            patch("platform.system", return_value="Windows"),
            patch("platform.machine", return_value="i386"),
        ):
            os_name, arch = self.manager.get_system_info()
            assert os_name == "windows"
            assert arch == "386"

    def test_find_existing_binary_found(self):
        """Test finding existing binary in PATH."""
        with patch("shutil.which", side_effect=lambda x: "/usr/bin/cfst" if x == "cfst" else None):
            binary = self.manager._find_existing_binary()
            assert binary == "cfst"

    def test_find_existing_binary_not_found(self):
        """Test when no existing binary is found."""
        with patch("shutil.which", return_value=None):
            binary = self.manager._find_existing_binary()
            assert binary is None

    def test_verify_binary_working(self):
        """Test binary verification when binary is working."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            assert self.manager._verify_binary("/path/to/binary") is True

    def test_verify_binary_not_working(self):
        """Test binary verification when binary is not working."""
        mock_result = Mock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            assert self.manager._verify_binary("/path/to/binary") is False

    def test_verify_binary_file_not_found(self):
        """Test binary verification when binary file is not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert self.manager._verify_binary("/path/to/binary") is False

    def test_get_cached_binary_path_exists(self):
        """Test getting cached binary path when it exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.manager.binary_dir = Path(temp_dir)
            binary_path = self.manager.binary_dir / "cfst"
            binary_path.touch()

            cached_path = self.manager._get_cached_binary_path()
            assert cached_path == str(binary_path)

    def test_get_cached_binary_path_not_exists(self):
        """Test getting cached binary path when it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.manager.binary_dir = Path(temp_dir)

            cached_path = self.manager._get_cached_binary_path()
            assert cached_path is None

    @patch("requests.get")
    def test_get_download_url_success(self, mock_get):
        """Test successful download URL retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "assets": [
                {
                    "name": "CloudflareSpeedTest_linux_amd64.tar.gz",
                    "browser_download_url": "https://github.com/XIU2/CloudflareSpeedTest/releases/download/v2.3.4/CloudflareSpeedTest_linux_amd64.tar.gz",
                }
            ]
        }
        mock_get.return_value = mock_response

        with patch.object(self.manager, "get_system_info", return_value=("linux", "amd64")):
            url = self.manager._get_download_url("linux", "amd64")
            assert "CloudflareSpeedTest_linux_amd64.tar.gz" in url

    @patch("requests.get")
    def test_get_download_url_no_matching_asset(self, mock_get):
        """Test download URL retrieval when no matching asset is found."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "assets": [
                {
                    "name": "CloudflareSpeedTest_windows_amd64.tar.gz",
                    "browser_download_url": "https://example.com/windows.tar.gz",
                }
            ]
        }
        mock_get.return_value = mock_response

        url = self.manager._get_download_url("linux", "amd64")
        assert url is None

    @patch("requests.get")
    def test_get_download_url_request_error(self, mock_get):
        """Test download URL retrieval when request fails."""
        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(BinaryError, match="Failed to get download URL"):
            self.manager._get_download_url("linux", "amd64")

    def test_ensure_binary_available_existing_system_binary(self):
        """Test ensuring binary availability when system binary exists."""
        with patch.object(self.manager, "_find_existing_binary", return_value="cfst"):
            binary_path = self.manager.ensure_binary_available()
            assert binary_path == "cfst"
            assert self.manager.binary_path == "cfst"

    def test_ensure_binary_available_cached_binary(self):
        """Test ensuring binary availability when cached binary exists."""
        with (
            patch.object(self.manager, "_find_existing_binary", return_value=None),
            patch.object(self.manager, "_get_cached_binary_path", return_value="/cache/cfst"),
            patch.object(self.manager, "_verify_binary", return_value=True),
        ):
            binary_path = self.manager.ensure_binary_available()
            assert binary_path == "/cache/cfst"
            assert self.manager.binary_path == "/cache/cfst"

    def test_ensure_binary_available_download_required(self):
        """Test ensuring binary availability when download is required."""
        with (
            patch.object(self.manager, "_find_existing_binary", return_value=None),
            patch.object(self.manager, "_get_cached_binary_path", return_value=None),
            patch.object(self.manager, "_download_and_install_binary", return_value="/new/cfst"),
        ):
            binary_path = self.manager.ensure_binary_available()
            assert binary_path == "/new/cfst"

    @patch("tempfile.TemporaryDirectory")
    @patch("requests.get")
    @patch("tarfile.open")
    @patch("shutil.copy2")
    def test_download_binary_success(self, mock_copy, mock_tarfile, mock_get, mock_tempdir):
        """Test successful binary download and extraction."""
        # Setup mocks
        temp_dir = Path("/tmp/test")
        mock_tempdir.return_value.__enter__.return_value = str(temp_dir)

        mock_response = Mock()
        mock_response.iter_content.return_value = [b"fake_data"]
        mock_get.return_value = mock_response

        mock_tar = Mock()
        mock_tarfile.return_value.__enter__.return_value = mock_tar

        # Mock file system
        with (
            patch("pathlib.Path.rglob") as mock_rglob,
            patch("pathlib.Path.is_file", return_value=True),
            patch("pathlib.Path.chmod"),
            patch("builtins.open", mock_open()),
        ):
            mock_file = Mock()
            mock_file.name = "cfst"
            mock_rglob.return_value = [mock_file]

            with tempfile.TemporaryDirectory() as real_temp_dir:
                self.manager.binary_dir = Path(real_temp_dir)

                result = self.manager._download_binary(
                    "https://example.com/binary.tar.gz", "linux", "amd64"
                )

                assert result.endswith("cfst")
                mock_copy.assert_called_once()

    @patch("subprocess.run")
    def test_get_binary_version_success(self, mock_run):
        """Test successful binary version retrieval."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "CloudflareSpeedTest v2.3.4"
        mock_run.return_value = mock_result

        self.manager.binary_path = "/path/to/cfst"
        version = self.manager.get_binary_version()
        assert version == "2.3.4"

    @patch("subprocess.run")
    def test_get_binary_version_no_version_info(self, mock_run):
        """Test binary version retrieval when no version info is available."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        self.manager.binary_path = "/path/to/cfst"
        version = self.manager.get_binary_version()
        assert version is None

    def test_get_binary_version_no_binary_path(self):
        """Test binary version retrieval when no binary path is set."""
        version = self.manager.get_binary_version()
        assert version is None

    def test_update_binary_version_mismatch(self):
        """Test binary update when version doesn't match."""
        with (
            patch.object(self.manager, "get_binary_version", return_value="2.3.3"),
            patch.object(self.manager, "_download_and_install_binary", return_value="/new/cfst"),
        ):
            updated = self.manager.update_binary()
            assert updated is True

    def test_update_binary_same_version(self):
        """Test binary update when version matches."""
        with patch.object(self.manager, "get_binary_version", return_value="2.3.4"):
            updated = self.manager.update_binary()
            assert updated is False

    def test_update_binary_no_version_info(self):
        """Test binary update when no version info is available."""
        with (
            patch.object(self.manager, "get_binary_version", return_value=None),
            patch.object(self.manager, "_download_and_install_binary", return_value="/new/cfst"),
        ):
            updated = self.manager.update_binary()
            assert updated is True

    def test_update_binary_download_fails(self):
        """Test binary update when download fails."""
        with (
            patch.object(self.manager, "get_binary_version", return_value="2.3.3"),
            patch.object(
                self.manager,
                "_download_and_install_binary",
                side_effect=BinaryError("Download failed"),
            ),
        ):
            updated = self.manager.update_binary()
            assert updated is False
