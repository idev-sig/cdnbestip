"""Unit tests for Windows compression handling functionality."""

import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, "src")

from cdnbestip.config import Config
from cdnbestip.exceptions import BinaryError
from cdnbestip.speedtest import SpeedTestManager


class TestWindowsCompressionHandling:
    """Test Windows zip file and tar.gz file handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.manager = SpeedTestManager(self.config)

    def create_test_zip(self, temp_dir, binary_name="cfst.exe"):
        """Helper to create a test zip file with binary."""
        zip_path = Path(temp_dir) / "test.zip"
        binary_content = b"fake binary content"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(binary_name, binary_content)

        return zip_path

    def create_test_tar_gz(self, temp_dir, binary_name="cfst"):
        """Helper to create a test tar.gz file with binary."""
        tar_path = Path(temp_dir) / "test.tar.gz"
        binary_content = b"fake binary content"

        with tarfile.open(tar_path, "w:gz") as tf:
            import io

            tarinfo = tarfile.TarInfo(name=binary_name)
            tarinfo.size = len(binary_content)
            tf.addfile(tarinfo, io.BytesIO(binary_content))

        return tar_path

    @patch("requests.get")
    def test_download_binary_zip_file_detection(self, mock_requests):
        """Test zip file detection from URL extension."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test zip file
            zip_path = self.create_test_zip(temp_dir)

            # Mock HTTP response
            with open(zip_path, "rb") as f:
                zip_content = f.read()

            mock_response = Mock()
            mock_response.iter_content.return_value = [zip_content]
            mock_response.raise_for_status.return_value = None
            mock_requests.return_value = mock_response

            # Test with .zip URL
            download_url = "https://example.com/binary.zip"

            with patch("pathlib.Path.chmod"):  # Mock chmod for Windows compatibility
                binary_path = self.manager._download_binary(download_url, "windows", "amd64")

            # Should successfully extract and return binary path
            assert binary_path.endswith("cfst.exe")
            assert Path(binary_path).exists()

    @patch("requests.get")
    def test_download_binary_tar_gz_file_detection(self, mock_requests):
        """Test tar.gz file detection from URL extension."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test tar.gz file
            tar_path = self.create_test_tar_gz(temp_dir)

            # Mock HTTP response
            with open(tar_path, "rb") as f:
                tar_content = f.read()

            mock_response = Mock()
            mock_response.iter_content.return_value = [tar_content]
            mock_response.raise_for_status.return_value = None
            mock_requests.return_value = mock_response

            # Test with .tar.gz URL
            download_url = "https://example.com/binary.tar.gz"

            with patch("pathlib.Path.chmod"):  # Mock chmod for Unix compatibility
                binary_path = self.manager._download_binary(download_url, "linux", "amd64")

            # Should successfully extract and return binary path
            assert binary_path.endswith("cfst")
            assert Path(binary_path).exists()

    @patch("requests.get")
    def test_download_binary_zip_extraction(self, mock_requests):
        """Test successful zip file extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test zip with specific binary name
            zip_path = self.create_test_zip(temp_dir, "CloudflareSpeedTest.exe")

            # Mock HTTP response
            with open(zip_path, "rb") as f:
                zip_content = f.read()

            mock_response = Mock()
            mock_response.iter_content.return_value = [zip_content]
            mock_response.raise_for_status.return_value = None
            mock_requests.return_value = mock_response

            download_url = "https://example.com/CloudflareSpeedTest_windows_amd64.zip"

            with patch("pathlib.Path.chmod"):
                binary_path = self.manager._download_binary(download_url, "windows", "amd64")

            # Should find and extract the binary
            assert Path(binary_path).exists()
            assert binary_path.endswith("cfst.exe")

    @patch("requests.get")
    def test_download_binary_tar_gz_extraction(self, mock_requests):
        """Test successful tar.gz file extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test tar.gz with specific binary name
            tar_path = self.create_test_tar_gz(temp_dir, "CloudflareSpeedTest")

            # Mock HTTP response
            with open(tar_path, "rb") as f:
                tar_content = f.read()

            mock_response = Mock()
            mock_response.iter_content.return_value = [tar_content]
            mock_response.raise_for_status.return_value = None
            mock_requests.return_value = mock_response

            download_url = "https://example.com/CloudflareSpeedTest_linux_amd64.tar.gz"

            with patch("pathlib.Path.chmod"):
                binary_path = self.manager._download_binary(download_url, "linux", "amd64")

            # Should find and extract the binary
            assert Path(binary_path).exists()
            assert binary_path.endswith("cfst")

    @patch("requests.get")
    def test_download_binary_bad_zip_file(self, mock_requests):
        """Test handling of corrupted zip file."""
        # Mock HTTP response with invalid zip content
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"not a zip file"]
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        download_url = "https://example.com/corrupted.zip"

        with pytest.raises(BinaryError, match="Failed to download binary"):
            self.manager._download_binary(download_url, "windows", "amd64")

    @patch("requests.get")
    def test_download_binary_bad_tar_file(self, mock_requests):
        """Test handling of corrupted tar.gz file."""
        # Mock HTTP response with invalid tar content
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"not a tar file"]
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        download_url = "https://example.com/corrupted.tar.gz"

        with pytest.raises(BinaryError, match="Failed to download binary"):
            self.manager._download_binary(download_url, "linux", "amd64")

    @patch("requests.get")
    def test_download_binary_no_binary_found_in_archive(self, mock_requests):
        """Test handling when no binary is found in archive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create zip with non-binary file
            zip_path = Path(temp_dir) / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("readme.txt", "This is a readme file")

            # Mock HTTP response
            with open(zip_path, "rb") as f:
                zip_content = f.read()

            mock_response = Mock()
            mock_response.iter_content.return_value = [zip_content]
            mock_response.raise_for_status.return_value = None
            mock_requests.return_value = mock_response

            download_url = "https://example.com/no_binary.zip"

            with pytest.raises(BinaryError, match="Binary not found in downloaded archive"):
                self.manager._download_binary(download_url, "windows", "amd64")

    def test_binary_name_windows_vs_unix(self):
        """Test binary naming convention for different platforms."""
        # Test Windows binary naming
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = self.create_test_zip(temp_dir, "cfst.exe")

            with zipfile.ZipFile(zip_path, "r") as zf:
                extracted_files = zf.namelist()

            # Should find Windows executable
            assert "cfst.exe" in extracted_files

        # Test Unix binary naming
        with tempfile.TemporaryDirectory() as temp_dir:
            tar_path = self.create_test_tar_gz(temp_dir, "cfst")

            with tarfile.open(tar_path, "r:gz") as tf:
                extracted_files = tf.getnames()

            # Should find Unix executable
            assert "cfst" in extracted_files

    @patch("requests.get")
    def test_download_binary_chmod_called_for_unix(self, mock_requests):
        """Test that chmod is called for Unix platforms but not Windows."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tar_path = self.create_test_tar_gz(temp_dir)

            with open(tar_path, "rb") as f:
                tar_content = f.read()

            mock_response = Mock()
            mock_response.iter_content.return_value = [tar_content]
            mock_response.raise_for_status.return_value = None
            mock_requests.return_value = mock_response

            download_url = "https://example.com/binary.tar.gz"

            with patch("pathlib.Path.chmod") as mock_chmod:
                self.manager._download_binary(download_url, "linux", "amd64")
                # Should call chmod for Unix
                mock_chmod.assert_called_once_with(0o755)

            with patch("pathlib.Path.chmod") as mock_chmod:
                # Create zip for Windows test
                zip_path = self.create_test_zip(temp_dir)
                with open(zip_path, "rb") as f:
                    zip_content = f.read()
                mock_response.iter_content.return_value = [zip_content]

                download_url = "https://example.com/binary.zip"
                self.manager._download_binary(download_url, "windows", "amd64")
                # Should not call chmod for Windows
                mock_chmod.assert_not_called()
