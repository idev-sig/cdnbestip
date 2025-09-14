"""Unit tests for Chinese CSV format parsing."""

import os
import tempfile

import pytest

from cdnbestip.config import Config
from cdnbestip.results import ResultsHandler


@pytest.fixture
def config():
    """Create a test configuration."""
    config = Config()
    config._skip_validation = True
    config.speed_threshold = 2.0
    config.quantity = 0
    return config


class TestChineseCSVParsing:
    """Test cases for Chinese CSV format parsing."""

    def test_parse_chinese_csv_format(self, config):
        """Test parsing Chinese format CSV file."""
        handler = ResultsHandler(config)

        # Create Chinese format CSV content
        chinese_csv_content = """IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码
104.17.110.237,4,4,0.00,31.60,18.75,HKG
104.18.95.211,4,4,0.00,31.09,18.53,HKG
104.17.111.55,4,4,0.00,30.58,18.38,HKG
104.17.162.80,4,4,0.00,31.34,18.34,HKG
104.19.148.77,4,4,0.00,31.79,18.33,HKG"""

        # Write to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(chinese_csv_content)
            temp_file = f.name

        try:
            # Parse the file
            results = handler.load_results_from_file(temp_file)

            # Verify results
            assert len(results) == 5

            # Check first result
            first_result = results[0]
            assert first_result.ip == "104.17.110.237"
            assert first_result.speed == 18.75
            assert first_result.latency == 31.60
            assert first_result.region == "HKG"
            assert first_result.data_center == "HKG"
            assert first_result.city == "HKG"
            assert first_result.port == 443  # Default port

            # Check that all results are parsed correctly
            expected_ips = [
                "104.17.110.237",
                "104.18.95.211",
                "104.17.111.55",
                "104.17.162.80",
                "104.19.148.77",
            ]

            actual_ips = [result.ip for result in results]
            assert actual_ips == expected_ips

            # Check speeds are parsed correctly
            expected_speeds = [18.75, 18.53, 18.38, 18.34, 18.33]
            actual_speeds = [result.speed for result in results]
            assert actual_speeds == expected_speeds

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_parse_english_csv_format_still_works(self, config):
        """Test that English format CSV still works after Chinese support."""
        handler = ResultsHandler(config)

        # Create English format CSV content
        english_csv_content = """IP,Port,Data Center,Region,City,Speed (MB/s),Latency (ms)
1.1.1.1,443,LAX,US-West,Los Angeles,5.2,15.5
1.0.0.1,443,LAX,US-West,Los Angeles,4.8,12.3"""

        # Write to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(english_csv_content)
            temp_file = f.name

        try:
            # Parse the file
            results = handler.load_results_from_file(temp_file)

            # Verify results
            assert len(results) == 2

            # Check first result
            first_result = results[0]
            assert first_result.ip == "1.1.1.1"
            assert first_result.port == 443
            assert first_result.data_center == "LAX"
            assert first_result.region == "US-West"
            assert first_result.city == "Los Angeles"
            assert first_result.speed == 5.2
            assert first_result.latency == 15.5

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_chinese_csv_filtering_and_selection(self, config):
        """Test filtering and selection works with Chinese CSV data."""
        handler = ResultsHandler(config)

        # Create Chinese format CSV content with varied speeds
        chinese_csv_content = """IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码
104.17.110.237,4,4,0.00,31.60,18.75,HKG
104.18.95.211,4,4,0.00,31.09,18.53,HKG
104.17.111.55,4,4,0.00,30.58,1.38,HKG
104.17.162.80,4,4,0.00,31.34,18.34,HKG
104.19.148.77,4,4,0.00,31.79,0.33,HKG"""

        # Write to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(chinese_csv_content)
            temp_file = f.name

        try:
            # Parse the file
            results = handler.load_results_from_file(temp_file)

            # Test speed filtering
            fast_results = handler.filter_by_speed(results, 10.0)
            assert len(fast_results) == 3  # Only results with speed >= 10.0

            # Test top IP selection
            top_ips = handler.get_top_ips(results, 2)
            assert len(top_ips) == 2
            assert top_ips[0] == "104.17.110.237"  # Highest speed
            assert top_ips[1] == "104.18.95.211"  # Second highest

            # Test performance summary
            summary = handler.get_performance_summary(results)
            assert summary["total_results"] == 5
            assert summary["results_above_threshold"] == 3  # Above default threshold of 2.0
            assert summary["max_speed"] == 18.75

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_mixed_format_handling(self, config):
        """Test handling of files that might have mixed or unclear formats."""
        handler = ResultsHandler(config)

        # Test with positional parsing (no header)
        csv_content_no_header = """104.17.110.237,4,4,0.00,31.60,18.75,HKG
104.18.95.211,4,4,0.00,31.09,18.53,HKG"""

        # Write to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(csv_content_no_header)
            temp_file = f.name

        try:
            # Parse the file
            results = handler.load_results_from_file(temp_file)

            # Should parse as Chinese format (7 columns)
            assert len(results) == 2
            assert results[0].ip == "104.17.110.237"
            assert results[0].speed == 18.75
            assert results[0].region == "HKG"

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__])
