"""
Integration tests for binary download and execution.

This module tests the complete binary management workflow including
download, verification, and execution of the CloudflareSpeedTest binary.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from cdnbestip.config import Config
from cdnbestip.exceptions import BinaryError, SpeedTestError
from cdnbestip.speedtest import SpeedTestManager


class TestBinaryDownloadIntegration:
    """Test binary download integration scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config()
        self.config._skip_validation = True
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SpeedTestManager(self.config)
        self.manager.binary_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("requests.get")
    @patch("tarfile.open")
    @patch("shutil.copy2")
    def test_complete_binary_download_workflow(self, mock_copy, mock_tarfile, mock_requests):
        """Test complete binary download workflow."""
        # Mock GitHub API response
        github_response = Mock()
        github_response.json.return_value = {
            "tag_name": "v2.3.4",
            "assets": [
                {
                    "name": "CloudflareSpeedTest_linux_amd64.tar.gz",
                    "browser_download_url": "https://github.com/XIU2/CloudflareSpeedTest/releases/download/v2.3.4/CloudflareSpeedTest_linux_amd64.tar.gz",
                    "size": 1024000,
                }
            ],
        }
        github_response.raise_for_status.return_value = None

        # Mock binary download
        binary_response = Mock()
        binary_response.iter_content.return_value = [b"fake_binary_data"] * 100
        binary_response.raise_for_status.return_value = None

        def requests_side_effect(url, **kwargs):
            if "api.github.com" in url:
                return github_response
            else:
                return binary_response

        mock_requests.side_effect = requests_side_effect

        # Mock tarfile extraction
        mock_tar = Mock()
        mock_tarfile.return_value.__enter__.return_value = mock_tar

        # Mock file system operations
        with (
            patch("pathlib.Path.rglob") as mock_rglob,
            patch("pathlib.Path.is_file", return_value=True),
            patch("pathlib.Path.chmod"),
            patch("builtins.open"),
            patch("subprocess.run") as mock_subprocess,
        ):
            # Mock extracted binary file
            mock_file = Mock()
            mock_file.name = "cfst"
            mock_rglob.return_value = [mock_file]

            # Mock binary verification
            verify_result = Mock()
            verify_result.returncode = 0
            mock_subprocess.return_value = verify_result

            # Execute download workflow
            with patch("shutil.which", return_value=None):  # No system binary
                binary_path = self.manager.ensure_binary_available()

            assert binary_path.endswith("cfst")
            mock_copy.assert_called_once()
            mock_subprocess.assert_called_once()

    @patch("requests.get")
    def test_github_api_rate_limiting(self, mock_requests):
        """Test handling of GitHub API rate limiting."""
        # Mock rate limit response
        rate_limit_response = Mock()
        rate_limit_response.status_code = 403
        rate_limit_response.json.return_value = {
            "message": "API rate limit exceeded",
            "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting",
        }
        rate_limit_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")

        mock_requests.return_value = rate_limit_response

        with patch("shutil.which", return_value=None):
            with pytest.raises(BinaryError, match="Failed to get download URL"):
                self.manager.ensure_binary_available()

    @patch("requests.get")
    def test_binary_download_with_cdn_acceleration(self, mock_requests):
        """Test binary download with CDN acceleration."""
        self.config.cdn_url = "https://cdn.example.com/"

        # Mock GitHub API response
        github_response = Mock()
        github_response.json.return_value = {
            "assets": [
                {
                    "name": "CloudflareSpeedTest_linux_amd64.tar.gz",
                    "browser_download_url": "https://github.com/XIU2/CloudflareSpeedTest/releases/download/v2.3.4/CloudflareSpeedTest_linux_amd64.tar.gz",
                }
            ]
        }
        github_response.raise_for_status.return_value = None
        mock_requests.return_value = github_response

        with patch.object(self.manager, "get_system_info", return_value=("linux", "amd64")):
            download_url = self.manager._get_download_url("linux", "amd64")

        # Should use CDN URL
        assert download_url.startswith("https://cdn.example.com/")

    @patch("requests.get")
    def test_binary_download_network_interruption(self, mock_requests):
        """Test binary download with network interruption."""
        # Mock connection error during download
        mock_requests.side_effect = requests.ConnectionError("Network interrupted")

        with patch("shutil.which", return_value=None):
            with pytest.raises(BinaryError, match="Failed to get download URL"):
                self.manager.ensure_binary_available()

    def test_binary_verification_failure(self):
        """Test binary verification failure."""
        # Create a fake binary file
        fake_binary = self.manager.binary_dir / "cfst"
        fake_binary.touch()
        fake_binary.chmod(0o755)

        # Mock verification failure
        with patch("subprocess.run") as mock_subprocess:
            verify_result = Mock()
            verify_result.returncode = 1  # Verification failed
            mock_subprocess.return_value = verify_result

            assert not self.manager._verify_binary(str(fake_binary))


