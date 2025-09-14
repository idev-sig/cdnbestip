"""Unit tests for results processing and filtering."""

import os
import time

import pytest

from cdnbestip.config import Config
from cdnbestip.exceptions import CDNBESTIPError
from cdnbestip.models import SpeedTestResult
from cdnbestip.results import ResultsHandler


@pytest.fixture
def config():
    """Create a test configuration."""
    config = Config()
    config._skip_validation = True
    config.speed_threshold = 2.0
    config.quantity = 0
    return config


@pytest.fixture
def sample_results():
    """Create sample speed test results for testing."""
    return [
        SpeedTestResult(
            ip="1.1.1.1",
            port=443,
            data_center="LAX",
            region="US-West",
            city="Los Angeles",
            speed=5.2,
            latency=15.5,
        ),
        SpeedTestResult(
            ip="1.0.0.1",
            port=443,
            data_center="LAX",
            region="US-West",
            city="Los Angeles",
            speed=4.8,
            latency=12.3,
        ),
        SpeedTestResult(
            ip="8.8.8.8",
            port=443,
            data_center="NYC",
            region="US-East",
            city="New York",
            speed=3.1,
            latency=25.7,
        ),
        SpeedTestResult(
            ip="8.8.4.4",
            port=443,
            data_center="NYC",
            region="US-East",
            city="New York",
            speed=1.8,
            latency=18.9,
        ),
        SpeedTestResult(
            ip="9.9.9.9",
            port=443,
            data_center="FRA",
            region="EU-Central",
            city="Frankfurt",
            speed=6.3,
            latency=45.2,
        ),
    ]


