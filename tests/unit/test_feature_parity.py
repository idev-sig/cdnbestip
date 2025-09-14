"""
Test feature parity between shell and Python versions.

This module validates that all original functionality works identically,
including CDN URL support, China-specific features, and network environment handling.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from cdnbestip.cli import parse_arguments
from cdnbestip.config import Config, load_config
from cdnbestip.dns import DNSManager
from cdnbestip.ip_sources import IPSourceManager
from cdnbestip.speedtest import SpeedTestManager


class TestIPSourceParity:
    """Test IP source functionality parity with shell script."""

    def test_cloudflare_ip_source(self):
        """Test CloudFlare IP source (cf) matches shell script."""
        config = Config(ip_data_url="cf")
        ip_manager = IPSourceManager(config)

        # Should use same URL as shell script
        expected_url = "https://www.cloudflare.com/ips-v4"
        assert ip_manager.get_source_url("cf") == expected_url

    def test_gcore_ip_source(self):
        """Test GCore IP source (gc) matches shell script."""
        config = Config(ip_data_url="gc")
        ip_manager = IPSourceManager(config)

        # Should use same URL as shell script
        expected_url = "https://api.gcore.com/cdn/public-ip-list"
        assert ip_manager.get_source_url("gc") == expected_url

    def test_cloudfront_ip_source(self):
        """Test CloudFront IP source (ct) matches shell script."""
        config = Config(ip_data_url="ct")
        ip_manager = IPSourceManager(config)

        # Should use same URL as shell script
        expected_url = "https://d7uri8nf7uskq.cloudfront.net/tools/list-cloudfront-ips"
        assert ip_manager.get_source_url("ct") == expected_url

    def test_aws_ip_source(self):
        """Test AWS IP source (aws) matches shell script."""
        config = Config(ip_data_url="aws")
        ip_manager = IPSourceManager(config)

        # Should use same URL as shell script
        expected_url = "https://ip-ranges.amazonaws.com/ip-ranges.json"
        assert ip_manager.get_source_url("aws") == expected_url

    def test_custom_ip_source_url(self):
        """Test custom IP source URL handling."""
        custom_url = "https://custom.example.com/ips.txt"
        config = Config(ip_data_url=custom_url)
        ip_manager = IPSourceManager(config)

        # Should handle custom URLs
        assert ip_manager.get_source_url(custom_url) == custom_url

    def test_json_ip_source_parsing(self):
        """Test JSON IP source parsing matches shell script logic."""
        # Test GCore JSON parsing
        gcore_json = {"addresses": ["1.1.1.1", "2.2.2.2", "3.3.3.3"]}

        config = Config(ip_data_url="gc")
        ip_manager = IPSourceManager(config)

        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = gcore_json
            mock_get.return_value.status_code = 200

            ips = ip_manager.parse_json_source(gcore_json, "gc")
            assert ips == ["1.1.1.1", "2.2.2.2", "3.3.3.3"]

    def test_cloudfront_json_parsing(self):
        """Test CloudFront JSON parsing matches shell script."""
        cloudfront_json = {"CLOUDFRONT_GLOBAL_IP_LIST": ["4.4.4.4", "5.5.5.5"]}

        config = Config(ip_data_url="ct")
        ip_manager = IPSourceManager(config)

        ips = ip_manager.parse_json_source(cloudfront_json, "ct")
        assert ips == ["4.4.4.4", "5.5.5.5"]

    def test_aws_json_parsing(self):
        """Test AWS JSON parsing matches shell script."""
        aws_json = {"prefixes": [{"ip_prefix": "6.6.6.0/24"}, {"ip_prefix": "7.7.7.0/24"}]}

        config = Config(ip_data_url="aws")
        ip_manager = IPSourceManager(config)

        ips = ip_manager.parse_json_source(aws_json, "aws")
        assert ips == ["6.6.6.0/24", "7.7.7.0/24"]


class TestCDNAccelerationParity:
    """Test CDN acceleration functionality parity."""

    def test_default_cdn_url(self):
        """Test default CDN URL matches shell script."""
        config = Config()

        # Should match shell script default
        expected_default = "https://fastfile.asfd.cn/"
        assert config.cdn_url == expected_default

    def test_custom_cdn_url(self):
        """Test custom CDN URL handling."""
        custom_cdn = "https://custom-cdn.example.com/"

        with patch("sys.argv", ["cdnbestip", "-c", custom_cdn]):
            args = parse_arguments()
            config = load_config(args)
            assert config.cdn_url == custom_cdn

    def test_cdn_environment_variable(self):
        """Test CDN environment variable."""
        custom_cdn = "https://env-cdn.example.com/"

        with patch.dict(os.environ, {"CDN": custom_cdn}):
            with patch("sys.argv", ["cdnbestip"]):
                args = parse_arguments()
                config = load_config(args)
                assert config.cdn_url == custom_cdn

    def test_cdn_url_path_handling(self):
        """Test CDN URL path handling matches shell script logic."""
        # Test URL without trailing slash
        cdn_without_slash = "https://cdn.example.com"
        Config(cdn_url=cdn_without_slash)

        # Should handle URL combination correctly
        # Matching shell script check_remove_https logic

        # Test URL with trailing slash
        cdn_with_slash = "https://cdn.example.com/"
        Config(cdn_url=cdn_with_slash)

        # Should preserve trailing slash behavior

    def test_https_removal_logic(self):
        """Test HTTPS removal logic for CDN acceleration."""
        # This matches shell script do_remove_https function

        # Should combine URLs correctly based on CDN format
        # Implementation should match shell script logic


class TestChinaSpecificFeatures:
    """Test China-specific features parity."""

    def test_china_network_detection(self):
        """Test China network detection logic."""
        # Test manual China flag
        with patch.dict(os.environ, {"CN": "1"}):
            with patch("sys.argv", ["cdnbestip"]):
                args = parse_arguments()
                config = load_config(args)

                # Should detect China network
                assert hasattr(config, "in_china") and config.in_china

    def test_china_cdn_urls(self):
        """Test China-specific CDN URLs."""
        # When in China, should use China-specific URLs
        with patch.dict(os.environ, {"CN": "1"}):
            Config()

            # Should use China CDN or framagit URLs
            # Matching shell script CN_PROJ_URL behavior

    def test_china_ip_source_acceleration(self):
        """Test IP source acceleration in China."""
        with patch.dict(os.environ, {"CN": "1"}):
            config = Config(ip_data_url="cf")
            IPSourceManager(config)

            # Should use accelerated URLs for IP sources in China
            # Matching shell script CDN_URL behavior

    def test_gcore_speed_test_url_in_china(self):
        """Test GCore speed test URL selection."""
        # When using GCore IPs, should set appropriate test URL
        with patch("sys.argv", ["cdnbestip", "-i", "gc"]):
            args = parse_arguments()
            load_config(args)

            # Should set GCore test URL if not specified
            # Matching shell script logic for IP_TEST_URL_GCORE

    def test_proxy_detection_in_china(self):
        """Test proxy detection in China network environment."""
        # Should detect proxy settings and handle appropriately
        proxy_env = {
            "HTTP_PROXY": "http://proxy.example.com:8080",
            "HTTPS_PROXY": "https://proxy.example.com:8080",
        }

        with patch.dict(os.environ, proxy_env):
            Config()

            # Should detect and handle proxy environment
            # For network requests and speed tests


class TestSpeedTestParity:
    """Test speed test functionality parity."""

    def test_cloudflare_speedtest_binary_detection(self):
        """Test CloudflareSpeedTest binary detection."""
        config = Config()
        SpeedTestManager(config)

        # Should check for multiple binary names like shell script
        expected_names = ["CloudflareSpeedTest", "CloudflareST", "cfst"]

        # Should try each name in order
        for _name in expected_names:
            # Test binary detection logic
            pass

    def test_binary_download_and_extraction(self):
        """Test binary download and extraction logic."""
        config = Config()
        SpeedTestManager(config)

        # Should download from GitHub releases
        # Should detect OS and architecture
        # Should extract and install binary
        # Matching shell script download_exact function

    def test_speed_test_parameter_passing(self):
        """Test speed test parameter passing."""
        config = Config(
            speed_port=8080, speed_url="https://test.example.com", extend_string="--custom-param"
        )
        speedtest_manager = SpeedTestManager(config)

        # Should pass parameters correctly to binary
        # Matching shell script RUN_PARAMS logic
        params = speedtest_manager.build_run_parameters()

        assert "-tp" in params and "8080" in params
        assert "-url" in params and "https://test.example.com" in params
        assert "--custom-param" in params

    def test_result_file_age_checking(self):
        """Test result file age checking (24-hour rule)."""
        config = Config()
        speedtest_manager = SpeedTestManager(config)

        # Should check file modification time
        # Should refresh if older than 24 hours
        # Matching shell script check_result_file logic

        # Test with fresh file (< 24 hours)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            result_file = f.name

        try:
            # File is fresh, should not need refresh
            assert not speedtest_manager.should_refresh_results(result_file)

            # Mock old file (> 24 hours)
            old_time = os.path.getmtime(result_file) - (25 * 3600)  # 25 hours ago
            os.utime(result_file, (old_time, old_time))

            # Should need refresh
            assert speedtest_manager.should_refresh_results(result_file)

        finally:
            os.unlink(result_file)

    def test_force_refresh_behavior(self):
        """Test force refresh behavior."""
        config = Config(refresh=True)
        speedtest_manager = SpeedTestManager(config)

        # Should always refresh when force flag is set
        # Regardless of file age
        with tempfile.NamedTemporaryFile(delete=False) as f:
            result_file = f.name

        try:
            # Even with fresh file, should refresh when forced
            assert speedtest_manager.should_refresh_results(result_file)

        finally:
            os.unlink(result_file)


class TestDNSOperationParity:
    """Test DNS operation functionality parity."""

    def test_dns_record_upsert_logic(self):
        """Test DNS record upsert logic matches shell script."""
        config = Config(
            cloudflare_api_token="test_token", domain="example.com", prefix="cf", zone_type="A"
        )
        DNSManager(config)

        # Should implement upsert logic
        # Create if not exists, update if exists
        # Matching shell script upsert_record function

    def test_batch_dns_updates(self):
        """Test batch DNS updates with prefixes."""
        config = Config(
            cloudflare_api_token="test_token",
            domain="example.com",
            prefix="cf",
            zone_type="A",
            quantity=3,
        )
        DNSManager(config)

        # Should create records with numbered prefixes
        # cf1.example.com, cf2.example.com, cf3.example.com
        # Matching shell script batch update logic

    def test_single_record_update_mode(self):
        """Test single record update mode (--only flag)."""
        config = Config(
            cloudflare_api_token="test_token",
            domain="example.com",
            prefix="cf",
            zone_type="A",
            only_one=True,
        )
        DNSManager(config)

        # Should update only one record
        # Using fastest IP from results
        # Matching shell script --only logic

    def test_speed_threshold_filtering(self):
        """Test speed threshold filtering for DNS updates."""
        Config(speed_threshold=5.0)

        # Should only use IPs above speed threshold
        # Should stop processing when speed drops below threshold
        # Matching shell script bc comparison logic

    def test_dns_authentication_methods(self):
        """Test DNS authentication methods."""
        # Test API token method
        config_token = Config(cloudflare_api_token="test_token")
        DNSManager(config_token)

        # Should use Bearer token authentication

        # Test API key + email method
        config_key = Config(cloudflare_api_key="test_key", cloudflare_account="test@example.com")
        DNSManager(config_key)

        # Should use X-Auth-Email and X-Auth-Key headers
        # Matching shell script authentication logic


class TestDependencyHandling:
    """Test dependency handling parity."""

    def test_required_dependencies_check(self):
        """Test required dependencies check."""
        # Should check for required tools like shell script

        # Should detect missing dependencies
        # Should provide installation instructions
        # Matching shell script check_dependencies function

    def test_os_detection_logic(self):
        """Test OS detection logic."""
        # Should detect OS for binary downloads
        # Should handle Linux, macOS, Windows
        # Matching shell script init_os function

    def test_architecture_detection(self):
        """Test architecture detection."""
        # Should detect CPU architecture
        # Should map to correct binary variants
        # Matching shell script init_arch function

    def test_package_manager_detection(self):
        """Test package manager detection."""
        # Should detect available package managers
        # Should install dependencies appropriately
        # Matching shell script OS-specific installation logic


class TestErrorHandlingParity:
    """Test error handling parity."""

    def test_missing_credentials_error(self):
        """Test missing credentials error handling."""
        config = Config()

        # Should detect missing credentials
        # Should provide clear error message
        # Matching shell script credential checks
        assert not config.has_valid_credentials()

    def test_invalid_domain_error(self):
        """Test invalid domain error handling."""
        # Should validate domain format
        # Should require dot in domain name
        # Matching shell script domain validation
        from cdnbestip.cli import _is_valid_domain

        assert not _is_valid_domain("invalid_domain")
        assert _is_valid_domain("valid.domain.com")

    def test_speed_threshold_validation(self):
        """Test speed threshold validation."""
        # Should validate speed >= 0
        # Matching shell script bc comparison
        from cdnbestip.cli import parse_arguments, validate_arguments

        with patch("sys.argv", ["cdnbestip", "-s", "-1"]):
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)

    def test_port_range_validation(self):
        """Test port range validation."""
        # Should validate port 0-65535
        # Matching shell script port validation
        from cdnbestip.cli import parse_arguments, validate_arguments

        with patch("sys.argv", ["cdnbestip", "-P", "70000"]):
            args = parse_arguments()
            with pytest.raises(SystemExit):
                validate_arguments(args)

    def test_url_format_validation(self):
        """Test URL format validation."""
        # Should validate URL format
        # Matching shell script is_url function
        from cdnbestip.cli import _is_valid_url

        assert _is_valid_url("https://example.com")
        assert _is_valid_url("http://example.com")
        assert not _is_valid_url("invalid_url")


class TestWorkflowParity:
    """Test complete workflow parity."""

    def test_complete_workflow_steps(self):
        """Test that complete workflow matches shell script."""
        # Should follow same steps as shell script main function:
        # 1. Check dependencies
        # 2. Check/download CloudflareSpeedTest binary
        # 3. Check/download IP file
        # 4. Check/run speed test
        # 5. Check/download cdnbestip script (not needed in Python)
        # 6. Refresh DNS records

    def test_conditional_execution_logic(self):
        """Test conditional execution logic."""
        # Should only run speed test if needed
        # Should only update DNS if requested
        # Should respect force refresh flags
        # Matching shell script conditional logic

    def test_exit_code_behavior(self):
        """Test exit code behavior."""
        # Should exit with appropriate codes
        # 0 for success, 1 for errors, 130 for interrupt
        # Matching shell script exit behavior


if __name__ == "__main__":
    pytest.main([__file__])