class TestBinaryExecutionIntegration:
    """Test binary execution integration scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config()
        self.config._skip_validation = True
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SpeedTestManager(self.config)
        self.manager.binary_path = "/usr/bin/cfst"  # Mock binary path

        # Create test files
        self.ip_file = os.path.join(self.temp_dir, "ips.txt")
        self.results_file = os.path.join(self.temp_dir, "results.csv")

        with open(self.ip_file, "w") as f:
            f.write("1.1.1.1\n1.0.0.1\n8.8.8.8\n")

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_speed_test_execution_with_all_parameters(self, mock_subprocess):
        """Test speed test execution with all configuration parameters."""
        # Configure all parameters
        self.config.speed_port = 8080
        self.config.speed_url = "https://test.example.com/speed"
        self.config.quantity = 5
        self.config.speed_threshold = 10.0
        self.config.extend_string = "--custom-param value"

        # Mock successful execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = "Speed test completed successfully"
        mock_subprocess.return_value = mock_result

        # Create expected results file
        with open(self.results_file, "w") as f:
            f.write("IP,Port,DataCenter,Region,City,Speed,Latency\n")
            f.write("1.1.1.1,443,LAX,US,LA,15.5,25.3\n")

        with patch("os.path.exists", return_value=True):
            result_file = self.manager.run_speed_test(self.ip_file, self.results_file)

        assert result_file == self.results_file

        # Verify command construction
        call_args = mock_subprocess.call_args[0][0]
        assert "/usr/bin/cfst" in call_args
        assert "-f" in call_args
        assert self.ip_file in call_args
        assert "-o" in call_args
        assert self.results_file in call_args
        assert "-tp" in call_args
        assert "8080" in call_args
        assert "-url" in call_args
        assert "https://test.example.com/speed" in call_args
        assert "-n" in call_args
        assert "5" in call_args
        assert "-sl" in call_args
        assert "10.0" in call_args

    @patch("subprocess.run")
    def test_speed_test_timeout_handling(self, mock_subprocess):
        """Test speed test timeout handling."""
        # Mock timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired(["cfst"], 300)

        with patch("os.path.exists", return_value=True):
            with pytest.raises(SpeedTestError, match="timed out"):
                self.manager.run_speed_test(self.ip_file, self.results_file)

    @patch("subprocess.run")
    def test_speed_test_binary_crash(self, mock_subprocess):
        """Test speed test binary crash handling."""
        # Mock binary crash
        mock_result = Mock()
        mock_result.returncode = -11  # SIGSEGV
        mock_result.stderr = "Segmentation fault"
        mock_subprocess.return_value = mock_result

        with patch("os.path.exists", return_value=True):
            with pytest.raises(SpeedTestError, match="failed with return code -11"):
                self.manager.run_speed_test(self.ip_file, self.results_file)

    @patch("subprocess.run")
    def test_speed_test_output_file_not_created(self, mock_subprocess):
        """Test handling when speed test doesn't create output file."""
        # Mock successful execution but no output file
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        with patch("os.path.exists", side_effect=lambda path: path == self.ip_file):
            with pytest.raises(SpeedTestError, match="output file not created"):
                self.manager.run_speed_test(self.ip_file, self.results_file)

    def test_speed_test_result_parsing_integration(self):
        """Test complete result parsing integration."""
        # Create comprehensive results file
        csv_content = """IP,Port,DataCenter,Region,City,Speed (MB/s),Latency (ms)
1.1.1.1,443,LAX,US-West,Los Angeles,15.50,25.30
1.0.0.1,80,LAX,US-West,Los Angeles,12.80,30.10
8.8.8.8,443,NYC,US-East,New York,18.70,45.20
8.8.4.4,53,NYC,US-East,New York,8.20,35.10
9.9.9.9,443,FRA,EU-Central,Frankfurt,22.10,55.80"""

        with open(self.results_file, "w") as f:
            f.write(csv_content)

        results = self.manager.parse_results(self.results_file)

        assert len(results) == 5

        # Verify first result
        assert results[0].ip == "1.1.1.1"
        assert results[0].port == 443
        assert results[0].data_center == "LAX"
        assert results[0].region == "US-West"
        assert results[0].city == "Los Angeles"
        assert results[0].speed == 15.50
        assert results[0].latency == 25.30

        # Verify different ports and data centers
        assert results[1].port == 80
        assert results[2].data_center == "NYC"
        assert results[4].region == "EU-Central"

    def test_speed_test_result_validation_integration(self):
        """Test result validation integration."""
        # Create results with various edge cases
        csv_content = """IP,Port,DataCenter,Region,City,Speed (MB/s),Latency (ms)
1.1.1.1,443,LAX,US,LA,15.5,25.3
,443,NYC,US,NY,12.8,30.1
8.8.8.8,443,FRA,EU,Frankfurt,-5.0,45.2
8.8.4.4,443,SJC,US,SJ,18.7,-10.0
9.9.9.9,443,DFW,US,Dallas,20.1,35.5"""

        with open(self.results_file, "w") as f:
            f.write(csv_content)

        results = self.manager.parse_results(self.results_file)
        valid_results = self.manager.validate_results(results)

        # Should filter out invalid results
        assert len(results) == 3  # Empty IP and negative values filtered during parsing
        assert len(valid_results) == 2  # Only valid results remain

        valid_ips = [r.ip for r in valid_results]
        assert "1.1.1.1" in valid_ips
        assert "9.9.9.9" in valid_ips