class TestResultsHandler:
    """Test cases for ResultsHandler class."""

    def test_init(self, config):
        """Test ResultsHandler initialization."""
        handler = ResultsHandler(config)
        assert handler.config == config

    def test_filter_by_speed(self, config, sample_results):
        """Test speed-based filtering."""
        handler = ResultsHandler(config)

        # Test with default threshold (2.0)
        filtered = handler.filter_by_speed(sample_results, 2.0)
        assert len(filtered) == 4  # All except 8.8.4.4 (1.8 MB/s)

        # Test with higher threshold
        filtered = handler.filter_by_speed(sample_results, 4.0)
        assert len(filtered) == 3  # 1.1.1.1, 1.0.0.1, 9.9.9.9

        # Test with very high threshold
        filtered = handler.filter_by_speed(sample_results, 10.0)
        assert len(filtered) == 0

        # Test with empty results
        filtered = handler.filter_by_speed([], 2.0)
        assert len(filtered) == 0

    def test_filter_by_latency(self, config, sample_results):
        """Test latency-based filtering."""
        handler = ResultsHandler(config)

        # Test with 20ms threshold
        filtered = handler.filter_by_latency(sample_results, 20.0)
        assert len(filtered) == 3  # 1.1.1.1, 1.0.0.1, 8.8.4.4

        # Test with very low threshold
        filtered = handler.filter_by_latency(sample_results, 10.0)
        assert len(filtered) == 0

        # Test with high threshold
        filtered = handler.filter_by_latency(sample_results, 100.0)
        assert len(filtered) == 5  # All results

    def test_filter_by_region(self, config, sample_results):
        """Test region-based filtering."""
        handler = ResultsHandler(config)

        # Test with US regions
        filtered = handler.filter_by_region(sample_results, ["US-West", "US-East"])
        assert len(filtered) == 4

        # Test with single region
        filtered = handler.filter_by_region(sample_results, ["EU-Central"])
        assert len(filtered) == 1
        assert filtered[0].ip == "9.9.9.9"

        # Test with non-existent region
        filtered = handler.filter_by_region(sample_results, ["Asia-Pacific"])
        assert len(filtered) == 0

        # Test with empty preferred regions
        filtered = handler.filter_by_region(sample_results, [])
        assert len(filtered) == 5  # Should return all results

    def test_get_top_ips(self, config, sample_results):
        """Test getting top IP addresses."""
        handler = ResultsHandler(config)

        # Test getting all IPs above threshold
        top_ips = handler.get_top_ips(sample_results, 0)
        expected_order = [
            "9.9.9.9",
            "1.1.1.1",
            "1.0.0.1",
            "8.8.8.8",
        ]  # Sorted by speed desc, latency asc
        assert top_ips == expected_order

        # Test getting top 2 IPs
        top_ips = handler.get_top_ips(sample_results, 2)
        assert top_ips == ["9.9.9.9", "1.1.1.1"]

        # Test with quantity in config
        config.quantity = 3
        top_ips = handler.get_top_ips(sample_results, 0)
        assert len(top_ips) == 3
        assert top_ips == ["9.9.9.9", "1.1.1.1", "1.0.0.1"]

        # Test with empty results
        top_ips = handler.get_top_ips([], 5)
        assert top_ips == []

    def test_get_top_results(self, config, sample_results):
        """Test getting top SpeedTestResult objects."""
        handler = ResultsHandler(config)

        # Test getting top 2 results
        top_results = handler.get_top_results(sample_results, 2)
        assert len(top_results) == 2
        assert top_results[0].ip == "9.9.9.9"  # Fastest
        assert top_results[1].ip == "1.1.1.1"  # Second fastest

        # Test with quantity in config
        config.quantity = 1
        top_results = handler.get_top_results(sample_results, 0)
        assert len(top_results) == 1
        assert top_results[0].ip == "9.9.9.9"

    def test_get_weighted_score(self, config, sample_results):
        """Test weighted scoring algorithm."""
        handler = ResultsHandler(config)

        # Test with default weights (0.7 speed, 0.3 latency)
        result = sample_results[0]  # 1.1.1.1: speed=5.2, latency=15.5
        score = handler.get_weighted_score(result)

        # Calculate expected score
        speed_score = 5.2
        latency_score = (1000 - 15.5) / 1000
        expected_score = (speed_score * 0.7) + (latency_score * 0.3)

        assert abs(score - expected_score) < 0.001

        # Test with custom weights
        score = handler.get_weighted_score(result, speed_weight=0.5, latency_weight=0.5)
        expected_score = (speed_score * 0.5) + (latency_score * 0.5)
        assert abs(score - expected_score) < 0.001

    def test_get_top_ips_weighted(self, config, sample_results):
        """Test weighted IP selection."""
        handler = ResultsHandler(config)

        # Test with default weights
        top_ips = handler.get_top_ips_weighted(sample_results, 3)
        assert len(top_ips) == 3

        # 9.9.9.9 should be first due to highest speed despite higher latency
        assert top_ips[0] == "9.9.9.9"

        # Test that weighted scoring works correctly
        # With default weights (0.7 speed, 0.3 latency), speed dominates
        # So 1.1.1.1 (speed=5.2) should rank higher than 1.0.0.1 (speed=4.8) despite worse latency
        assert top_ips.index("1.1.1.1") < top_ips.index("1.0.0.1")

        # Test with results that have significant latency differences
        latency_test_results = [
            SpeedTestResult(
                "fast-high-latency", 443, "FAR", "Remote", "Far", 5.0, 500.0
            ),  # Very high latency
            SpeedTestResult(
                "slow-low-latency", 443, "NEAR", "Local", "Near", 4.0, 5.0
            ),  # Very low latency
        ]

        # With extreme latency weighting, low latency should win despite lower speed
        top_ips_latency_heavy = handler.get_top_ips_weighted(
            latency_test_results, 2, speed_weight=0.1, latency_weight=0.9
        )
        assert top_ips_latency_heavy[0] == "slow-low-latency"  # Better latency should win

        # Test with speed-only weighting
        top_ips_speed_only = handler.get_top_ips_weighted(
            sample_results, 3, speed_weight=1.0, latency_weight=0.0
        )
        assert top_ips_speed_only[0] == "9.9.9.9"  # Fastest speed

        # Test that weighted scoring function works
        result1 = sample_results[0]  # 1.1.1.1
        score1 = handler.get_weighted_score(result1, 0.7, 0.3)
        score2 = handler.get_weighted_score(result1, 0.3, 0.7)
        # Different weights should produce different scores
        assert score1 != score2

    def test_get_diverse_ips(self, config, sample_results):
        """Test diverse IP selection."""
        handler = ResultsHandler(config)

        # Test with max 1 per datacenter
        diverse_ips = handler.get_diverse_ips(sample_results, 0, max_per_datacenter=1)
        assert len(diverse_ips) == 3  # LAX, NYC, FRA

        # Should get best IP from each datacenter
        assert "9.9.9.9" in diverse_ips  # Best from FRA
        assert "1.1.1.1" in diverse_ips  # Best from LAX (higher speed than 1.0.0.1)
        assert "8.8.8.8" in diverse_ips  # Best from NYC (above threshold)

        # Test with max 2 per datacenter
        diverse_ips = handler.get_diverse_ips(sample_results, 0, max_per_datacenter=2)
        assert len(diverse_ips) == 4  # Should exclude 8.8.4.4 (below threshold)

        # Test with count limit
        diverse_ips = handler.get_diverse_ips(sample_results, 2, max_per_datacenter=2)
        assert len(diverse_ips) == 2

    def test_should_update_dns(self, config, sample_results):
        """Test DNS update decision logic."""
        handler = ResultsHandler(config)

        # Test with results above threshold
        assert handler.should_update_dns(sample_results) is True

        # Test with no results
        assert handler.should_update_dns([]) is False

        # Test with results below threshold
        config.speed_threshold = 10.0
        assert handler.should_update_dns(sample_results) is False

    def test_get_best_ip(self, config, sample_results):
        """Test getting the best single IP."""
        handler = ResultsHandler(config)

        # Test normal case
        best_ip = handler.get_best_ip(sample_results)
        assert best_ip == "9.9.9.9"  # Fastest speed

        # Test with no results
        with pytest.raises(ValueError, match="No results available"):
            handler.get_best_ip([])

        # Test with no results above threshold
        config.speed_threshold = 10.0
        with pytest.raises(ValueError, match="No results meet speed threshold"):
            handler.get_best_ip(sample_results)

    def test_get_performance_summary(self, config, sample_results):
        """Test performance summary statistics."""
        handler = ResultsHandler(config)

        # Test with normal results
        summary = handler.get_performance_summary(sample_results)

        assert summary["total_results"] == 5
        assert summary["results_above_threshold"] == 4  # All except 8.8.4.4
        assert summary["max_speed"] == 6.3  # 9.9.9.9
        assert summary["min_speed"] == 1.8  # 8.8.4.4
        assert summary["min_latency"] == 12.3  # 1.0.0.1
        assert summary["max_latency"] == 45.2  # 9.9.9.9

        # Check averages
        expected_avg_speed = (5.2 + 4.8 + 3.1 + 1.8 + 6.3) / 5
        expected_avg_latency = (15.5 + 12.3 + 25.7 + 18.9 + 45.2) / 5

        assert abs(summary["avg_speed"] - expected_avg_speed) < 0.001
        assert abs(summary["avg_latency"] - expected_avg_latency) < 0.001

        # Test with empty results
        summary = handler.get_performance_summary([])
        assert summary["total_results"] == 0
        assert summary["results_above_threshold"] == 0
        assert summary["avg_speed"] == 0.0
        assert summary["max_speed"] == 0.0


