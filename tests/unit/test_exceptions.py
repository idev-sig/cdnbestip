"""Unit tests for exception classes and error handling."""

from cdnbestip.exceptions import (
    AuthenticationError,
    BinaryError,
    CDNBESTIPError,
    ConfigurationError,
    DNSError,
    FileError,
    IPSourceError,
    NetworkError,
    SpeedTestError,
    ValidationError,
)


class TestCDNBESTIPError:
    """Test base CDNBESTIPError class."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = CDNBESTIPError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.suggestion is None
        assert error.error_code is None
        assert error.details == {}

    def test_error_with_suggestion(self):
        """Test error with suggestion."""
        error = CDNBESTIPError("Test error", suggestion="Try this fix")
        expected = "Test error\n\nSuggestion: Try this fix"
        assert str(error) == expected
        assert error.get_user_message() == expected

    def test_error_with_all_fields(self):
        """Test error with all fields."""
        details = {"field": "value", "code": 123}
        error = CDNBESTIPError(
            "Test error", suggestion="Fix suggestion", error_code="TEST_ERROR", details=details
        )

        assert error.message == "Test error"
        assert error.suggestion == "Fix suggestion"
        assert error.error_code == "TEST_ERROR"
        assert error.details == details

    def test_debug_info(self):
        """Test debug info generation."""
        error = CDNBESTIPError(
            "Test error", suggestion="Fix it", error_code="TEST_CODE", details={"key": "value"}
        )

        debug_info = error.get_debug_info()
        expected = {
            "error_type": "CDNBESTIPError",
            "message": "Test error",
            "suggestion": "Fix it",
            "error_code": "TEST_CODE",
            "details": {"key": "value"},
        }
        assert debug_info == expected


class TestConfigurationError:
    """Test ConfigurationError class."""

    def test_basic_config_error(self):
        """Test basic configuration error."""
        error = ConfigurationError("Invalid config")
        assert error.message == "Invalid config"
        assert error.error_code == "CONFIG_ERROR"

    def test_config_error_with_field(self):
        """Test configuration error with field."""
        error = ConfigurationError("Invalid email", field="cloudflare_account")
        assert error.field == "cloudflare_account"
        assert "Set CLOUDFLARE_ACCOUNT" in error.suggestion

    def test_field_suggestions(self):
        """Test field-specific suggestions."""
        test_cases = [
            ("cloudflare_account", "CLOUDFLARE_ACCOUNT"),
            ("cloudflare_api_key", "CLOUDFLARE_API_KEY"),
            ("domain", "-d/--domain"),
            ("prefix", "-p/--prefix"),
        ]

        for field, expected_text in test_cases:
            error = ConfigurationError("Test error", field=field)
            assert expected_text in error.suggestion

    def test_custom_suggestion(self):
        """Test custom suggestion overrides field suggestion."""
        error = ConfigurationError("Test error", field="domain", suggestion="Custom suggestion")
        assert error.suggestion == "Custom suggestion"


class TestSpeedTestError:
    """Test SpeedTestError class."""

    def test_basic_speedtest_error(self):
        """Test basic speed test error."""
        error = SpeedTestError("Speed test failed")
        assert error.message == "Speed test failed"
        assert error.error_code == "SPEEDTEST_ERROR"

    def test_speedtest_error_with_exit_code(self):
        """Test speed test error with exit code."""
        error = SpeedTestError("Binary failed", exit_code=1)
        assert error.exit_code == 1
        assert "IP file format" in error.suggestion

    def test_timeout_suggestion(self):
        """Test timeout-specific suggestion."""
        error = SpeedTestError("Operation timeout occurred")
        assert "reducing the number of IPs" in error.suggestion

    def test_permission_suggestion(self):
        """Test permission-specific suggestion."""
        error = SpeedTestError("Permission denied")
        assert "file permissions" in error.suggestion

    def test_exit_code_suggestions(self):
        """Test exit code specific suggestions."""
        test_cases = [
            (1, "IP file format"),
            (2, "network connectivity"),
        ]

        for exit_code, expected_text in test_cases:
            error = SpeedTestError("Test error", exit_code=exit_code)
            assert expected_text in error.suggestion


class TestDNSError:
    """Test DNSError class."""

    def test_basic_dns_error(self):
        """Test basic DNS error."""
        error = DNSError("DNS operation failed")
        assert error.message == "DNS operation failed"
        assert error.error_code == "DNS_ERROR"

    def test_dns_error_with_context(self):
        """Test DNS error with context."""
        error = DNSError(
            "Record not found",
            operation="create",
            zone_id="zone123",
            record_name="test.example.com",
        )
        assert error.operation == "create"
        assert error.zone_id == "zone123"
        assert error.record_name == "test.example.com"

    def test_operation_suggestions(self):
        """Test operation-specific suggestions."""
        test_cases = [
            ("zone not found", "domain is added to your CloudFlare account"),
            ("record not found", "Check if the DNS record exists"),
            ("permission denied", "API credentials have DNS edit permissions"),
            ("rate limit", "Wait a moment and try again"),
        ]

        for message, expected_text in test_cases:
            error = DNSError(message)
            assert expected_text in error.suggestion

    def test_create_operation_suggestion(self):
        """Test create operation with existing record."""
        error = DNSError("Record already exists", operation="create")
        assert "update operation instead" in error.suggestion


class TestAuthenticationError:
    """Test AuthenticationError class."""

    def test_basic_auth_error(self):
        """Test basic authentication error."""
        error = AuthenticationError("Auth failed")
        assert error.message == "Auth failed"
        assert error.error_code == "AUTH_ERROR"

    def test_auth_error_with_method(self):
        """Test authentication error with method."""
        error = AuthenticationError("Invalid token", auth_method="token")
        assert error.auth_method == "token"

    def test_auth_method_suggestions(self):
        """Test authentication method specific suggestions."""
        # Token method
        error = AuthenticationError("Invalid credentials", auth_method="token")
        assert "API token" in error.suggestion
        assert "api-tokens" in error.suggestion

        # Key method
        error = AuthenticationError("Invalid credentials", auth_method="key")
        assert "API key and email" in error.suggestion

    def test_expired_token_suggestion(self):
        """Test expired token suggestion."""
        error = AuthenticationError("Token expired")
        assert "expired" in error.suggestion
        assert "Generate a new token" in error.suggestion

    def test_permission_suggestion(self):
        """Test permission error suggestion."""
        error = AuthenticationError("Insufficient permissions")
        assert "Zone:Edit and DNS:Edit permissions" in error.suggestion


class TestBinaryError:
    """Test BinaryError class."""

    def test_basic_binary_error(self):
        """Test basic binary error."""
        error = BinaryError("Binary not found")
        assert error.message == "Binary not found"
        assert error.error_code == "BINARY_ERROR"

    def test_binary_error_with_context(self):
        """Test binary error with context."""
        error = BinaryError(
            "Download failed", binary_path="/path/to/binary", platform_info="linux/amd64"
        )
        assert error.binary_path == "/path/to/binary"
        assert error.platform_info == "linux/amd64"

    def test_binary_suggestions(self):
        """Test binary-specific suggestions."""
        test_cases = [
            ("not found", "downloaded automatically"),
            ("permission denied", "chmod +x"),
            ("no binary available", "not available for your platform"),
            ("download failed", "Check your internet connection"),
        ]

        for message, expected_text in test_cases:
            error = BinaryError(message)
            assert expected_text in error.suggestion

    def test_platform_specific_suggestion(self):
        """Test platform-specific suggestion."""
        error = BinaryError("No binary available", platform_info="unsupported/arch")
        assert "unsupported/arch" in error.suggestion
        assert "github.com/XIU2/CloudflareSpeedTest" in error.suggestion


class TestIPSourceError:
    """Test IPSourceError class."""

    def test_basic_ip_source_error(self):
        """Test basic IP source error."""
        error = IPSourceError("Source failed")
        assert error.message == "Source failed"
        assert error.error_code == "IP_SOURCE_ERROR"

    def test_ip_source_error_with_context(self):
        """Test IP source error with context."""
        error = IPSourceError("Download failed", source="cf", url="https://example.com/ips")
        assert error.source == "cf"
        assert error.url == "https://example.com/ips"

    def test_source_suggestions(self):
        """Test source-specific suggestions."""
        test_cases = [
            ("timeout", "Network connectivity issue"),
            ("connection failed", "Check your internet connection"),
            ("not found", "different source"),
            ("404", "different source"),
            ("invalid format", "invalid data format"),
        ]

        for message, expected_text in test_cases:
            error = IPSourceError(message)
            assert expected_text in error.suggestion

    def test_source_specific_suggestion(self):
        """Test source-specific suggestion."""
        error = IPSourceError("Failed", source="cf")
        assert "source 'cf'" in error.suggestion
        assert "cf, gc, aws" in error.suggestion


class TestNetworkError:
    """Test NetworkError class."""

    def test_basic_network_error(self):
        """Test basic network error."""
        error = NetworkError("Connection failed")
        assert error.message == "Connection failed"
        assert error.error_code == "NETWORK_ERROR"

    def test_network_error_with_context(self):
        """Test network error with context."""
        error = NetworkError("Timeout", url="https://example.com", timeout=30.0)
        assert error.url == "https://example.com"
        assert error.timeout == 30.0

    def test_network_suggestions(self):
        """Test network-specific suggestions."""
        test_cases = [
            ("timeout", "Network timeout occurred"),
            ("ssl certificate", "SSL/TLS certificate issue"),
            ("dns resolution", "DNS resolution failed"),
            ("proxy error", "Proxy configuration issue"),
        ]

        for message, expected_text in test_cases:
            error = NetworkError(message)
            assert expected_text in error.suggestion


class TestValidationError:
    """Test ValidationError class."""

    def test_basic_validation_error(self):
        """Test basic validation error."""
        error = ValidationError("Invalid input")
        assert error.message == "Invalid input"
        assert error.error_code == "VALIDATION_ERROR"

    def test_validation_error_with_context(self):
        """Test validation error with context."""
        error = ValidationError(
            "Invalid email",
            field="email",
            value="invalid-email",
            expected_format="user@example.com",
        )
        assert error.field == "email"
        assert error.value == "invalid-email"
        assert error.expected_format == "user@example.com"
        assert "Expected format: user@example.com" in error.suggestion

    def test_field_suggestions(self):
        """Test field-specific validation suggestions."""
        test_cases = [
            ("email", "valid email format"),
            ("domain", "valid domain format"),
            ("ip", "valid IP address format"),
            ("url", "valid URL format"),
            ("port", "valid port number"),
            ("speed", "positive number"),
        ]

        for field, expected_text in test_cases:
            error = ValidationError("Test error", field=field)
            assert expected_text in error.suggestion


class TestFileError:
    """Test FileError class."""

    def test_basic_file_error(self):
        """Test basic file error."""
        error = FileError("File operation failed")
        assert error.message == "File operation failed"
        assert error.error_code == "FILE_ERROR"

    def test_file_error_with_context(self):
        """Test file error with context."""
        error = FileError("Cannot read file", file_path="/path/to/file", operation="read")
        assert error.file_path == "/path/to/file"
        assert error.operation == "read"

    def test_file_suggestions(self):
        """Test file operation suggestions."""
        test_cases = [
            ("not found", "File not found"),
            ("permission denied", "Permission denied"),
            ("disk space", "Insufficient disk space"),
        ]

        for message, expected_text in test_cases:
            error = FileError(message)
            assert expected_text in error.suggestion

    def test_operation_suggestions(self):
        """Test operation-specific suggestions."""
        # Write operation
        error = FileError("Failed", operation="write")
        assert "Cannot write to file" in error.suggestion

        # Read operation
        error = FileError("Failed", operation="read")
        assert "Cannot read file" in error.suggestion


class TestErrorInheritance:
    """Test error class inheritance."""

    def test_inheritance_hierarchy(self):
        """Test that all errors inherit from CDNBESTIPError."""
        error_classes = [
            ConfigurationError,
            SpeedTestError,
            DNSError,
            AuthenticationError,
            BinaryError,
            IPSourceError,
            NetworkError,
            ValidationError,
            FileError,
        ]

        for error_class in error_classes:
            error = error_class("Test message")
            assert isinstance(error, CDNBESTIPError)
            assert isinstance(error, Exception)

    def test_dns_error_inheritance(self):
        """Test that AuthenticationError inherits from DNSError."""
        error = AuthenticationError("Auth failed")
        assert isinstance(error, DNSError)
        assert isinstance(error, CDNBESTIPError)

    def test_speedtest_error_inheritance(self):
        """Test that BinaryError inherits from SpeedTestError."""
        error = BinaryError("Binary failed")
        assert isinstance(error, SpeedTestError)
        assert isinstance(error, CDNBESTIPError)


class TestErrorScenarios:
    """Test realistic error scenarios."""

    def test_missing_credentials_scenario(self):
        """Test missing credentials error scenario."""
        error = ConfigurationError(
            "CloudFlare credentials required for DNS operations", field="cloudflare_api_token"
        )

        assert "credentials required" in error.message
        assert "CLOUDFLARE_API_TOKEN" in error.suggestion
        assert error.error_code == "CONFIG_ERROR"

    def test_invalid_domain_scenario(self):
        """Test invalid domain error scenario."""
        error = ValidationError(
            "Invalid domain format",
            field="domain",
            value="invalid..domain",
            expected_format="example.com",
        )

        assert "Invalid domain format" in error.message
        assert "example.com" in error.suggestion
        assert error.field == "domain"

    def test_speed_test_timeout_scenario(self):
        """Test speed test timeout scenario."""
        error = SpeedTestError(
            "Speed test timed out after 5 minutes",
            suggestion="Try reducing the number of IPs with -n option",
        )

        assert "timed out" in error.message
        assert "reducing the number of IPs" in error.suggestion

    def test_dns_zone_not_found_scenario(self):
        """Test DNS zone not found scenario."""
        error = DNSError(
            "Zone not found for domain: example.com",
            operation="zone_lookup",
            suggestion="Verify the domain is added to your CloudFlare account",
        )

        assert "Zone not found" in error.message
        assert "CloudFlare account" in error.suggestion
        assert error.operation == "zone_lookup"

    def test_binary_download_failed_scenario(self):
        """Test binary download failed scenario."""
        error = BinaryError(
            "Failed to download CloudflareSpeedTest binary",
            platform_info="linux/amd64",
            suggestion="Check your internet connection and try again",
        )

        assert "download" in error.message
        assert "internet connection" in error.suggestion
        assert error.platform_info == "linux/amd64"
