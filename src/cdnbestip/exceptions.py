"""Exception classes for CDNBESTIP operations."""

from typing import Any


class CDNBESTIPError(Exception):
    """
    Base exception for CDNBESTIP operations.

    Provides structured error handling with user-friendly messages and actionable suggestions.
    """

    def __init__(
        self,
        message: str,
        suggestion: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Initialize CDNBESTIP error.

        Args:
            message: Human-readable error message
            suggestion: Actionable suggestion to resolve the error
            error_code: Machine-readable error code for programmatic handling
            details: Additional error details for debugging
        """
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        """Return formatted error message with suggestion if available."""
        result = self.message
        if self.suggestion:
            result += f"\n\nSuggestion: {self.suggestion}"
        return result

    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        return str(self)

    def get_debug_info(self) -> dict[str, Any]:
        """Get detailed error information for debugging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "suggestion": self.suggestion,
            "error_code": self.error_code,
            "details": self.details,
        }


class ConfigurationError(CDNBESTIPError):
    """Configuration validation errors with specific guidance."""

    def __init__(
        self, message: str, field: str | None = None, suggestion: str | None = None, **kwargs
    ):
        """
        Initialize configuration error.

        Args:
            message: Error message
            field: Configuration field that caused the error
            suggestion: How to fix the configuration
        """
        if not suggestion and field:
            suggestion = self._get_field_suggestion(field)

        super().__init__(message, suggestion, error_code="CONFIG_ERROR", **kwargs)
        self.field = field

    def _get_field_suggestion(self, field: str) -> str:
        """Get field-specific suggestions."""
        suggestions = {
            "cloudflare_account": "Set CLOUDFLARE_ACCOUNT environment variable or use -a/--account option",
            "cloudflare_api_key": "Set CLOUDFLARE_API_KEY environment variable or use -k/--key option",
            "cloudflare_api_token": "Set CLOUDFLARE_API_TOKEN environment variable or use -t/--token option",
            "domain": "Specify domain with -d/--domain option (e.g., example.com)",
            "prefix": "Specify DNS record prefix with -p/--prefix option (e.g., cf)",
            "speed_threshold": "Use -s/--speed option with a positive number (e.g., -s 2.0)",
            "speed_port": "Use -tp/--port option with a valid port number (0-65535)",
            "quantity": "Use -n/--quantity option with a positive number",
        }
        return suggestions.get(field, f"Check the {field} configuration parameter")


class SpeedTestError(CDNBESTIPError):
    """Speed test execution errors with troubleshooting guidance."""

    def __init__(
        self, message: str, suggestion: str | None = None, exit_code: int | None = None, **kwargs
    ):
        """
        Initialize speed test error.

        Args:
            message: Error message
            suggestion: Troubleshooting suggestion
            exit_code: Process exit code if applicable
        """
        if not suggestion:
            suggestion = self._get_default_suggestion(message, exit_code)

        # Use provided error_code or default to SPEEDTEST_ERROR
        error_code = kwargs.pop("error_code", "SPEEDTEST_ERROR")
        super().__init__(message, suggestion=suggestion, error_code=error_code, **kwargs)
        self.exit_code = exit_code

    def _get_default_suggestion(self, message: str, exit_code: int | None) -> str:
        """Get default troubleshooting suggestions."""
        if "timeout" in message.lower():
            return "Try reducing the number of IPs to test with -n option or check your network connection"
        elif "not found" in message.lower():
            return "Ensure CloudflareSpeedTest binary is installed or let the tool download it automatically"
        elif "permission" in message.lower():
            return "Check file permissions or run with appropriate privileges"
        elif exit_code == 1:
            return "Check the IP file format and ensure it contains valid IP addresses"
        elif exit_code == 2:
            return "Verify network connectivity and firewall settings"
        else:
            return "Check network connectivity and try again with different parameters"