class TestResultsHandlerEdgeCases:
    """Test edge cases and error conditions."""

    def test_filter_with_edge_values(self, config):
        """Test filtering with edge case values."""
        handler = ResultsHandler(config)

        # Test with zero speed
        results = [
            SpeedTestResult("1.1.1.1", 443, "LAX", "US", "LA", 0.0, 10.0),
            SpeedTestResult("2.2.2.2", 443, "NYC", "US", "NY", 2.0, 20.0),
        ]

        filtered = handler.filter_by_speed(results, 0.0)
        assert len(filtered) == 2

        filtered = handler.filter_by_speed(results, 1.0)
        assert len(filtered) == 1
        assert filtered[0].ip == "2.2.2.2"

    def test_sorting_with_equal_speeds(self, config):
        """Test sorting behavior with equal speeds."""
        handler = ResultsHandler(config)

        # Create results with same speed but different latencies
        results = [
            SpeedTestResult("1.1.1.1", 443, "LAX", "US", "LA", 5.0, 20.0),
            SpeedTestResult("2.2.2.2", 443, "NYC", "US", "NY", 5.0, 10.0),
            SpeedTestResult("3.3.3.3", 443, "FRA", "EU", "Frankfurt", 5.0, 15.0),
        ]

        top_ips = handler.get_top_ips(results, 0)

        # Should be sorted by latency (ascending) when speeds are equal
        assert top_ips == ["2.2.2.2", "3.3.3.3", "1.1.1.1"]

    def test_quantity_limits(self, config):
        """Test various quantity limit scenarios."""
        handler = ResultsHandler(config)

        results = [
            SpeedTestResult("1.1.1.1", 443, "LAX", "US", "LA", 5.0, 10.0),
            SpeedTestResult("2.2.2.2", 443, "NYC", "US", "NY", 4.0, 15.0),
            SpeedTestResult("3.3.3.3", 443, "FRA", "EU", "Frankfurt", 3.0, 20.0),
        ]

        # Test count parameter takes precedence over config.quantity
        config.quantity = 1
        top_ips = handler.get_top_ips(results, 2)
        assert len(top_ips) == 2

        # Test config.quantity when count is 0
        top_ips = handler.get_top_ips(results, 0)
        assert len(top_ips) == 1

        # Test when count exceeds available results
        top_ips = handler.get_top_ips(results, 10)
        assert len(top_ips) == 3


