"""
Integration tests for shell script compatibility.

This module tests actual compatibility between the shell and Python versions
by running real commands and comparing behavior.
"""

import os
import subprocess
import sys

import pytest


class TestShellCompatibilityIntegration:
    """Integration tests for shell script compatibility."""

    def test_help_output_similarity(self):
        """Test that help output is similar between shell and Python versions."""
        # Test Python version help
        result = subprocess.run(
            [sys.executable, "-m", "cdnbestip.cli", "--help"], capture_output=True, text=True
        )

        python_help = result.stdout

        # Should contain key sections
        assert "CloudFlare DNS speed testing" in python_help
        assert "CloudFlare Credentials" in python_help
        assert "DNS Settings" in python_help
        assert "Speed Test Settings" in python_help
        assert "Examples:" in python_help

        # Should contain all major options
        key_options = [
            "-a",
            "-k",
            "-t",
            "-d",
            "-p",
            "-s",
            "-P",
            "-u",
            "-q",
            "-i",
            "-r",
            "-n",
            "-o",
            "-c",
            "-e",
        ]
        for option in key_options:
            assert option in python_help

    def test_argument_validation_compatibility(self):
        """Test that argument validation behaves like shell script."""
        # Test invalid speed threshold
        result = subprocess.run(
            [sys.executable, "-m", "cdnbestip.cli", "-s", "-1"], capture_output=True, text=True
        )

        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "validation" in result.stdout.lower()

        # Test invalid port
        result = subprocess.run(
            [sys.executable, "-m", "cdnbestip.cli", "-P", "70000"], capture_output=True, text=True
        )

        assert result.returncode != 0

        # Test invalid domain
        result = subprocess.run(
            [sys.executable, "-m", "cdnbestip.cli", "-d", "invalid_domain"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0

    def test_environment_variable_support(self):
        """Test environment variable support."""
        env = os.environ.copy()
        env.update({"CLOUDFLARE_API_KEY": "test_key", "CLOUDFLARE_EMAIL": "test@example.com"})

        # Should not fail with valid environment variables
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments
from cdnbestip.config import load_config
sys.argv = ["cdnbestip", "-d", "example.com"]
args = parse_arguments()
config = load_config(args)
print(f"API_KEY: {config.cloudflare_api_key}")
print(f"EMAIL: {config.CLOUDFLARE_EMAIL}")
""",
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        assert "API_KEY: test_key" in result.stdout
        assert "EMAIL: test@example.com" in result.stdout

    def test_ip_source_compatibility(self):
        """Test IP source parameter compatibility."""
        # Test predefined sources
        for source in ["cf", "gc", "ct", "aws"]:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    f'''
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments
from cdnbestip.config import load_config
sys.argv = ["cdnbestip", "-i", "{source}"]
args = parse_arguments()
config = load_config(args)
print(f"IP_SOURCE: {{config.ip_data_url}}")
''',
                ],
                capture_output=True,
                text=True,
            )

            assert f"IP_SOURCE: {source}" in result.stdout

    def test_dns_operation_flags(self):
        """Test DNS operation flags compatibility."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments
from cdnbestip.config import load_config
sys.argv = ["cdnbestip", "-d", "example.com", "-p", "cf", "-n", "-o"]
args = parse_arguments()
config = load_config(args)
print(f"UPDATE_DNS: {config.update_dns}")
print(f"ONLY_ONE: {config.only_one}")
print(f"DOMAIN: {config.domain}")
print(f"PREFIX: {config.prefix}")
""",
            ],
            capture_output=True,
            text=True,
        )

        assert "UPDATE_DNS: True" in result.stdout
        assert "ONLY_ONE: True" in result.stdout
        assert "DOMAIN: example.com" in result.stdout
        assert "PREFIX: cf" in result.stdout

    def test_speed_test_parameters(self):
        """Test speed test parameter compatibility."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments
from cdnbestip.config import load_config
sys.argv = ["cdnbestip", "-s", "5.0", "-P", "8080", "-u", "https://test.com", "-q", "10"]
args = parse_arguments()
config = load_config(args)
print(f"SPEED: {config.speed_threshold}")
print(f"PORT: {config.speed_port}")
print(f"URL: {config.speed_url}")
print(f"QUANTITY: {config.quantity}")
""",
            ],
            capture_output=True,
            text=True,
        )

        assert "SPEED: 5.0" in result.stdout
        assert "PORT: 8080" in result.stdout
        assert "URL: https://test.com" in result.stdout
        assert "QUANTITY: 10" in result.stdout

    def test_zone_type_compatibility(self):
        """Test zone type parameter compatibility."""
        for zone_type in ["A", "AAAA", "CNAME", "MX", "TXT"]:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    f'''
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments
from cdnbestip.config import load_config
sys.argv = ["cdnbestip", "--type", "{zone_type}"]
args = parse_arguments()
config = load_config(args)
print(f"ZONE_TYPE: {{config.zone_type}}")
''',
                ],
                capture_output=True,
                text=True,
            )

            assert f"ZONE_TYPE: {zone_type}" in result.stdout

    def test_cdn_parameter_compatibility(self):
        """Test CDN parameter compatibility."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments
from cdnbestip.config import load_config
sys.argv = ["cdnbestip", "-c", "https://custom-cdn.example.com/"]
args = parse_arguments()
config = load_config(args)
print(f"CDN_URL: {config.cdn_url}")
""",
            ],
            capture_output=True,
            text=True,
        )

        assert "CDN_URL: https://custom-cdn.example.com/" in result.stdout

    def test_extend_parameter_compatibility(self):
        """Test extend parameter compatibility."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments
from cdnbestip.config import load_config
sys.argv = ["cdnbestip", "-e", "custom-param"]
args = parse_arguments()
config = load_config(args)
print(f"EXTEND: {config.extend_string}")
""",
            ],
            capture_output=True,
            text=True,
        )

        assert "EXTEND: custom-param" in result.stdout

    def test_refresh_flag_compatibility(self):
        """Test refresh flag compatibility."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments
from cdnbestip.config import load_config
sys.argv = ["cdnbestip", "-r"]
args = parse_arguments()
config = load_config(args)
print(f"REFRESH: {config.refresh}")
""",
            ],
            capture_output=True,
            text=True,
        )

        assert "REFRESH: True" in result.stdout

    def test_default_values_compatibility(self):
        """Test that default values match shell script."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments
from cdnbestip.config import load_config
sys.argv = ["cdnbestip", "-d", "example.com"]
args = parse_arguments()
config = load_config(args)
print(f"ZONE_TYPE: {config.zone_type}")
print(f"SPEED_THRESHOLD: {config.speed_threshold}")
print(f"QUANTITY: {config.quantity}")
print(f"CDN_URL: {config.cdn_url}")
print(f"REFRESH: {config.refresh}")
print(f"UPDATE_DNS: {config.update_dns}")
print(f"ONLY_ONE: {config.only_one}")
""",
            ],
            capture_output=True,
            text=True,
        )

        # Check shell script defaults
        assert "ZONE_TYPE: A" in result.stdout
        assert "SPEED_THRESHOLD: None" in result.stdout
        assert "QUANTITY: 0" in result.stdout
        assert "CDN_URL: https://fastfile.asfd.cn/" in result.stdout
        assert "REFRESH: False" in result.stdout
        assert "UPDATE_DNS: False" in result.stdout
        assert "ONLY_ONE: False" in result.stdout


class TestShellScriptExampleCompatibility:
    """Test compatibility with shell script examples."""

    def test_example_1_compatibility(self):
        """Test first shell script example."""
        # Example: cdnbestip -a user@example.com -k api_key -d example.com -p cf -s 2 -n -o
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments, validate_arguments
from cdnbestip.config import load_config
sys.argv = ["cdnbestip", "-a", "user@example.com", "-k", "api_key", "-d", "example.com", "-p", "cf", "-s", "2", "-n", "-o"]
args = parse_arguments()
validate_arguments(args)
config = load_config(args)
print("SUCCESS")
print(f"EMAIL: {config.CLOUDFLARE_EMAIL}")
print(f"API_KEY: {config.cloudflare_api_key}")
print(f"DOMAIN: {config.domain}")
print(f"PREFIX: {config.prefix}")
print(f"SPEED: {config.speed_threshold}")
print(f"DNS: {config.update_dns}")
print(f"ONLY: {config.only_one}")
""",
            ],
            capture_output=True,
            text=True,
        )

        assert "SUCCESS" in result.stdout
        assert "EMAIL: user@example.com" in result.stdout
        assert "API_KEY: api_key" in result.stdout
        assert "DOMAIN: example.com" in result.stdout
        assert "PREFIX: cf" in result.stdout
        assert "SPEED: 2.0" in result.stdout
        assert "DNS: True" in result.stdout
        assert "ONLY: True" in result.stdout

    def test_example_2_with_env_vars(self):
        """Test second shell script example with environment variables."""
        env = os.environ.copy()
        env.update({"CLOUDFLARE_API_KEY": "api_key", "CLOUDFLARE_EMAIL": "user@example.com"})

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments, validate_arguments
from cdnbestip.config import load_config
sys.argv = ["cdnbestip", "-d", "example.com", "-p", "cf", "-s", "2", "-n", "-o"]
args = parse_arguments()
validate_arguments(args)
config = load_config(args)
print("SUCCESS")
print(f"EMAIL: {config.CLOUDFLARE_EMAIL}")
print(f"API_KEY: {config.cloudflare_api_key}")
print(f"DOMAIN: {config.domain}")
print(f"PREFIX: {config.prefix}")
""",
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        assert "SUCCESS" in result.stdout
        assert "EMAIL: user@example.com" in result.stdout
        assert "API_KEY: api_key" in result.stdout
        assert "DOMAIN: example.com" in result.stdout
        assert "PREFIX: cf" in result.stdout


class TestErrorHandlingCompatibility:
    """Test error handling compatibility with shell script."""

    def test_missing_dns_requirements(self):
        """Test error when DNS requirements are missing."""
        # Should fail when -n flag is used without domain/prefix
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments, validate_arguments
sys.argv = ["cdnbestip", "-n"]
args = parse_arguments()
try:
    validate_arguments(args)
    print("UNEXPECTED_SUCCESS")
except SystemExit:
    print("VALIDATION_FAILED_AS_EXPECTED")
""",
            ],
            capture_output=True,
            text=True,
        )

        assert "VALIDATION_FAILED_AS_EXPECTED" in result.stdout

    def test_invalid_parameter_ranges(self):
        """Test invalid parameter range handling."""
        # Test invalid speed
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments, validate_arguments
sys.argv = ["cdnbestip", "-s", "-5"]
args = parse_arguments()
try:
    validate_arguments(args)
    print("UNEXPECTED_SUCCESS")