class DNSError(CDNBESTIPError):
    """DNS operation errors with CloudFlare-specific guidance."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        zone_id: str | None = None,
        record_name: str | None = None,
        suggestion: str | None = None,
        **kwargs,
    ):
        """
        Initialize DNS error.

        Args:
            message: Error message
            operation: DNS operation that failed (create, update, delete, etc.)
            zone_id: Zone ID if applicable
            record_name: DNS record name if applicable
            suggestion: How to resolve the DNS issue
        """
        if not suggestion:
            suggestion = self._get_operation_suggestion(operation, message)

        # Use provided error_code or default to DNS_ERROR
        error_code = kwargs.pop("error_code", "DNS_ERROR")
        super().__init__(message, suggestion=suggestion, error_code=error_code, **kwargs)
        self.operation = operation
        self.zone_id = zone_id
        self.record_name = record_name

    def _get_operation_suggestion(self, operation: str | None, message: str) -> str:
        """Get operation-specific suggestions."""
        if "zone not found" in message.lower():
            return "Verify the domain is added to your CloudFlare account and DNS is managed by CloudFlare"
        elif "record not found" in message.lower():
            return "Check if the DNS record exists or create it first"
        elif "permission" in message.lower() or "unauthorized" in message.lower():
            return "Verify your API credentials have DNS edit permissions for this zone"
        elif "rate limit" in message.lower():
            return "Wait a moment and try again. CloudFlare API has rate limits"
        elif operation == "create" and "already exists" in message.lower():
            return "Use update operation instead, or delete the existing record first"
        else:
            return "Check your CloudFlare account permissions and zone configuration"


class AuthenticationError(DNSError):
    """CloudFlare authentication errors with credential guidance."""

    def __init__(
        self, message: str, auth_method: str | None = None, suggestion: str | None = None, **kwargs
    ):
        """
        Initialize authentication error.

        Args:
            message: Error message
            auth_method: Authentication method used (token, key, etc.)
            suggestion: How to fix authentication
        """
        if not suggestion:
            suggestion = self._get_auth_suggestion(auth_method, message)

        # Pass error_code to parent
        super().__init__(message, suggestion=suggestion, error_code="AUTH_ERROR", **kwargs)
        self.auth_method = auth_method

    def _get_auth_suggestion(self, auth_method: str | None, message: str) -> str:
        """Get authentication-specific suggestions."""
        if "invalid" in message.lower() or "unauthorized" in message.lower():
            if auth_method == "token":
                return (
                    "Check your API token is correct and has the required permissions. "
                    "Generate a new token at https://dash.cloudflare.com/profile/api-tokens"
                )
            else:
                return (
                    "Verify your API key and email are correct. "
                    "Find your API key at https://dash.cloudflare.com/profile/api-tokens"
                )
        elif "expired" in message.lower():
            return "Your API token has expired. Generate a new token in your CloudFlare dashboard"
        elif "permission" in message.lower():
            return (
                "Your API credentials don't have sufficient permissions. "
                "Ensure the token/key has Zone:Edit and DNS:Edit permissions"
            )
        else:
            return (
                "Check your CloudFlare credentials. Use either API token (recommended) "
                "or API key + email combination"
            )


class BinaryError(SpeedTestError):
    """CloudflareSpeedTest binary related errors with installation guidance."""

    def __init__(
        self,
        message: str,
        binary_path: str | None = None,
        platform_info: str | None = None,
        suggestion: str | None = None,
        **kwargs,
    ):
        """
        Initialize binary error.

        Args:
            message: Error message
            binary_path: Path to binary if applicable
            platform_info: Platform information (OS/arch)
            suggestion: Installation or troubleshooting suggestion
        """
        if not suggestion:
            suggestion = self._get_binary_suggestion(message, platform_info)

        # Pass error_code to parent
        super().__init__(message, suggestion=suggestion, error_code="BINARY_ERROR", **kwargs)
        self.binary_path = binary_path
        self.platform_info = platform_info

    def _get_binary_suggestion(self, message: str, platform_info: str | None) -> str:
        """Get binary-specific suggestions."""
        if "not found" in message.lower():
            return (
                "CloudflareSpeedTest binary will be downloaded automatically. "
                "Ensure you have internet connectivity and sufficient disk space"
            )
        elif "permission" in message.lower():
            return (
                "Check file permissions. The binary needs execute permissions. "
                "Try: chmod +x /path/to/binary"
            )
        elif "no binary available" in message.lower():
            return (
                f"CloudflareSpeedTest binary is not available for your platform ({platform_info}). "
                "Check https://github.com/XIU2/CloudflareSpeedTest/releases for supported platforms"
            )
        elif "download" in message.lower():
            return (
                "Binary download failed. Check your internet connection and try again. "
                "You can also manually download from https://github.com/XIU2/CloudflareSpeedTest/releases"
            )
        else:
            return (
                "Try manually downloading CloudflareSpeedTest binary from "
                "https://github.com/XIU2/CloudflareSpeedTest/releases"
            )


class IPSourceError(CDNBESTIPError):
    """IP data source related errors with source-specific guidance."""

    def __init__(
        self,
        message: str,
        source: str | None = None,
        url: str | None = None,
        suggestion: str | None = None,
        **kwargs,
    ):
        """
        Initialize IP source error.

        Args:
            message: Error message
            source: IP source name (cf, gc, aws, etc.)
            url: Source URL if applicable
            suggestion: How to resolve the source issue
        """
        if not suggestion:
            suggestion = self._get_source_suggestion(source, message)

        super().__init__(message, suggestion, error_code="IP_SOURCE_ERROR", **kwargs)
        self.source = source
        self.url = url

    def _get_source_suggestion(self, source: str | None, message: str) -> str:
        """Get source-specific suggestions."""
        if "timeout" in message.lower() or "connection" in message.lower():
            return (
                "Network connectivity issue. Check your internet connection and try again. "
                "You can also try a different IP source with -ipurl option"
            )
        elif "not found" in message.lower() or "404" in message:
            return (
                "IP source URL is not accessible. Try using a different source: "
                "cf (CloudFlare), gc (GCore), aws (AWS), or ct (CloudFront)"
            )
        elif "invalid format" in message.lower():
            return (
                "IP source returned invalid data format. "
                "Try using a different source or check the source URL"
            )
        elif source:
            return (
                f"Issue with IP source '{source}'. Try using a different source: "
                "cf, gc, aws, or ct, or provide a custom URL with -ipurl"
            )
        else:
            return (
                "IP source issue. Try using a predefined source (cf, gc, aws, ct) "
                "or check your custom IP source URL"
            )


class NetworkError(CDNBESTIPError):
    """Network-related errors with connectivity guidance."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        timeout: float | None = None,
        suggestion: str | None = None,
        **kwargs,
    ):
        """
        Initialize network error.

        Args:
            message: Error message
            url: URL that failed if applicable
            timeout: Timeout value if applicable
            suggestion: Network troubleshooting suggestion
        """
        if not suggestion:
            suggestion = self._get_network_suggestion(message, timeout)

        super().__init__(message, suggestion, error_code="NETWORK_ERROR", **kwargs)
        self.url = url
        self.timeout = timeout

    def _get_network_suggestion(self, message: str, timeout: float | None) -> str:
        """Get network-specific suggestions."""
        if "timeout" in message.lower():
            return (
                "Network timeout occurred. Check your internet connection, "
                "firewall settings, and try again. You may need to use a proxy or VPN"
            )
        elif "ssl" in message.lower() or "certificate" in message.lower():
            return (
                "SSL/TLS certificate issue. Check your system time and certificates. "
                "You may need to update your system or use a different network"
            )
        elif "dns" in message.lower():
            return "DNS resolution failed. Check your DNS settings and internet connectivity"
        elif "proxy" in message.lower():
            return "Proxy configuration issue. Check your proxy settings or try without proxy"
        else:
            return (
                "Network connectivity issue. Check your internet connection, "
                "firewall settings, and proxy configuration"
            )