class TestBinaryVersionManagement:
    """Test binary version management and updates."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config()
        self.config._skip_validation = True
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SpeedTestManager(self.config)
        self.manager.binary_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_binary_version_detection(self, mock_subprocess):
        """Test binary version detection."""
        # Create fake binary
        fake_binary = self.manager.binary_dir / "cfst"
        fake_binary.touch()
        fake_binary.chmod(0o755)
        self.manager.binary_path = str(fake_binary)

        # Mock version output
        version_outputs = [
            "CloudflareSpeedTest v2.3.4",
            "CloudflareSpeedTest version 2.3.4",
            "cfst v2.3.4 (build 12345)",
            "Version: 2.3.4",
        ]

        for output in version_outputs:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = output
            mock_subprocess.return_value = mock_result

            version = self.manager.get_binary_version()
            assert version == "2.3.4"

    @patch("subprocess.run")
    def test_binary_version_update_check(self, mock_subprocess):
        """Test binary version update check."""
        fake_binary = self.manager.binary_dir / "cfst"
        fake_binary.touch()
        fake_binary.chmod(0o755)
        self.manager.binary_path = str(fake_binary)

        # Test with outdated version
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "CloudflareSpeedTest v2.3.3"  # Older version
        mock_subprocess.return_value = mock_result

        with patch.object(
            self.manager, "_download_and_install_binary", return_value="/new/cfst"
        ) as mock_download:
            updated = self.manager.update_binary()
            assert updated is True
            mock_download.assert_called_once()

        # Test with current version
        mock_result.stdout = "CloudflareSpeedTest v2.3.4"  # Current version
        updated = self.manager.update_binary()
        assert updated is False

    @patch("subprocess.run")
    def test_binary_version_no_version_info(self, mock_subprocess):
        """Test binary with no version information."""
        fake_binary = self.manager.binary_dir / "cfst"
        fake_binary.touch()
        fake_binary.chmod(0o755)
        self.manager.binary_path = str(fake_binary)

        # Mock no version output
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        version = self.manager.get_binary_version()
        assert version is None

        # Should force update when no version info
        with patch.object(
            self.manager, "_download_and_install_binary", return_value="/new/cfst"
        ) as mock_download:
            updated = self.manager.update_binary()
            assert updated is True
            mock_download.assert_called_once()


class TestBinaryPlatformCompatibility:
    """Test binary platform compatibility and detection."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config()
        self.config._skip_validation = True
        self.manager = SpeedTestManager(self.config)

    def test_system_info_detection_variations(self):
        """Test system information detection for various platforms."""
        platform_scenarios = [
            # (system, machine) -> (expected_os, expected_arch)
            (("Linux", "x86_64"), ("linux", "amd64")),
            (("Linux", "amd64"), ("linux", "amd64")),
            (("Linux", "i386"), ("linux", "386")),
            (("Linux", "i686"), ("linux", "386")),
            (("Linux", "aarch64"), ("linux", "arm64")),
            (("Linux", "arm64"), ("linux", "arm64")),
            (("Linux", "armv7l"), ("linux", "armv6l")),
            (("Darwin", "x86_64"), ("darwin", "amd64")),
            (("Darwin", "arm64"), ("darwin", "arm64")),
            (("Windows", "AMD64"), ("windows", "amd64")),
            (("Windows", "x86"), ("windows", "386")),
        ]

        for (system, machine), (expected_os, expected_arch) in platform_scenarios:
            with (
                patch("platform.system", return_value=system),
                patch("platform.machine", return_value=machine),
            ):
                os_name, arch = self.manager.get_system_info()
                assert os_name == expected_os, f"Failed for {system}/{machine}"
                assert arch == expected_arch, f"Failed for {system}/{machine}"

    @patch("requests.get")
    def test_binary_availability_for_platforms(self, mock_requests):
        """Test binary availability check for different platforms."""
        # Mock GitHub API response with various platform binaries
        github_response = Mock()
        github_response.json.return_value = {
            "assets": [
                {
                    "name": "CloudflareSpeedTest_linux_amd64.tar.gz",
                    "browser_download_url": "https://example.com/linux_amd64.tar.gz",
                },
                {
                    "name": "CloudflareSpeedTest_linux_386.tar.gz",
                    "browser_download_url": "https://example.com/linux_386.tar.gz",
                },
                {
                    "name": "CloudflareSpeedTest_linux_arm64.tar.gz",
                    "browser_download_url": "https://example.com/linux_arm64.tar.gz",
                },
                {
                    "name": "CloudflareSpeedTest_darwin_amd64.tar.gz",
                    "browser_download_url": "https://example.com/darwin_amd64.tar.gz",
                },
                {
                    "name": "CloudflareSpeedTest_darwin_arm64.tar.gz",
                    "browser_download_url": "https://example.com/darwin_arm64.tar.gz",
                },
                {
                    "name": "CloudflareSpeedTest_windows_amd64.tar.gz",
                    "browser_download_url": "https://example.com/windows_amd64.tar.gz",
                },
                {
                    "name": "CloudflareSpeedTest_windows_386.tar.gz",
                    "browser_download_url": "https://example.com/windows_386.tar.gz",
                },
            ]
        }
        github_response.raise_for_status.return_value = None
        mock_requests.return_value = github_response

        supported_platforms = [
            ("linux", "amd64"),
            ("linux", "386"),
            ("linux", "arm64"),
            ("darwin", "amd64"),
            ("darwin", "arm64"),
            ("windows", "amd64"),
            ("windows", "386"),
        ]

        for os_name, arch in supported_platforms:
            url = self.manager._get_download_url(os_name, arch)
            assert url is not None, f"No binary available for {os_name}/{arch}"
            assert f"{os_name}_{arch}" in url

        # Test unsupported platform
        url = self.manager._get_download_url("freebsd", "amd64")
        assert url is None


if __name__ == "__main__":
    pytest.main([__file__])
