"""
Integration tests for end-to-end workflows.

This module tests complete workflows from speed testing to DNS updates,
including error handling and recovery scenarios.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from cdnbestip.config import Config
from cdnbestip.dns import DNSManager
from cdnbestip.exceptions import (
    AuthenticationError,
    BinaryError,
    IPSourceError,
    SpeedTestError,
)
from cdnbestip.ip_sources import IPSourceManager
from cdnbestip.models import SpeedTestResult
from cdnbestip.results import ResultsHandler
from cdnbestip.speedtest import SpeedTestManager


class TestSpeedTestToDNSWorkflow:
    """Test complete speed test to DNS update workflow."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config(
            cloudflare_api_token="test_token",
            domain="example.com",
            prefix="cf",
            speed_threshold=2.0,
            quantity=3,
            update_dns=True,
        )
        self.config._skip_validation = True

        self.temp_dir = tempfile.mkdtemp()
        self.ip_file = os.path.join(self.temp_dir, "ips.txt")
        self.results_file = os.path.join(self.temp_dir, "results.csv")

        # Create sample IP file
        with open(self.ip_file, "w") as f:
            f.write("1.1.1.1\n1.0.0.1\n8.8.8.8\n8.8.4.4\n")

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("cdnbestip.speedtest.subprocess.run")
    @patch("cdnbestip.dns.Cloudflare")
    def test_complete_workflow_success(self, mock_cloudflare, mock_subprocess):
        """Test successful complete workflow from speed test to DNS update."""
        # Mock speed test execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Create mock results file
        csv_content = """IP,Port,DataCenter,Region,City,Speed,Latency
1.1.1.1,443,LAX,US-West,Los Angeles,15.5,25.3
1.0.0.1,443,LAX,US-West,Los Angeles,12.8,30.1
8.8.8.8,443,NYC,US-East,New York,18.7,45.2
8.8.4.4,443,NYC,US-East,New York,8.2,35.1"""

        with open(self.results_file, "w") as f:
            f.write(csv_content)

        # Mock CloudFlare API
        mock_client = Mock()
        mock_cloudflare.return_value = mock_client

        # Mock authentication
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_client.user.get.return_value = mock_user

        # Mock zone operations
        mock_zone = Mock()
        mock_zone.id = "zone123"
        mock_zone.name = "example.com"
        mock_zones = Mock()
        mock_zones.result = [mock_zone]
        mock_client.zones.list.return_value = mock_zones

        # Mock DNS record operations
        mock_records = Mock()
        mock_records.result = []  # No existing records
        mock_client.zones.dns_records.list.return_value = mock_records

        # Mock record creation
        def create_record_side_effect(**kwargs):
            mock_record = Mock()
            mock_record.id = f"record_{kwargs['name']}"
            mock_record.name = kwargs["name"]
            mock_record.content = kwargs["content"]
            mock_record.type = kwargs["type"]
            return mock_record

        mock_client.zones.dns_records.create.side_effect = create_record_side_effect

        # Execute workflow
        speed_manager = SpeedTestManager(self.config)
        speed_manager.binary_path = "/usr/bin/cfst"  # Mock binary path

        dns_manager = DNSManager(self.config)
        results_handler = ResultsHandler(self.config)

        # Step 1: Run speed test
        with patch("os.path.exists", return_value=True):
            result_file = speed_manager.run_speed_test(self.ip_file, self.results_file)
            assert result_file == self.results_file

        # Step 2: Parse results
        results = speed_manager.parse_results(result_file)
        assert len(results) == 4

        # Step 3: Filter and get top IPs
        top_ips = results_handler.get_top_ips(results, self.config.quantity)
        assert len(top_ips) == 3  # Limited by quantity
        assert top_ips[0] == "8.8.8.8"  # Fastest

        # Step 4: Authenticate with CloudFlare
        dns_manager.authenticate()
        assert dns_manager.is_authenticated()

        # Step 5: Get zone ID
        zone_id = dns_manager.get_zone_id("example.com")
        assert zone_id == "zone123"

        # Step 6: Update DNS records
        updated_records = []
        for i, ip in enumerate(top_ips, 1):
            record = dns_manager.upsert_record(
                zone_id=zone_id, name=f"cf{i}.example.com", content=ip, record_type="A"
            )
            updated_records.append(record)

        assert len(updated_records) == 3
        assert updated_records[0].content == "8.8.8.8"
        assert updated_records[1].content == "1.1.1.1"
        assert updated_records[2].content == "1.0.0.1"

        # Verify API calls
        mock_client.zones.dns_records.create.assert_called()
        assert mock_client.zones.dns_records.create.call_count == 3

    @patch("cdnbestip.speedtest.subprocess.run")
    def test_workflow_speed_test_failure(self, mock_subprocess):
        """Test workflow when speed test fails."""
        # Mock speed test failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Speed test failed"
        mock_subprocess.return_value = mock_result

        speed_manager = SpeedTestManager(self.config)
        speed_manager.binary_path = "/usr/bin/cfst"

        with patch("os.path.exists", return_value=True):
            with pytest.raises(SpeedTestError, match="Speed test failed"):
                speed_manager.run_speed_test(self.ip_file, self.results_file)

    @patch("cdnbestip.dns.Cloudflare")
    def test_workflow_dns_authentication_failure(self, mock_cloudflare):
        """Test workflow when DNS authentication fails."""
        # Mock authentication failure
        mock_client = Mock()
        mock_cloudflare.return_value = mock_client

        import cloudflare

        mock_response = Mock()
        mock_client.user.get.side_effect = cloudflare.AuthenticationError(
            message="Invalid token", response=mock_response, body=None
        )

        dns_manager = DNSManager(self.config)

        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            dns_manager.authenticate()

    @patch("cdnbestip.speedtest.subprocess.run")
    @patch("cdnbestip.dns.Cloudflare")
    def test_workflow_partial_dns_update_failure(self, mock_cloudflare, mock_subprocess):
        """Test workflow when some DNS updates fail."""
        # Mock successful speed test
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Create results file
        csv_content = """IP,Port,DataCenter,Region,City,Speed,Latency
1.1.1.1,443,LAX,US-West,Los Angeles,15.5,25.3
1.0.0.1,443,LAX,US-West,Los Angeles,12.8,30.1"""

        with open(self.results_file, "w") as f:
            f.write(csv_content)

        # Mock CloudFlare API with partial failure
        mock_client = Mock()
        mock_cloudflare.return_value = mock_client

        # Mock authentication
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_client.user.get.return_value = mock_user

        # Mock zone operations
        mock_zone = Mock()
        mock_zone.id = "zone123"
        mock_zones = Mock()
        mock_zones.result = [mock_zone]
        mock_client.zones.list.return_value = mock_zones

        # Mock DNS record operations with failure on second record
        mock_records = Mock()
        mock_records.result = []
        mock_client.zones.dns_records.list.return_value = mock_records

        def create_record_side_effect(**kwargs):
            if "cf2" in kwargs["name"]:
                import cloudflare

                mock_response = Mock()
                raise cloudflare.APIError(
                    message="Rate limit exceeded", response=mock_response, body=None
                )

            mock_record = Mock()
            mock_record.id = f"record_{kwargs['name']}"
            mock_record.name = kwargs["name"]
            mock_record.content = kwargs["content"]
            return mock_record

        mock_client.zones.dns_records.create.side_effect = create_record_side_effect

        # Execute workflow
        speed_manager = SpeedTestManager(self.config)
        speed_manager.binary_path = "/usr/bin/cfst"
        dns_manager = DNSManager(self.config)
        results_handler = ResultsHandler(self.config)

        # Run speed test and parse results
        with patch("os.path.exists", return_value=True):
            speed_manager.run_speed_test(self.ip_file, self.results_file)

        results = speed_manager.parse_results(self.results_file)
        top_ips = results_handler.get_top_ips(results, 2)

        dns_manager.authenticate()
        zone_id = dns_manager.get_zone_id("example.com")

        # Batch update should handle partial failures
        updated_records = dns_manager.batch_upsert_records(
            zone_id=zone_id, base_name="cf", ip_addresses=top_ips
        )

        # Should have 1 successful record (cf1), cf2 failed
        assert len(updated_records) == 1
        assert updated_records[0].content == "1.1.1.1"