class ValidationError(CDNBESTIPError):
    """Data validation errors with format guidance."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: str | None = None,
        expected_format: str | None = None,
        suggestion: str | None = None,
        **kwargs,
    ):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            value: Invalid value
            expected_format: Expected format description
            suggestion: How to fix the validation issue
        """
        if not suggestion and expected_format:
            suggestion = f"Expected format: {expected_format}"
        elif not suggestion:
            suggestion = self._get_validation_suggestion(field)

        super().__init__(message, suggestion, error_code="VALIDATION_ERROR", **kwargs)
        self.field = field
        self.value = value
        self.expected_format = expected_format

    def _get_validation_suggestion(self, field: str | None) -> str:
        """Get validation-specific suggestions."""
        suggestions = {
            "email": "Use a valid email format: user@example.com",
            "domain": "Use a valid domain format: example.com",
            "ip": "Use a valid IP address format: 192.168.1.1",
            "url": "Use a valid URL format: https://example.com",
            "port": "Use a valid port number: 1-65535",
            "speed": "Use a positive number for speed threshold",
        }
        return suggestions.get(field, "Check the input format and try again")


class FileError(CDNBESTIPError):
    """File operation errors with file-specific guidance."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        operation: str | None = None,
        suggestion: str | None = None,
        **kwargs,
    ):
        """
        Initialize file error.

        Args:
            message: Error message
            file_path: File path that caused the error
            operation: File operation (read, write, delete, etc.)
            suggestion: How to resolve the file issue
        """
        if not suggestion:
            suggestion = self._get_file_suggestion(operation, message)

        super().__init__(message, suggestion, error_code="FILE_ERROR", **kwargs)
        self.file_path = file_path
        self.operation = operation

    def _get_file_suggestion(self, operation: str | None, message: str) -> str:
        """Get file operation suggestions."""
        if "not found" in message.lower():
            return (
                "File not found. Check the file path and ensure the file exists. "
                "The tool may need to download or create the file first"
            )
        elif "permission" in message.lower():
            return (
                "Permission denied. Check file permissions and ensure you have "
                "read/write access to the file and directory"
            )
        elif "disk" in message.lower() or "space" in message.lower():
            return "Insufficient disk space. Free up some disk space and try again"
        elif operation == "write":
            return "Cannot write to file. Check directory permissions and disk space"
        elif operation == "read":
            return "Cannot read file. Check file exists and you have read permissions"
        else:
            return "File operation failed. Check file path, permissions, and disk space"
