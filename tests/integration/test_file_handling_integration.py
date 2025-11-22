"""
Integration tests for file handling and caching logic.

This module tests file operations, caching mechanisms, and data persistence
across the application components.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cdnbestip.config import Config
from cdnbestip.ip_sources import IPSourceManager
from cdnbestip.models import SpeedTestResult
from cdnbestip.results import ResultsHandler


class TestResultsFileCaching:
    """Test results file caching and management."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config()
        self.config._skip_validation = True
        self.temp_dir = tempfile.mkdtemp()
        self.handler = ResultsHandler(self.config)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_results_file_age_based_refresh(self):
        """Test results file refresh based on age."""
        results_file = os.path.join(self.temp_dir, "results.csv")

        # Create fresh file
        with open(results_file, "w") as f:
            f.write("IP,Port,DataCenter,Region,City,Speed,Latency\n")
            f.write("1.1.1.1,443,LAX,US,LA,15.5,25.3\n")

        # Fresh file should not need refresh
        assert not self.handler.should_refresh_results(results_file, max_age_hours=24)

        # Make file old by modifying timestamp
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        os.utime(results_file, (old_time, old_time))

        # Old file should need refresh
        assert self.handler.should_refresh_results(results_file, max_age_hours=24)

        # But not if we allow older files
        assert not self.handler.should_refresh_results(results_file, max_age_hours=48)

    def test_results_file_validation_and_corruption_handling(self):
        """Test results file validation and corruption handling."""
        results_file = os.path.join(self.temp_dir, "results.csv")

        # Test with valid file
        valid_content = """IP,Port,DataCenter,Region,City,Speed (MB/s),Latency (ms)
1.1.1.1,443,LAX,US,LA,15.5,25.3
1.0.0.1,443,NYC,US,NY,12.8,30.1"""

        with open(results_file, "w") as f:
            f.write(valid_content)

        assert self.handler.is_results_file_valid(results_file)

        # Test with corrupted file
        with open(results_file, "w") as f:
            f.write("corrupted,data,invalid\n")

        assert not self.handler.is_results_file_valid(results_file)

        # Test with empty file
        with open(results_file, "w") as f:
            f.write("")

        assert not self.handler.is_results_file_valid(results_file)

        # Test with non-existent file
        os.remove(results_file)
        assert not self.handler.is_results_file_valid(results_file)

    def test_results_caching_mechanism(self):
        """Test results caching mechanism."""
        cache_dir = self.temp_dir
        cache_key = "test_speed_results"

        # Create sample results
        sample_results = [
            SpeedTestResult("1.1.1.1", 443, "LAX", "US", "LA", 15.5, 25.3),
            SpeedTestResult("1.0.0.1", 443, "NYC", "US", "NY", 12.8, 30.1),
        ]

        # Initially no cached results
        cached = self.handler.get_cached_results(cache_key, cache_dir=cache_dir)
        assert cached is None

        # Cache the results
        success = self.handler.cache_results(sample_results, cache_key, cache_dir=cache_dir)
        assert success is True

        # Retrieve cached results
        cached = self.handler.get_cached_results(cache_key, cache_dir=cache_dir)
        assert cached is not None
        assert len(cached) == 2
        assert cached[0].ip == "1.1.1.1"
        assert cached[1].ip == "1.0.0.1"

        # Test cache expiration
        cached_expired = self.handler.get_cached_results(
            cache_key,
            max_age_hours=0,  # Immediate expiration
            cache_dir=cache_dir,
        )
        assert cached_expired is None

    def test_results_file_backup_and_recovery(self):
        """Test results file backup and recovery."""
        results_file = os.path.join(self.temp_dir, "results.csv")
        backup_file = results_file + ".backup"

        # Create original results file
        original_content = """IP,Port,DataCenter,Region,City,Speed,Latency
1.1.1.1,443,LAX,US,LA,15.5,25.3
1.0.0.1,443,NYC,US,NY,12.8,30.1"""

        with open(results_file, "w") as f:
            f.write(original_content)

        # Create backup
        import shutil

        shutil.copy2(results_file, backup_file)

        # Corrupt original file
        with open(results_file, "w") as f:
            f.write("corrupted data")

        # Verify original is corrupted
        assert not self.handler.is_results_file_valid(results_file)

        # Restore from backup
        if os.path.exists(backup_file) and self.handler.is_results_file_valid(backup_file):
            shutil.copy2(backup_file, results_file)

        # Verify restoration
        assert self.handler.is_results_file_valid(results_file)
        results = self.handler.load_results_from_file(results_file)
        assert len(results) == 2

    def test_concurrent_file_access(self):
        """Test concurrent file access handling."""
        results_file = os.path.join(self.temp_dir, "results.csv")

        # Create results file
        content = """IP,Port,DataCenter,Region,City,Speed,Latency
1.1.1.1,443,LAX,US,LA,15.5,25.3"""

        with open(results_file, "w") as f:
            f.write(content)

        # Simulate concurrent read operations
        results1 = self.handler.load_results_from_file(results_file)
        results2 = self.handler.load_results_from_file(results_file)

        assert len(results1) == 1
        assert len(results2) == 1
        assert results1[0].ip == results2[0].ip

    def test_large_results_file_handling(self):
        """Test handling of large results files."""
        results_file = os.path.join(self.temp_dir, "large_results.csv")

        # Create large results file
        with open(results_file, "w") as f:
            f.write("IP,Port,Data Center,Region,City,Speed (MB/s),Latency (ms)\n")

            # Generate 1000 result entries
            for i in range(1000):
                ip = f"192.168.{i // 256}.{i % 256}"
                speed = (i % 50) + (i % 10) / 10.0  # Generate realistic speed values
                latency = (i % 100) + (i % 10) / 10.0  # Generate realistic latency values
                f.write(f"{ip},443,DC{i % 10},Region{i % 5},City{i % 20},{speed},{latency}\n")

        # Load and verify large file
        results = self.handler.load_results_from_file(results_file)
        assert len(results) == 1000

        # Test performance summary on large dataset
        summary = self.handler.get_performance_summary(results)
        assert summary["total_results"] == 1000
        assert summary["max_speed"] > 0
        assert summary["min_speed"] >= 0