class TestIPSourceToSpeedTestWorkflow:
    """Test IP source download to speed test workflow."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config()
        self.config._skip_validation = True
        self.temp_dir = tempfile.mkdtemp()
        self.ip_file = os.path.join(self.temp_dir, "ips.txt")

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("requests.get")
    @patch("cdnbestip.speedtest.subprocess.run")
    def test_ip_download_to_speed_test_workflow(self, mock_subprocess, mock_requests):
        """Test complete workflow from IP download to speed test."""
        # Mock IP source download
        mock_response = Mock()
        mock_response.text = "1.1.1.1\n1.0.0.1\n8.8.8.8\n8.8.4.4\n"
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock speed test execution
        mock_subprocess_result = Mock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stderr = ""
        mock_subprocess.return_value = mock_subprocess_result

        # Execute workflow
        ip_manager = IPSourceManager(self.config)
        speed_manager = SpeedTestManager(self.config)
        speed_manager.binary_path = "/usr/bin/cfst"

        # Step 1: Download IP list
        ip_manager.download_ip_list("cf", self.ip_file, force_refresh=True)

        # Verify IP file was created
        assert os.path.exists(self.ip_file)
        with open(self.ip_file) as f:
            content = f.read()
            assert "1.1.1.1" in content
            assert "8.8.8.8" in content

        # Step 2: Run speed test with downloaded IPs
        results_file = os.path.join(self.temp_dir, "results.csv")

        with patch("os.path.exists", return_value=True):
            result_file = speed_manager.run_speed_test(self.ip_file, results_file)
            assert result_file == results_file

        # Verify speed test was called with correct IP file
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert self.ip_file in call_args

    @patch("requests.get")
    def test_ip_download_network_failure(self, mock_requests):
        """Test IP download workflow with network failure."""
        # Mock network failure
        mock_requests.side_effect = requests.ConnectionError("Network error")

        ip_manager = IPSourceManager(self.config)

        with pytest.raises(IPSourceError, match="Network error"):
            ip_manager.download_ip_list("cf", self.ip_file, force_refresh=True)

    @patch("requests.get")
    def test_ip_download_invalid_response(self, mock_requests):
        """Test IP download workflow with invalid response."""
        # Mock invalid response
        mock_response = Mock()
        mock_response.text = "invalid response format"
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        ip_manager = IPSourceManager(self.config)

        # Should still create file but with invalid content
        ip_manager.download_ip_list("cf", self.ip_file, force_refresh=True)

        assert os.path.exists(self.ip_file)
        with open(self.ip_file) as f:
            content = f.read()
            assert "invalid response format" in content


class TestBinaryDownloadToSpeedTestWorkflow:
    """Test binary download to speed test workflow."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config()
        self.config._skip_validation = True
        self.temp_dir = tempfile.mkdtemp()
        self.ip_file = os.path.join(self.temp_dir, "ips.txt")

        # Create IP file
        with open(self.ip_file, "w") as f:
            f.write("1.1.1.1\n1.0.0.1\n")

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("requests.get")
    @patch("tarfile.open")
    @patch("shutil.copy2")
    @patch("cdnbestip.speedtest.subprocess.run")
    def test_binary_download_to_speed_test_workflow(
        self, mock_subprocess, mock_copy, mock_tarfile, mock_requests
    ):
        """Test complete workflow from binary download to speed test."""
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

        # Mock binary download
        binary_response = Mock()
        binary_response.iter_content.return_value = [b"fake_binary_data"]
        binary_response.raise_for_status.return_value = None

        # Mock requests to return appropriate response
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
        ):
            mock_file = Mock()
            mock_file.name = "cfst"
            mock_rglob.return_value = [mock_file]

            # Mock binary verification
            verify_result = Mock()
            verify_result.returncode = 0

            # Mock speed test execution
            speed_result = Mock()
            speed_result.returncode = 0
            speed_result.stderr = ""

            def subprocess_side_effect(cmd, **kwargs):
                if "-h" in cmd:
                    return verify_result
                else:
                    return speed_result

            mock_subprocess.side_effect = subprocess_side_effect

            # Execute workflow
            speed_manager = SpeedTestManager(self.config)
            speed_manager.binary_dir = Path(self.temp_dir)

            # Step 1: Ensure binary is available (should download)
            with patch("shutil.which", return_value=None):  # No system binary
                binary_path = speed_manager.ensure_binary_available()
                assert binary_path.endswith("cfst")

            # Step 2: Run speed test with downloaded binary
            results_file = os.path.join(self.temp_dir, "results.csv")

            with patch("os.path.exists", return_value=True):
                result_file = speed_manager.run_speed_test(self.ip_file, results_file)
                assert result_file == results_file

            # Verify binary was downloaded and used
            mock_copy.assert_called_once()
            assert mock_subprocess.call_count >= 2  # Verification + speed test

    @patch("requests.get")
    def test_binary_download_failure(self, mock_requests):
        """Test binary download failure handling."""
        # Mock GitHub API failure
        mock_requests.side_effect = requests.RequestException("API error")

        speed_manager = SpeedTestManager(self.config)

        with patch("shutil.which", return_value=None):  # No system binary
            with pytest.raises(BinaryError, match="Failed to get download URL"):
                speed_manager.ensure_binary_available()

    @patch("requests.get")
    def test_binary_no_matching_platform(self, mock_requests):
        """Test binary download when no matching platform is available."""
        # Mock GitHub API response with no matching assets
        mock_response = Mock()
        mock_response.json.return_value = {
            "assets": [
                {
                    "name": "CloudflareSpeedTest_windows_amd64.tar.gz",
                    "browser_download_url": "https://example.com/windows.tar.gz",
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        speed_manager = SpeedTestManager(self.config)

        with patch("shutil.which", return_value=None):  # No system binary
            with patch.object(speed_manager, "get_system_info", return_value=("linux", "amd64")):
                with pytest.raises(BinaryError, match="No binary available"):
                    speed_manager.ensure_binary_available()


class TestErrorRecoveryWorkflows:
    """Test error recovery and retry workflows."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config(
            cloudflare_api_token="test_token", domain="example.com", prefix="cf", update_dns=True
        )
        self.config._skip_validation = True

    @patch("cdnbestip.dns.Cloudflare")
    def test_dns_retry_on_rate_limit(self, mock_cloudflare):
        """Test DNS operation retry on rate limit."""
        mock_client = Mock()
        mock_cloudflare.return_value = mock_client

        # Mock authentication success
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_client.user.get.return_value = mock_user

        # Mock zone operations
        mock_zone = Mock()
        mock_zone.id = "zone123"
        mock_zones = Mock()
        mock_zones.result = [mock_zone]
        mock_client.zones.list.return_value = mock_zones

        # Mock rate limit then success
        import cloudflare

        rate_limit_error = cloudflare.RateLimitError(
            message="Rate limit exceeded", response=Mock(), body=None
        )

        success_record = Mock()
        success_record.id = "record123"
        success_record.name = "cf1.example.com"
        success_record.content = "1.1.1.1"

        mock_client.zones.dns_records.list.return_value = Mock(result=[])
        mock_client.zones.dns_records.create.side_effect = [rate_limit_error, success_record]

        dns_manager = DNSManager(self.config)
        dns_manager.authenticate()

        # Should retry and succeed on second attempt
        with patch("time.sleep"):  # Speed up test
            record = dns_manager.upsert_record(
                zone_id="zone123", name="cf1.example.com", content="1.1.1.1"
            )

        assert record.content == "1.1.1.1"
        assert mock_client.zones.dns_records.create.call_count == 2

    @patch("cdnbestip.speedtest.subprocess.run")
    def test_speed_test_retry_on_timeout(self, mock_subprocess):
        """Test speed test retry on timeout."""
        import subprocess

        # Mock timeout then success
        timeout_error = subprocess.TimeoutExpired(["cfst"], 300)
        success_result = Mock()
        success_result.returncode = 0
        success_result.stderr = ""

        mock_subprocess.side_effect = [timeout_error, success_result]

        speed_manager = SpeedTestManager(self.config)
        speed_manager.binary_path = "/usr/bin/cfst"

        temp_dir = tempfile.mkdtemp()
        try:
            ip_file = os.path.join(temp_dir, "ips.txt")
            results_file = os.path.join(temp_dir, "results.csv")

            with open(ip_file, "w") as f:
                f.write("1.1.1.1\n")

            with patch("os.path.exists", return_value=True):
                # Should retry and succeed
                result_file = speed_manager.run_speed_test(ip_file, results_file)
                assert result_file == results_file

            assert mock_subprocess.call_count == 2
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("requests.get")
    def test_ip_source_fallback_on_failure(self, mock_requests):
        """Test IP source fallback when primary source fails."""

        # Mock primary source failure, secondary success
        def requests_side_effect(url, **kwargs):
            if "cloudflare.com" in url:
                raise requests.ConnectionError("Primary source failed")
            else:
                mock_response = Mock()
                mock_response.text = "1.1.1.1\n1.0.0.1\n"
                mock_response.raise_for_status.return_value = None
                return mock_response

        mock_requests.side_effect = requests_side_effect

        ip_manager = IPSourceManager(self.config)

        temp_dir = tempfile.mkdtemp()
        try:
            ip_file = os.path.join(temp_dir, "ips.txt")

            # Should fallback to secondary source
            with patch.object(ip_manager, "get_available_sources", return_value=["cf", "gc"]):
                # Try primary source (cf), then fallback to secondary (gc)
                try:
                    ip_manager.download_ip_list("cf", ip_file, force_refresh=True)
                except IPSourceError:
                    # Fallback to secondary source
                    ip_manager.download_ip_list("gc", ip_file, force_refresh=True)

            # Should have created file with secondary source data
            assert os.path.exists(ip_file)
            with open(ip_file) as f:
                content = f.read()
                assert "1.1.1.1" in content
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)


class TestConcurrentOperationsWorkflow:
    """Test workflows with concurrent operations."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config(
            cloudflare_api_token="test_token",
            domain="example.com",
            prefix="cf",
            quantity=5,
            update_dns=True,
        )
        self.config._skip_validation = True

    @patch("cdnbestip.dns.Cloudflare")
    def test_batch_dns_operations(self, mock_cloudflare):
        """Test batch DNS operations workflow."""
        mock_client = Mock()
        mock_cloudflare.return_value = mock_client

        # Mock authentication
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_client.user.get.return_value = mock_user

        # Mock zone operations
        mock_zone = Mock()
        mock_zone.id = "zone123"
        mock_zone.name = "example.com"
        mock_zones = Mock()
        mock_zones.result = [mock_zone]
        mock_client.zones.list.return_value = mock_zones
        mock_client.zones.get.return_value = mock_zone

        # Mock DNS record operations
        mock_records = Mock()
        mock_records.result = []
        mock_client.zones.dns_records.list.return_value = mock_records

        # Mock record creation
        created_records = []

        def create_record_side_effect(**kwargs):
            mock_record = Mock()
            mock_record.id = f"record_{len(created_records)}"
            mock_record.name = kwargs["name"]
            mock_record.content = kwargs["content"]
            mock_record.type = kwargs["type"]
            created_records.append(mock_record)
            return mock_record

        mock_client.zones.dns_records.create.side_effect = create_record_side_effect

        # Execute batch operations
        dns_manager = DNSManager(self.config)
        dns_manager.authenticate()

        zone_id = dns_manager.get_zone_id("example.com")

        # Batch upsert multiple records
        ip_addresses = ["1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "9.9.9.9"]

        records = dns_manager.batch_upsert_records(
            zone_id=zone_id, base_name="cf", ip_addresses=ip_addresses
        )

        assert len(records) == 5
        assert mock_client.zones.dns_records.create.call_count == 5

        # Verify record names and contents
        for i, record in enumerate(records, 1):
            assert record.name == f"cf{i}.example.com"
            assert record.content == ip_addresses[i - 1]

    def test_parallel_result_processing(self):
        """Test parallel processing of speed test results."""
        # Create large dataset
        results = []
        for i in range(100):
            result = SpeedTestResult(
                ip=f"192.168.1.{i}",
                port=443,
                data_center=f"DC{i % 10}",
                region=f"Region{i % 5}",
                city=f"City{i % 20}",
                speed=float(i % 50),
                latency=float(i % 100),
            )
            results.append(result)

        results_handler = ResultsHandler(self.config)

        # Process results in parallel-like manner
        # Filter by speed
        fast_results = results_handler.filter_by_speed(results, 25.0)

        # Get diverse IPs
        diverse_ips = results_handler.get_diverse_ips(fast_results, 10, max_per_datacenter=2)

        # Get top weighted results
        top_weighted = results_handler.get_top_ips_weighted(fast_results, 5)

        assert len(fast_results) > 0
        assert len(diverse_ips) <= 10
        assert len(top_weighted) <= 5

        # Verify results are properly filtered and sorted
        for result in fast_results:
            assert result.speed >= 25.0


if __name__ == "__main__":
    pytest.main([__file__])
