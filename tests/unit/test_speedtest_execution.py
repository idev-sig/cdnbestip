"""Unit tests for speed test execution and result parsing."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cdnbestip.config import Config
from cdnbestip.exceptions import SpeedTestError
from cdnbestip.models import SpeedTestResult
from cdnbestip.speedtest import SpeedTestManager


class TestSpeedTestExecution:
    """Test speed test execution and result parsing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.manager = SpeedTestManager(self.config)
        self.manager.binary_path = "/usr/bin/cfst"  # Mock binary path

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_run_speed_test_success(self, mock_exists, mock_run):
        """Test successful speed test execution."""
        # Mock file existence
        mock_exists.side_effect = lambda path: path in ["/tmp/ip.txt", "result.csv"]

        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result_file = self.manager.run_speed_test("/tmp/ip.txt")

        assert result_file == "result.csv"
        mock_run.assert_called_once()

        # Check command arguments
        call_args = mock_run.call_args[0][0]
        assert "/usr/bin/cfst" in call_args
        assert "-f" in call_args
        assert "/tmp/ip.txt" in call_args
        assert "-o" in call_args
        assert "result.csv" in call_args

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_run_speed_test_with_config_params(self, mock_exists, mock_run):
        """Test speed test execution with configuration parameters."""
        # Set up config with parameters
        self.config.speed_port = 443
        self.config.speed_url = "https://example.com/test"
        self.config.quantity = 10
        self.config.speed_threshold = 5.0

        # Mock file existence
        mock_exists.side_effect = lambda path: path in ["/tmp/ip.txt", "result.csv"]

        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        self.manager.run_speed_test("/tmp/ip.txt")

        # Check that config parameters were included
        call_args = mock_run.call_args[0][0]
        assert "-tp" in call_args
        assert "443" in call_args
        assert "-url" in call_args
        assert "https://example.com/test" in call_args
        # When speed_threshold > 0, -sl and -tl should be added
        assert "-sl" in call_args
        assert "5.0" in call_args
        assert "-tl" in call_args
        assert "200" in call_args

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_run_speed_test_without_speed_threshold(self, mock_exists, mock_run):
        """Test speed test execution without speed threshold (should not add -sl/-tl)."""
        # Set speed_threshold to None
        self.config.speed_threshold = None

        # Mock file existence
        mock_exists.side_effect = lambda path: path in ["/tmp/ip.txt", "result.csv"]

        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        self.manager.run_speed_test("/tmp/ip.txt")

        # Check that -sl and -tl are NOT included
        call_args = mock_run.call_args[0][0]
        assert "-sl" not in call_args
        assert "-tl" not in call_args

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_run_speed_test_with_zero_speed_threshold(self, mock_exists, mock_run):
        """Test speed test execution with zero speed threshold (should not add -sl/-tl)."""
        # Set speed_threshold to 0
        self.config.speed_threshold = 0.0

        # Mock file existence
        mock_exists.side_effect = lambda path: path in ["/tmp/ip.txt", "result.csv"]

        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        self.manager.run_speed_test("/tmp/ip.txt")

        # Check that -sl and -tl are NOT included
        call_args = mock_run.call_args[0][0]
        assert "-sl" not in call_args
        assert "-tl" not in call_args

    @patch("os.path.exists")
    def test_run_speed_test_ip_file_not_found(self, mock_exists):
        """Test speed test execution when IP file doesn't exist."""
        mock_exists.return_value = False

        with pytest.raises(SpeedTestError, match="IP file not found"):
            self.manager.run_speed_test("/nonexistent/ip.txt")

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_run_speed_test_binary_fails(self, mock_exists, mock_run):
        """Test speed test execution when binary fails."""
        mock_exists.side_effect = lambda path: path == "/tmp/ip.txt"

        # Mock failed subprocess run
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: Invalid parameters"
        mock_run.return_value = mock_result

        with pytest.raises(SpeedTestError, match="Speed test failed with return code 1"):
            self.manager.run_speed_test("/tmp/ip.txt")

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_run_speed_test_timeout(self, mock_exists, mock_run):
        """Test speed test execution timeout."""
        mock_exists.side_effect = lambda path: path == "/tmp/ip.txt"
        mock_run.side_effect = subprocess.TimeoutExpired(["cfst"], 300)

        with pytest.raises(SpeedTestError, match="Speed test timed out"):
            self.manager.run_speed_test("/tmp/ip.txt")

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_run_speed_test_binary_not_found(self, mock_exists, mock_run):
        """Test speed test execution when binary is not found."""
        mock_exists.side_effect = lambda path: path == "/tmp/ip.txt"
        mock_run.side_effect = FileNotFoundError("Binary not found")

        with pytest.raises(SpeedTestError, match="Speed test binary not found"):
            self.manager.run_speed_test("/tmp/ip.txt")

    def test_parse_results_success(self):
        """Test successful CSV result parsing."""
        csv_content = """IP,Port,DataCenter,Region,City,Speed,Latency
192.168.1.1,443,SJC,US,San Jose,15.5,25.3
192.168.1.2,80,LAX,US,Los Angeles,12.8,30.1
10.0.0.1,443,NYC,US,New York,18.2,45.2"""

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as temp_file:
            temp_file.write(csv_content)
            temp_path = temp_file.name

        try:
            results = self.manager.parse_results(temp_path)

            assert len(results) == 3

            # Check first result
            result1 = results[0]
            assert result1.ip == "192.168.1.1"
            assert result1.port == 443
            assert result1.data_center == "SJC"
            assert result1.region == "US"
            assert result1.city == "San Jose"
            assert result1.speed == 15.5
            assert result1.latency == 25.3

            # Check second result
            result2 = results[1]
            assert result2.ip == "192.168.1.2"
            assert result2.speed == 12.8

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_parse_results_file_not_found(self):
        """Test CSV parsing when file doesn't exist."""
        with pytest.raises(SpeedTestError, match="Results file not found"):
            self.manager.parse_results("/nonexistent/file.csv")

    def test_parse_results_empty_file(self):
        """Test CSV parsing with empty file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as temp_file:
            temp_file.write("")
            temp_path = temp_file.name

        try:
            with pytest.raises(SpeedTestError, match="Results file is empty"):
                self.manager.parse_results(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_parse_results_header_only(self):
        """Test CSV parsing with header only."""
        csv_content = "IP,Port,DataCenter,Region,City,Speed,Latency\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as temp_file:
            temp_file.write(csv_content)
            temp_path = temp_file.name

        try:
            with pytest.raises(SpeedTestError, match="Results file is empty or missing header"):
                self.manager.parse_results(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_parse_csv_line_success(self):
        """Test parsing a valid CSV line."""
        line = "192.168.1.1,443,SJC,US,San Jose,15.5,25.3"
        result = self.manager._parse_csv_line(line, 2)

        assert result.ip == "192.168.1.1"
        assert result.port == 443
        assert result.data_center == "SJC"
        assert result.region == "US"
        assert result.city == "San Jose"
        assert result.speed == 15.5
        assert result.latency == 25.3

    def test_parse_csv_line_with_na_values(self):
        """Test parsing CSV line with N/A values."""
        line = "192.168.1.1,443,SJC,US,San Jose,N/A,N/A"
        result = self.manager._parse_csv_line(line, 2)

        assert result.ip == "192.168.1.1"
        assert result.speed == 0.0
        assert result.latency == 0.0

    def test_parse_csv_line_invalid_format(self):
        """Test parsing invalid CSV line."""
        line = "192.168.1.1,443,SJC"  # Missing columns

        with pytest.raises(ValueError, match="Invalid CSV format"):
            self.manager._parse_csv_line(line, 2)

    def test_parse_csv_line_invalid_ip(self):
        """Test parsing CSV line with invalid IP."""
        line = ",443,SJC,US,San Jose,15.5,25.3"  # Empty IP

        with pytest.raises(ValueError, match="Invalid IP address"):
            self.manager._parse_csv_line(line, 2)

    def test_validate_results(self):
        """Test result validation."""
        results = [
            SpeedTestResult("192.168.1.1", 443, "SJC", "US", "San Jose", 15.5, 25.3),
            SpeedTestResult("", 443, "LAX", "US", "Los Angeles", 12.8, 30.1),  # Invalid IP
            SpeedTestResult("10.0.0.1", 443, "NYC", "US", "New York", -5.0, 45.2),  # Negative speed
            SpeedTestResult(
                "172.16.0.1", 443, "DFW", "US", "Dallas", 20.1, -10.0
            ),  # Negative latency
            SpeedTestResult("203.0.113.1", 443, "SEA", "US", "Seattle", 18.7, 22.1),  # Valid
        ]

        valid_results = self.manager.validate_results(results)

        assert len(valid_results) == 2
        assert valid_results[0].ip == "192.168.1.1"
        assert valid_results[1].ip == "203.0.113.1"

    def test_filter_results_by_speed(self):
        """Test filtering results by speed threshold."""
        results = [
            SpeedTestResult("192.168.1.1", 443, "SJC", "US", "San Jose", 15.5, 25.3),
            SpeedTestResult("192.168.1.2", 443, "LAX", "US", "Los Angeles", 8.2, 30.1),
            SpeedTestResult("10.0.0.1", 443, "NYC", "US", "New York", 18.7, 45.2),
        ]

        filtered = self.manager.filter_results_by_speed(results, 10.0)

        assert len(filtered) == 2
        assert all(result.speed >= 10.0 for result in filtered)

    def test_sort_results_by_speed(self):
        """Test sorting results by speed."""
        results = [
            SpeedTestResult("192.168.1.1", 443, "SJC", "US", "San Jose", 15.5, 25.3),
            SpeedTestResult("192.168.1.2", 443, "LAX", "US", "Los Angeles", 8.2, 30.1),
            SpeedTestResult("10.0.0.1", 443, "NYC", "US", "New York", 18.7, 45.2),
        ]

        # Sort descending (fastest first)
        sorted_desc = self.manager.sort_results_by_speed(results, reverse=True)
        assert sorted_desc[0].speed == 18.7
        assert sorted_desc[1].speed == 15.5
        assert sorted_desc[2].speed == 8.2

        # Sort ascending (slowest first)
        sorted_asc = self.manager.sort_results_by_speed(results, reverse=False)
        assert sorted_asc[0].speed == 8.2
        assert sorted_asc[1].speed == 15.5
        assert sorted_asc[2].speed == 18.7

    def test_get_top_results(self):
        """Test getting top N results."""
        results = [
            SpeedTestResult("192.168.1.1", 443, "SJC", "US", "San Jose", 15.5, 25.3),
            SpeedTestResult("192.168.1.2", 443, "LAX", "US", "Los Angeles", 8.2, 30.1),
            SpeedTestResult("10.0.0.1", 443, "NYC", "US", "New York", 18.7, 45.2),
            SpeedTestResult("172.16.0.1", 443, "DFW", "US", "Dallas", 12.3, 35.1),
        ]

        top_2 = self.manager.get_top_results(results, 2)

        assert len(top_2) == 2
        assert top_2[0].speed == 18.7  # Fastest
        assert top_2[1].speed == 15.5  # Second fastest

    def test_get_top_results_unlimited(self):
        """Test getting all results when count is 0."""
        results = [
            SpeedTestResult("192.168.1.1", 443, "SJC", "US", "San Jose", 15.5, 25.3),
            SpeedTestResult("10.0.0.1", 443, "NYC", "US", "New York", 18.7, 45.2),
        ]

        all_results = self.manager.get_top_results(results, 0)

        assert len(all_results) == 2
        assert all_results[0].speed == 18.7  # Still sorted by speed

    def test_should_refresh_results_file_age(self):
        """Test result refresh based on file age."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Fresh file should not need refresh
            assert not self.manager.should_refresh_results(temp_path)

            # Mock old file (modify timestamp)
            import time

            old_time = time.time() - 90000  # More than 24 hours
            os.utime(temp_path, (old_time, old_time))

            assert self.manager.should_refresh_results(temp_path)

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_should_refresh_results_config_refresh(self):
        """Test result refresh when config.refresh is True."""
        self.config.refresh = True

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Even fresh file should be refreshed when config.refresh is True
            assert self.manager.should_refresh_results(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_should_refresh_results_nonexistent_file(self):
        """Test result refresh for nonexistent file."""
        assert self.manager.should_refresh_results("/nonexistent/file.csv")

    def test_parse_results_with_malformed_lines(self):
        """Test CSV parsing with some malformed lines."""
        csv_content = """IP,Port,DataCenter,Region,City,Speed,Latency
192.168.1.1,443,SJC,US,San Jose,15.5,25.3
invalid,line,with,not,enough
192.168.1.2,80,LAX,US,Los Angeles,12.8,30.1
,443,NYC,US,New York,18.2,45.2
192.168.1.3,443,DFW,US,Dallas,20.1,35.5"""

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as temp_file:
            temp_file.write(csv_content)
            temp_path = temp_file.name

        try:
            # Should capture warnings but continue parsing valid lines
            with patch("builtins.print") as mock_print:
                results = self.manager.parse_results(temp_path)

                # Should have 2 valid results (skipping malformed lines)
                assert len(results) == 2
                assert results[0].ip == "192.168.1.1"
                assert results[1].ip == "192.168.1.2"

                # Should have printed warnings for malformed lines
                assert mock_print.call_count >= 1

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_parse_csv_line_with_empty_values(self):
        """Test parsing CSV line with empty values."""
        line = "192.168.1.1,,SJC,US,San Jose,,25.3"
        result = self.manager._parse_csv_line(line, 2)

        assert result.ip == "192.168.1.1"
        assert result.port == 0  # Empty port becomes 0
        assert result.speed == 0.0  # Empty speed becomes 0.0
        assert result.latency == 25.3

    def test_parse_csv_line_with_whitespace(self):
        """Test parsing CSV line with whitespace."""
        line = " 192.168.1.1 , 443 , SJC , US , San Jose , 15.5 , 25.3 "
        result = self.manager._parse_csv_line(line, 2)

        assert result.ip == "192.168.1.1"
        assert result.port == 443
        assert result.data_center == "SJC"
        assert result.region == "US"
        assert result.city == "San Jose"
        assert result.speed == 15.5
        assert result.latency == 25.3

    def test_parse_csv_line_invalid_numeric_values(self):
        """Test parsing CSV line with invalid numeric values."""
        line = "192.168.1.1,invalid_port,SJC,US,San Jose,invalid_speed,invalid_latency"

        with pytest.raises(ValueError):
            self.manager._parse_csv_line(line, 2)

    def test_validate_results_edge_cases(self):
        """Test result validation with edge cases."""
        results = [
            SpeedTestResult("192.168.1.1", 443, "SJC", "US", "San Jose", 15.5, 25.3),  # Valid
            SpeedTestResult("", 443, "LAX", "US", "Los Angeles", 12.8, 30.1),  # Empty IP
            SpeedTestResult(
                "10.0.0.1", -1, "NYC", "US", "New York", 18.7, 45.2
            ),  # Negative port (but should be valid)
            SpeedTestResult(
                "172.16.0.1", 443, "", "", "", 20.1, 22.1
            ),  # Empty location fields (but should be valid)
        ]

        valid_results = self.manager.validate_results(results)

        # Should only keep results with valid IP and non-negative speed/latency
        assert len(valid_results) == 3  # First, third, and fourth results
        assert valid_results[0].ip == "192.168.1.1"
        assert valid_results[1].ip == "10.0.0.1"
        assert valid_results[2].ip == "172.16.0.1"

    def test_filter_results_by_speed_edge_cases(self):
        """Test speed filtering with edge cases."""
        results = [
            SpeedTestResult("1.1.1.1", 443, "LAX", "US", "LA", 0.0, 20.0),  # Zero speed
            SpeedTestResult("1.0.0.1", 443, "NYC", "US", "NY", 2.0, 25.0),  # Exact threshold
            SpeedTestResult("8.8.8.8", 443, "SJC", "US", "SJ", 2.1, 15.0),  # Just above threshold
        ]

        # Filter with threshold 2.0
        filtered = self.manager.filter_results_by_speed(results, 2.0)
        assert len(filtered) == 2  # Should include exact match and above
        assert filtered[0].speed == 2.0
        assert filtered[1].speed == 2.1

        # Filter with threshold 0.0
        filtered_zero = self.manager.filter_results_by_speed(results, 0.0)
        assert len(filtered_zero) == 3  # Should include all

    def test_sort_results_by_speed_with_equal_speeds(self):
        """Test sorting when multiple results have the same speed."""
        results = [
            SpeedTestResult("1.1.1.1", 443, "LAX", "US", "LA", 10.0, 30.0),
            SpeedTestResult("1.0.0.1", 443, "NYC", "US", "NY", 10.0, 20.0),
            SpeedTestResult("8.8.8.8", 443, "SJC", "US", "SJ", 10.0, 25.0),
        ]

        sorted_results = self.manager.sort_results_by_speed(results, reverse=True)

        # All should have same speed, order should be preserved or by some secondary criteria
        assert len(sorted_results) == 3
        assert all(result.speed == 10.0 for result in sorted_results)

    def test_get_top_results_more_than_available(self):
        """Test getting more results than available."""
        results = [
            SpeedTestResult("1.1.1.1", 443, "LAX", "US", "LA", 15.0, 20.0),
            SpeedTestResult("1.0.0.1", 443, "NYC", "US", "NY", 12.0, 25.0),
        ]

        # Request more than available
        top_results = self.manager.get_top_results(results, 5)

        # Should return all available results
        assert len(top_results) == 2
        assert top_results[0].speed == 15.0  # Fastest first
        assert top_results[1].speed == 12.0

    def test_get_top_results_empty_list(self):
        """Test getting top results from empty list."""
        top_results = self.manager.get_top_results([], 5)
        assert len(top_results) == 0


class TestSpeedTestManagerConfiguration:
    """Test SpeedTestManager configuration and initialization."""

    def test_manager_initialization(self):
        """Test SpeedTestManager initialization."""
        config = Config()
        manager = SpeedTestManager(config)

        assert manager.config == config
        assert manager.binary_path is None
        assert manager.binary_dir.name == "bin"
        assert "cdnbestip" in str(manager.binary_dir)

    def test_manager_with_custom_config(self):
        """Test SpeedTestManager with custom configuration."""
        config = Config()
        config.speed_threshold = 5.0
        config.quantity = 10
        config.speed_port = 8080
        config.speed_url = "https://custom.example.com/test"

        manager = SpeedTestManager(config)

        assert manager.config.speed_threshold == 5.0
        assert manager.config.quantity == 10
        assert manager.config.speed_port == 8080
        assert manager.config.speed_url == "https://custom.example.com/test"

    def test_binary_names_constant(self):
        """Test that binary names constant is properly defined."""
        assert hasattr(SpeedTestManager, "BINARY_NAMES")
        assert isinstance(SpeedTestManager.BINARY_NAMES, list)
        assert len(SpeedTestManager.BINARY_NAMES) > 0
        assert "CloudflareSpeedTest" in SpeedTestManager.BINARY_NAMES

    def test_github_repo_constant(self):
        """Test that GitHub repo constant is properly defined."""
        assert hasattr(SpeedTestManager, "GITHUB_REPO")
        assert SpeedTestManager.GITHUB_REPO == "XIU2/CloudflareSpeedTest"

    def test_binary_version_constant(self):
        """Test that binary version constant is properly defined."""
        assert hasattr(SpeedTestManager, "BINARY_VERSION")
        assert SpeedTestManager.BINARY_VERSION.startswith("v")