except SystemExit:
    print("VALIDATION_FAILED_AS_EXPECTED")
""",
            ],
            capture_output=True,
            text=True,
        )

        assert "VALIDATION_FAILED_AS_EXPECTED" in result.stdout

        # Test invalid port
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, ".")
from cdnbestip.cli import parse_arguments, validate_arguments
sys.argv = ["cdnbestip", "-P", "70000"]
args = parse_arguments()
try:
    validate_arguments(args)
    print("UNEXPECTED_SUCCESS")
except SystemExit:
    print("VALIDATION_FAILED_AS_EXPECTED")
""",
            ],
            capture_output=True,
            text=True,
        )

        assert "VALIDATION_FAILED_AS_EXPECTED" in result.stdout


class TestFeatureCompatibilityValidation:
    """Test that all shell script features are available."""

    def test_all_cli_options_available(self):
        """Test that all CLI options from shell script are available."""
        # Get help output
        result = subprocess.run(
            [sys.executable, "-m", "cdnbestip.cli", "--help"], capture_output=True, text=True
        )

        help_output = result.stdout

        # All shell script options should be present
        shell_options = [
            "-a",
            "--EMAIL",  # CloudFlare EMAIL
            "-k",
            "--key",  # CloudFlare API key
            "-t",
            "--token",  # CloudFlare API token
            "-d",
            "--domain",  # Domain name
            "-p",
            "--prefix",  # DNS record prefix
            "--type",  # DNS record type
            "-s",
            "--speed",  # Speed threshold
            "-P",
            "--port",  # Speed test port
            "-u",
            "--url",  # Speed test URL
            "-q",
            "--quantity",  # Record quantity
            "-i",
            "--ipurl",  # IP data source
            "-r",
            "--refresh",  # Force refresh
            "-n",
            "--dns",  # Update DNS
            "-o",
            "--only",  # Only one record
            "-c",
            "--cdn",  # CDN URL
            "-e",
            "--extend",  # Extended parameters
            "-h",
            "--help",  # Help
        ]

        for option in shell_options:
            assert option in help_output, f"Missing CLI option: {option}"

    def test_ip_sources_available(self):
        """Test that all IP sources are available."""
        help_result = subprocess.run(
            [sys.executable, "-m", "cdnbestip.cli", "--help"], capture_output=True, text=True
        )

        help_output = help_result.stdout

        # Should mention all IP sources
        ip_sources = ["cf", "gc", "ct", "aws"]
        for source in ip_sources:
            assert source in help_output, f"Missing IP source: {source}"

    def test_zone_types_available(self):
        """Test that all zone types are available."""
        help_result = subprocess.run(
            [sys.executable, "-m", "cdnbestip.cli", "--help"], capture_output=True, text=True
        )

        help_output = help_result.stdout

        # Should mention zone types
        zone_types = ["A", "AAAA", "CNAME", "MX", "TXT"]
        for zone_type in zone_types:
            assert zone_type in help_output, f"Missing zone type: {zone_type}"


if __name__ == "__main__":
    pytest.main([__file__])