class TestResultsFileManagement:
    """Test cases for file management and caching functionality."""

    def test_should_refresh_results(self, config, tmp_path):
        """Test result file refresh logic."""
        handler = ResultsHandler(config)

        # Non-existent file should be refreshed
        non_existent = tmp_path / "nonexistent.csv"
        assert handler.should_refresh_results(str(non_existent)) is True

        # Create a fresh file
        fresh_file = tmp_path / "fresh.csv"
        fresh_file.write_text("test")
        assert handler.should_refresh_results(str(fresh_file), max_age_hours=24) is False

        # Create an old file by modifying its timestamp
        old_file = tmp_path / "old.csv"
        old_file.write_text("test")

        # Set file modification time to 25 hours ago
        old_time = time.time() - (25 * 3600)
        os.utime(str(old_file), (old_time, old_time))

        assert handler.should_refresh_results(str(old_file), max_age_hours=24) is True
        assert handler.should_refresh_results(str(old_file), max_age_hours=48) is False

    def test_is_results_file_valid(self, config, tmp_path):
        """Test result file validation."""
        handler = ResultsHandler(config)

        # Non-existent file is invalid
        non_existent = tmp_path / "nonexistent.csv"
        assert handler.is_results_file_valid(str(non_existent)) is False

        # Empty file is invalid
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")
        assert handler.is_results_file_valid(str(empty_file)) is False

        # Valid CSV file
        valid_file = tmp_path / "valid.csv"
        valid_file.write_text(
            "IP,Port,Data Center,Region,City,Speed (MB/s),Latency (ms)\n"
            "1.1.1.1,443,LAX,US-West,Los Angeles,5.2,15.5\n"
        )
        assert handler.is_results_file_valid(str(valid_file)) is True

        # Corrupted file
        corrupted_file = tmp_path / "corrupted.csv"
        corrupted_file.write_text("invalid,csv,content")
        assert handler.is_results_file_valid(str(corrupted_file)) is False

    def test_load_results_from_file(self, config, tmp_path):
        """Test loading results from CSV file."""
        handler = ResultsHandler(config)

        # Test with header
        csv_with_header = tmp_path / "with_header.csv"
        csv_with_header.write_text(
            "IP,Port,Data Center,Region,City,Speed (MB/s),Latency (ms)\n"
            "1.1.1.1,443,LAX,US-West,Los Angeles,5.2,15.5\n"
            "8.8.8.8,443,NYC,US-East,New York,3.1,25.7\n"
        )

        results = handler.load_results_from_file(str(csv_with_header))
        assert len(results) == 2
        assert results[0].ip == "1.1.1.1"
        assert results[0].speed == 5.2
        assert results[0].latency == 15.5

        # Test without header (positional)
        csv_without_header = tmp_path / "without_header.csv"
        csv_without_header.write_text(
            "1.1.1.1,443,LAX,US-West,Los Angeles,5.2,15.5\n"
            "8.8.8.8,443,NYC,US-East,New York,3.1,25.7\n"
        )

        results = handler.load_results_from_file(str(csv_without_header))
        assert len(results) == 2
        assert results[0].ip == "1.1.1.1"

        # Test with malformed rows (should skip them)
        csv_with_errors = tmp_path / "with_errors.csv"
        csv_with_errors.write_text(
            "IP,Port,Data Center,Region,City,Speed (MB/s),Latency (ms)\n"
            "1.1.1.1,443,LAX,US-West,Los Angeles,5.2,15.5\n"
            "invalid,row,with,not,enough,data\n"
            "8.8.8.8,443,NYC,US-East,New York,3.1,25.7\n"
        )

        results = handler.load_results_from_file(str(csv_with_errors))
        assert len(results) == 2  # Should skip the malformed row

        # Test non-existent file
        with pytest.raises(CDNBESTIPError, match="Results file not found"):
            handler.load_results_from_file(str(tmp_path / "nonexistent.csv"))

    def test_save_results_to_file(self, config, tmp_path, sample_results):
        """Test saving results to CSV file."""
        handler = ResultsHandler(config)

        output_file = tmp_path / "output.csv"
        handler.save_results_to_file(sample_results, str(output_file))

        # Verify file was created
        assert output_file.exists()

        # Verify content by loading it back
        loaded_results = handler.load_results_from_file(str(output_file))
        assert len(loaded_results) == len(sample_results)

        # Check first result
        assert loaded_results[0].ip == sample_results[0].ip
        assert loaded_results[0].speed == sample_results[0].speed
        assert loaded_results[0].latency == sample_results[0].latency

    def test_get_results_file_info(self, config, tmp_path):
        """Test getting file information."""
        handler = ResultsHandler(config)

        # Non-existent file
        info = handler.get_results_file_info(str(tmp_path / "nonexistent.csv"))
        assert info["exists"] is False
        assert info["result_count"] == 0
        assert info["is_valid"] is False

        # Valid file
        valid_file = tmp_path / "valid.csv"
        valid_file.write_text(
            "IP,Port,Data Center,Region,City,Speed (MB/s),Latency (ms)\n"
            "1.1.1.1,443,LAX,US-West,Los Angeles,5.2,15.5\n"
        )

        info = handler.get_results_file_info(str(valid_file))
        assert info["exists"] is True
        assert info["result_count"] == 1
        assert info["is_valid"] is True
        assert info["size"] > 0
        assert info["age_hours"] >= 0

    def test_cleanup_old_results(self, config, tmp_path):
        """Test cleanup of old result files."""
        handler = ResultsHandler(config)

        # Create some files with different ages
        old_file1 = tmp_path / "old1.csv"
        old_file2 = tmp_path / "old2.csv"
        new_file = tmp_path / "new.csv"
        non_csv_file = tmp_path / "other.txt"

        # Create files
        for f in [old_file1, old_file2, new_file, non_csv_file]:
            f.write_text("test")

        # Make some files old (8 days ago)
        old_time = time.time() - (8 * 24 * 3600)
        for f in [old_file1, old_file2]:
            os.utime(str(f), (old_time, old_time))

        # Cleanup files older than 7 days
        deleted_count = handler.cleanup_old_results(str(tmp_path), max_age_days=7)

        assert deleted_count == 2  # Should delete old1.csv and old2.csv
        assert not old_file1.exists()
        assert not old_file2.exists()
        assert new_file.exists()  # Should keep new file
        assert non_csv_file.exists()  # Should keep non-CSV file

        # Test with non-existent directory
        deleted_count = handler.cleanup_old_results(str(tmp_path / "nonexistent"), max_age_days=7)
        assert deleted_count == 0

    def test_caching_functionality(self, config, sample_results, tmp_path):
        """Test result caching functionality."""
        handler = ResultsHandler(config)

        cache_key = "test_cache"
        cache_dir = str(tmp_path)

        # Initially no cached results
        cached = handler.get_cached_results(cache_key, cache_dir=cache_dir)
        assert cached is None

        # Cache some results
        success = handler.cache_results(sample_results, cache_key, cache_dir=cache_dir)
        assert success is True

        # Retrieve cached results
        cached = handler.get_cached_results(cache_key, cache_dir=cache_dir)
        assert cached is not None
        assert len(cached) == len(sample_results)
        assert cached[0].ip == sample_results[0].ip

        # Test cache expiration
        cached_expired = handler.get_cached_results(cache_key, max_age_hours=0, cache_dir=cache_dir)
        assert cached_expired is None  # Should be expired

    def test_force_refresh_results(self, config, tmp_path):
        """Test force refresh functionality."""
        handler = ResultsHandler(config)

        # Create a file
        test_file = tmp_path / "test.csv"
        test_file.write_text("test content")
        assert test_file.exists()

        # Force refresh should remove the file
        success = handler.force_refresh_results(str(test_file))
        assert success is True
        assert not test_file.exists()

        # Force refresh on non-existent file should succeed
        success = handler.force_refresh_results(str(test_file))
        assert success is True