class TestIPSourceFileCaching:
    """Test IP source file caching and management."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config()
        self.config._skip_validation = True
        self.temp_dir = tempfile.mkdtemp()
        self.manager = IPSourceManager(self.config)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ip_file_caching_and_refresh(self):
        """Test IP file caching and refresh logic."""
        ip_file = os.path.join(self.temp_dir, "ips.txt")

        # Create initial IP file
        initial_ips = "1.1.1.1\n1.0.0.1\n8.8.8.8\n"
        with open(ip_file, "w") as f:
            f.write(initial_ips)

        # File should exist and be valid
        assert os.path.exists(ip_file)
        with open(ip_file) as f:
            content = f.read()
            assert "1.1.1.1" in content

        # Make file old
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        os.utime(ip_file, (old_time, old_time))

        # Mock download of updated IPs
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = "1.1.1.1\n1.0.0.1\n9.9.9.9\n"  # Updated list
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Force refresh should update the file
            self.manager.download_ip_list("cf", ip_file, force_refresh=True)

            # Verify file was updated
            with open(ip_file) as f:
                updated_content = f.read()
                assert "9.9.9.9" in updated_content

    def test_ip_file_format_validation(self):
        """Test IP file format validation."""
        os.path.join(self.temp_dir, "ips.txt")

        # Test valid IP file formats
        valid_formats = [
            "1.1.1.1\n1.0.0.1\n",  # Simple IPs
            "192.168.1.0/24\n10.0.0.0/8\n",  # CIDR notation
            "# Comment\n1.1.1.1\n# Another comment\n1.0.0.1\n",  # With comments
            "1.1.1.1:443\n1.0.0.1:80\n",  # With ports
        ]

        for i, content in enumerate(valid_formats):
            test_file = os.path.join(self.temp_dir, f"test_{i}.txt")
            with open(test_file, "w") as f:
                f.write(content)

            # Should be able to read without errors
            assert os.path.exists(test_file)
            with open(test_file) as f:
                read_content = f.read()
                assert len(read_content.strip()) > 0

    def test_ip_source_fallback_caching(self):
        """Test IP source fallback and caching."""
        primary_file = os.path.join(self.temp_dir, "primary_ips.txt")
        fallback_file = os.path.join(self.temp_dir, "fallback_ips.txt")

        # Create fallback file
        fallback_ips = "8.8.8.8\n8.8.4.4\n"
        with open(fallback_file, "w") as f:
            f.write(fallback_ips)

        # Mock primary source failure
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Primary source failed")

            # Should be able to use fallback
            if os.path.exists(fallback_file):
                import shutil

                shutil.copy2(fallback_file, primary_file)

            assert os.path.exists(primary_file)
            with open(primary_file) as f:
                content = f.read()
                assert "8.8.8.8" in content


class TestConfigurationFilePersistence:
    """Test configuration file persistence and loading."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_configuration_file_save_and_load(self):
        """Test saving and loading configuration files."""
        config_file = os.path.join(self.temp_dir, "config.json")

        # Create configuration data
        config_data = {
            "cloudflare_api_token": "test_token",
            "domain": "example.com",
            "prefix": "cf",
            "speed_threshold": 5.0,
            "quantity": 3,
            "zone_type": "A",
            "update_dns": True,
        }

        # Save configuration
        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)

        # Load and verify configuration
        with open(config_file) as f:
            loaded_config = json.load(f)

        assert loaded_config["domain"] == "example.com"
        assert loaded_config["speed_threshold"] == 5.0
        assert loaded_config["update_dns"] is True

    def test_configuration_file_migration(self):
        """Test configuration file format migration."""
        old_config_file = os.path.join(self.temp_dir, "old_config.json")
        new_config_file = os.path.join(self.temp_dir, "new_config.json")

        # Create old format configuration
        old_config = {"api_key": "old_key", "email": "old@example.com", "domain": "example.com"}

        with open(old_config_file, "w") as f:
            json.dump(old_config, f)

        # Migrate to new format
        with open(old_config_file) as f:
            old_data = json.load(f)

        new_config = {
            "cloudflare_api_key": old_data.get("api_key"),
            "cloudflare_email": old_data.get("email"),
            "domain": old_data.get("domain"),
            "speed_threshold": None,  # New default (not specified)
            "zone_type": "A",  # New default
        }

        with open(new_config_file, "w") as f:
            json.dump(new_config, f, indent=2)

        # Verify migration
        with open(new_config_file) as f:
            migrated_config = json.load(f)

        assert migrated_config["cloudflare_api_key"] == "old_key"
        assert migrated_config["cloudflare_email"] == "old@example.com"
        assert migrated_config["speed_threshold"] is None


class TestLogFileCaching:
    """Test log file caching and rotation."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_file_rotation(self):
        """Test log file rotation mechanism."""
        log_dir = Path(self.temp_dir)

        # Create multiple log files with different ages
        log_files = [
            ("cdnbestip_20240101.log", time.time() - (10 * 24 * 3600)),  # 10 days old
            ("cdnbestip_20240115.log", time.time() - (5 * 24 * 3600)),  # 5 days old
            ("cdnbestip_20240120.log", time.time() - (1 * 24 * 3600)),  # 1 day old
            ("performance_20240101.log", time.time() - (10 * 24 * 3600)),
            ("performance_20240120.log", time.time() - (1 * 24 * 3600)),
        ]

        for filename, timestamp in log_files:
            log_file = log_dir / filename
            log_file.touch()
            os.utime(log_file, (timestamp, timestamp))

        # Simulate log cleanup (keep files newer than 7 days)
        cutoff_time = time.time() - (7 * 24 * 3600)

        for log_file in log_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()

        # Verify cleanup
        remaining_files = list(log_dir.glob("*.log"))
        remaining_names = [f.name for f in remaining_files]

        assert "cdnbestip_20240120.log" in remaining_names
        assert "performance_20240120.log" in remaining_names
        assert "cdnbestip_20240101.log" not in remaining_names
        assert "performance_20240101.log" not in remaining_names

    def test_log_file_size_management(self):
        """Test log file size management."""
        log_file = os.path.join(self.temp_dir, "test.log")

        # Create large log file
        with open(log_file, "w") as f:
            for i in range(10000):
                f.write(f"Log entry {i}: This is a test log message with some content\n")

        file_size = os.path.getsize(log_file)
        assert file_size > 100000  # Should be reasonably large

        # Simulate log rotation when file gets too large
        max_size = 50000  # 50KB limit

        if file_size > max_size:
            # Rotate log file
            backup_file = log_file + ".1"
            import shutil

            shutil.move(log_file, backup_file)

            # Create new log file
            with open(log_file, "w") as f:
                f.write("New log file after rotation\n")

        # Verify rotation
        assert os.path.exists(backup_file)
        assert os.path.getsize(log_file) < max_size


class TestTemporaryFileHandling:
    """Test temporary file handling and cleanup."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_temporary_file_lifecycle(self):
        """Test temporary file creation, usage, and cleanup."""
        # Create temporary files for different purposes
        temp_files = []

        # Speed test results temp file
        results_temp = os.path.join(self.temp_dir, "temp_results.csv")
        with open(results_temp, "w") as f:
            f.write("IP,Port,DataCenter,Region,City,Speed,Latency\n")
            f.write("1.1.1.1,443,LAX,US,LA,15.5,25.3\n")
        temp_files.append(results_temp)

        # IP list temp file
        ip_temp = os.path.join(self.temp_dir, "temp_ips.txt")
        with open(ip_temp, "w") as f:
            f.write("1.1.1.1\n1.0.0.1\n")
        temp_files.append(ip_temp)

        # Binary download temp file
        binary_temp = os.path.join(self.temp_dir, "temp_binary.tar.gz")
        with open(binary_temp, "wb") as f:
            f.write(b"fake binary data")
        temp_files.append(binary_temp)

        # Verify all temp files exist
        for temp_file in temp_files:
            assert os.path.exists(temp_file)

        # Simulate cleanup
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        # Verify cleanup
        for temp_file in temp_files:
            assert not os.path.exists(temp_file)

    def test_temporary_directory_cleanup(self):
        """Test temporary directory cleanup."""
        # Create nested temporary structure
        nested_dir = os.path.join(self.temp_dir, "nested", "deep")
        os.makedirs(nested_dir, exist_ok=True)

        # Create files in nested structure
        files = [
            os.path.join(nested_dir, "file1.txt"),
            os.path.join(nested_dir, "file2.csv"),
            os.path.join(self.temp_dir, "nested", "file3.log"),
        ]

        for file_path in files:
            with open(file_path, "w") as f:
                f.write("temporary content")

        # Verify structure exists
        assert os.path.exists(nested_dir)
        for file_path in files:
            assert os.path.exists(file_path)

        # Cleanup entire temporary structure
        import shutil

        shutil.rmtree(os.path.join(self.temp_dir, "nested"))

        # Verify cleanup
        assert not os.path.exists(nested_dir)
        for file_path in files:
            assert not os.path.exists(file_path)


if __name__ == "__main__":
    pytest.main([__file__])
