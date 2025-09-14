"""Command-line interface for CDNBESTIP."""

import argparse
import os
import sys

from .config import Config, load_config
from .dns import DNSManager
from .exceptions import (
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
from .ip_sources import IPSourceManager
from .logging_config import (
    PerformanceTimer,
    configure_logging,
    get_logger,
    log_performance,
)
from .models import SpeedTestResult
from .results import ResultsHandler
from .speedtest import SpeedTestManager

# Get logger for this module
logger = get_logger(__name__)

__version__ = "0.1.0"


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments with comprehensive validation."""
    parser = argparse.ArgumentParser(
        prog="cdnbestip",
        description="CloudFlare DNS speed testing and management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -a user@example.com -k api_key -d example.com -p cf -s 2 -n -o

  export CLOUDFLARE_API_KEY="api_key"
  export CLOUDFLARE_email="user@example.com"
  %(prog)s -d example.com -p cf -s 2 -n -o

  # Using extend parameter to pass additional options to CloudflareSpeedTest
  %(prog)s -d example.com -p cf -e="-cfcolo HKG" -n
  %(prog)s -d example.com -p cf -e "\\-cfcolo HKG -a 1" -n

  # Using proxy for Cloudflare API and IP list downloads
  %(prog)s -d example.com -p cf -x http://proxy.example.com:8080 -n

IP Data Sources:
  cf   - CloudFlare IPs
  gc   - GCore IPs
  ct   - CloudFront IPs
  aws  - Amazon AWS IPs
  <url> - Custom IP data URL

Zone Types:
  A, AAAA, CNAME, MX, TXT, SRV, NS, PTR
        """,
    )

    # CloudFlare credentials
    creds_group = parser.add_argument_group("CloudFlare Credentials")
    creds_group.add_argument(
        "-a", "--email", metavar="EMAIL", help="CloudFlare account email"
    )
    creds_group.add_argument("-k", "--key", metavar="API_KEY", help="CloudFlare API key")
    creds_group.add_argument(
        "-t", "--token", metavar="API_TOKEN", help="CloudFlare API token (alternative to key+email)"
    )

    # DNS settings
    dns_group = parser.add_argument_group("DNS Settings")
    dns_group.add_argument(
        "-d", "--domain", metavar="DOMAIN", help="Domain name (required for DNS operations)"
    )
    dns_group.add_argument(
        "-p", "--prefix", metavar="PREFIX", help="DNS record prefix (required for DNS operations)"
    )
    dns_group.add_argument(
        "-y",
        "--type",
        default="A",
        dest="zone_type",
        metavar="TYPE",
        help="DNS record type (default: A)",
    )

    # Speed test settings
    speed_group = parser.add_argument_group("Speed Test Settings")
    speed_group.add_argument(
        "-s",
        "--speed",
        type=float,
        default=2.0,
        metavar="THRESHOLD",
        help="Download speed threshold in MB/s (default: 2.0)",
    )
    speed_group.add_argument(
        "-P", "--port", type=int, metavar="PORT", help="Speed test port (0-65535)"
    )
    speed_group.add_argument("-u", "--url", metavar="URL", help="Speed test URL")
    speed_group.add_argument(
        "-T",
        "--timeout",
        type=int,
        default=600,
        metavar="SECONDS",
        help="Speed test timeout in seconds (default: 600)",
    )
    speed_group.add_argument(
        "-q",
        "--quantity",
        type=int,
        default=0,
        metavar="COUNT",
        help="Number of DNS records to create (default: 0 = unlimited)",
    )

    # IP data source
    data_group = parser.add_argument_group("IP Data Source")
    data_group.add_argument(
        "-i", "--ipurl", metavar="SOURCE", help="IP data source: cf, gc, ct, aws, or custom URL"
    )

    # Operational flags
    ops_group = parser.add_argument_group("Operations")
    ops_group.add_argument(
        "-r", "--refresh", action="store_true", help="Force refresh result.csv file"
    )
    ops_group.add_argument(
        "-n", "--dns", action="store_true", help="Update DNS records after speed test"
    )
    ops_group.add_argument(
        "-o", "--only", action="store_true", help="Only update one DNS record (fastest IP)"
    )

    # Advanced options
    advanced_group = parser.add_argument_group("Advanced Options")
    advanced_group.add_argument("-c", "--cdn", metavar="URL", help="CDN URL for file acceleration")
    advanced_group.add_argument(
        "-e",
        "--extend",
        metavar="STRING",
        help='Extended parameters for CloudflareSpeedTest binary (use -e="-param" or -e "\\-param")',
    )
    advanced_group.add_argument(
        "-x",
        "--proxy",
        metavar="URL",
        help="Proxy URL for Cloudflare API and IP list downloads (e.g., http://proxy.example.com:8080)",
    )

    # Logging and debugging options
    debug_group = parser.add_argument_group("Logging and Debugging")
    debug_group.add_argument(
        "-g", "--debug", action="store_true", help="Enable debug mode with detailed logging"
    )
    debug_group.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    debug_group.add_argument(
        "-l",
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )
    debug_group.add_argument(
        "-C", "--no-console-log", action="store_true", help="Disable console logging"
    )
    debug_group.add_argument(
        "-F", "--no-file-log", action="store_true", help="Disable file logging"
    )

    # Version and help
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    return parser.parse_args()


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate command line arguments before processing.

    Raises:
        ValidationError: If any arguments are invalid
    """
    errors = []

    try:
        # Validate speed threshold
        if args.speed < 0:
            errors.append(
                ValidationError(
                    "Speed threshold must be greater than or equal to 0",
                    field="speed",
                    value=str(args.speed),
                    expected_format="positive number (e.g., 2.0)",
                )
            )

        # Validate port range
        if args.port is not None and not (0 <= args.port <= 65535):
            errors.append(
                ValidationError(
                    f"Port {args.port} is out of valid range",
                    field="port",
                    value=str(args.port),
                    expected_format="0-65535",
                )
            )

        # Validate quantity
        if args.quantity < 0:
            errors.append(
                ValidationError(
                    "Quantity must be greater than or equal to 0",
                    field="quantity",
                    value=str(args.quantity),
                    expected_format="non-negative integer",
                )
            )

        # Validate timeout
        if args.timeout <= 0:
            errors.append(
                ValidationError(
                    "Timeout must be greater than 0",
                    field="timeout",
                    value=str(args.timeout),
                    expected_format="positive integer (e.g., 600)",
                )
            )

        # Validate zone type
        valid_zone_types = ["A", "AAAA", "CNAME", "MX", "TXT", "SRV", "NS", "PTR"]
        if hasattr(args, "zone_type") and args.zone_type.upper() not in valid_zone_types:
            errors.append(
                ValidationError(
                    f"Invalid zone type: {args.zone_type}",
                    field="zone_type",
                    value=args.zone_type,
                    expected_format=f"one of {valid_zone_types}",
                )
            )

        # Validate URL format if provided
        if args.url and not _is_valid_url(args.url):
            errors.append(
                ValidationError(
                    "Invalid speed test URL format",
                    field="url",
                    value=args.url,
                    expected_format="https://example.com/path",
                )
            )

        # Validate CDN URL format if provided
        if args.cdn and not _is_valid_url(args.cdn):
            errors.append(
                ValidationError(
                    "Invalid CDN URL format",
                    field="cdn",
                    value=args.cdn,
                    expected_format="https://example.com/",
                )
            )

        # Validate proxy URL format if provided
        if args.proxy and not _is_valid_proxy_url(args.proxy):
            errors.append(
                ValidationError(
                    "Invalid proxy URL format",
                    field="proxy",
                    value=args.proxy,
                    expected_format="http://proxy.example.com:8080",
                )
            )

        # Validate domain format if provided
        if args.domain and not _is_valid_domain(args.domain):
            errors.append(
                ValidationError(
                    "Invalid domain format",
                    field="domain",
                    value=args.domain,
                    expected_format="example.com",
                )
            )

        # Validate IP data URL if it's not a predefined source
        if args.ipurl:
            predefined_sources = ["cf", "gc", "aws", "ct"]
            if args.ipurl.lower() not in predefined_sources:
                if not _is_valid_url(args.ipurl):
                    errors.append(
                        ValidationError(
                            "Invalid IP data URL format",
                            field="ipurl",
                            value=args.ipurl,
                            expected_format="cf, gc, aws, ct, or https://example.com/ips.json",
                        )
                    )

        # Check for DNS operation requirements
        if args.dns:
            if not args.domain:
                errors.append(
                    ConfigurationError(
                        "Domain is required for DNS operations",
                        field="domain",
                        suggestion="Use -d/--domain option to specify your domain (e.g., -d example.com)",
                    )
                )
            if not args.prefix:
                errors.append(
                    ConfigurationError(
                        "Prefix is required for DNS operations",
                        field="prefix",
                        suggestion="Use -p/--prefix option to specify DNS record prefix (e.g., -p cf)",
                    )
                )

        # Validate conflicting options
        if args.only and not args.dns:
            errors.append(
                ConfigurationError(
                    "--only flag requires --dns flag to be set",
                    suggestion="Use both -n/--dns and -o/--only flags together",
                )
            )

        # If there are validation errors, raise the first one with a summary
        if errors:
            error_messages = [str(error) for error in errors]
            raise ValidationError(
                f"Found {len(errors)} validation error(s):\n"
                + "\n".join(f"  • {msg}" for msg in error_messages),
                suggestion="Fix the validation errors above and try again",
            )

    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Unexpected validation error: {e}") from e


def _is_valid_url(url: str) -> bool:
    """Validate URL format (matches shell script logic)."""
    import re

    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, url))


def _is_valid_domain(domain: str) -> bool:
    """Validate domain format (matches shell script logic)."""
    import re

    # Must contain at least one dot
    if "." not in domain:
        return False

    # Basic domain pattern validation
    pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    return bool(re.match(pattern, domain))


def _is_valid_proxy_url(proxy_url: str) -> bool:
    """Validate proxy URL format."""
    import re

    # Support only http and https proxies
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, proxy_url))


def print_configuration_summary(config: Config) -> None:
    """Print a detailed configuration summary."""
    print("CDNBESTIP Configuration Summary:")
    print("=" * 50)

    # Credentials section
    print("\n📋 Authentication:")
    if config.has_valid_credentials():
        if config.cloudflare_api_token:
            print("  ✓ Method: API Token")
        else:
            print("  ✓ Method: API Key + email")
            print(f"  ✓ Email: {config.cloudflare_email}")
    else:
        print("  ⚠ Status: Not configured")
        print("    Set CLOUDFLARE_API_TOKEN or (CLOUDFLARE_API_KEY + CLOUDFLARE_email)")

    # DNS settings section
    print("\n🌐 DNS Settings:")
    if config.domain:
        print(f"  ✓ Domain: {config.domain}")
    else:
        print("  ⚠ Domain: Not specified")

    if config.prefix:
        print(f"  ✓ Prefix: {config.prefix}")
    else:
        print("  ⚠ Prefix: Not specified")

    print(f"  ✓ Record Type: {config.zone_type}")

    # Speed test settings section
    print("\n⚡ Speed Test Settings:")
    print(f"  ✓ Speed Threshold: {config.speed_threshold} MB/s")

    if config.speed_port:
        print(f"  ✓ Test Port: {config.speed_port}")

    if config.speed_url:
        print(f"  ✓ Test URL: {config.speed_url}")

    if config.quantity > 0:
        print(f"  ✓ Record Limit: {config.quantity}")
    else:
        print("  ✓ Record Limit: Unlimited")

    # IP data source section
    print("\n📊 IP Data Source:")
    if config.ip_data_url:
        source_names = {"cf": "CloudFlare", "gc": "GCore", "ct": "CloudFront", "aws": "Amazon AWS"}
        source_name = source_names.get(config.ip_data_url.lower(), config.ip_data_url)
        print(f"  ✓ Source: {source_name}")
    else:
        print("  ✓ Source: Default (CloudFlare)")

    # Operational settings section
    print("\n⚙️ Operations:")
    operations = []
    if config.refresh:
        operations.append("Force refresh results")
    if config.update_dns:
        if config.only_one:
            operations.append("Update DNS (single record)")
        else:
            operations.append("Update DNS (multiple records)")

    if operations:
        for op in operations:
            print(f"  ✓ {op}")
    else:
        print("  ✓ Speed test only")

    # Advanced settings section
    if config.cdn_url != "https://fastfile.asfd.cn/" or config.extend_string or config.proxy_url:
        print("\n🔧 Advanced Settings:")
        if config.cdn_url != "https://fastfile.asfd.cn/":
            print(f"  ✓ CDN URL: {config.cdn_url}")
        if config.extend_string:
            print(f"  ✓ Extended Params: {config.extend_string}")
        if config.proxy_url:
            print(f"  ✓ Proxy: {config.proxy_url}")

    print("=" * 50)

    # Status summary
    print("\n📈 Status:")
    if config.requires_dns_update():
        print("  ✅ Ready for DNS operations")
    elif config.update_dns:
        print("  ⚠️ DNS update requested but configuration incomplete:")
        if not config.has_valid_credentials():
            print("     - Missing CloudFlare credentials")
        if not config.domain:
            print("     - Missing domain")
        if not config.prefix:
            print("     - Missing prefix")
    else:
        print("  ℹ️ Speed test mode (no DNS updates)")


class WorkflowOrchestrator:
    """Orchestrates the complete CDNBESTIP workflow from speed testing to DNS updates."""

    def __init__(self, config: Config):
        """Initialize workflow orchestrator with configuration."""
        self.config = config
        self.logger = get_logger(__name__)
        self.speedtest_manager = SpeedTestManager(config)
        self.results_handler = ResultsHandler(config)
        self.ip_source_manager = IPSourceManager(config)
        self.dns_manager = None

        # Initialize DNS manager only if needed
        if config.update_dns:
            self.dns_manager = DNSManager(config)

        self.logger.info("Workflow orchestrator initialized")
        self.logger.debug(
            f"Configuration: DNS update={config.update_dns}, "
            f"refresh={config.refresh}, only_one={config.only_one}"
        )

    @log_performance("Complete Workflow")
    def execute(self) -> None:
        """Execute the complete workflow."""
        self.logger.info("Starting workflow execution")

        print("📋 Workflow Steps:")
        print("  1. Prepare IP data source")
        print("  2. Run speed test")
        print("  3. Process results")
        if self.config.update_dns:
            print("  4. Update DNS records")
        print()

        try:
            # Step 1: Prepare IP data source
            with PerformanceTimer("IP Data Preparation", self.logger):
                ip_file = self._prepare_ip_data()

            # Step 2: Run speed test
            with PerformanceTimer("Speed Test Execution", self.logger):
                results_file = self._run_speed_test(ip_file)

            # Step 3: Process results
            with PerformanceTimer("Results Processing", self.logger):
                results = self._process_results(results_file)

            # Step 4: Update DNS records (if requested)
            if self.config.update_dns:
                with PerformanceTimer("DNS Update", self.logger):
                    self._update_dns_records(results)

            # Display final summary
            self._display_summary(results)

            self.logger.info("Workflow execution completed successfully")

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}", exc_info=True)
            raise

    def _prepare_ip_data(self) -> str:
        """
        Prepare IP data source file.

        Returns:
            str: Path to the IP file

        Raises:
            IPSourceError: If IP data preparation fails
            FileError: If file operations fail
        """
        print("📊 Step 1: Preparing IP data source...")

        # Determine IP source
        ip_source = self.config.ip_data_url or "cf"  # Default to CloudFlare
        ip_file = "ip_list.txt"

        try:
            # Check if we need to refresh the IP file
            force_refresh = self.config.refresh or not os.path.exists(ip_file)

            if force_refresh:
                print(f"  📥 Downloading IP list from source: {ip_source}")
                try:
                    self.ip_source_manager.download_ip_list(ip_source, ip_file, force_refresh=True)
                except Exception as e:
                    if "timeout" in str(e).lower() or "connection" in str(e).lower():
                        raise NetworkError(
                            f"Failed to download IP list from {ip_source}",
                            url=ip_source,
                            suggestion="Check your internet connection and try again, or use a different IP source",
                        ) from e
                    elif "not found" in str(e).lower() or "404" in str(e):
                        raise IPSourceError(
                            f"IP source '{ip_source}' not found or unavailable",
                            source=ip_source,
                            suggestion="Try using a different IP source: cf, gc, aws, or ct",
                        ) from e
                    else:
                        raise IPSourceError(
                            f"Failed to download IP list from {ip_source}: {e}", source=ip_source
                        ) from e
            else:
                print(f"  ✓ Using existing IP file: {ip_file}")

            # Verify IP file exists and has content
            if not os.path.exists(ip_file):
                raise FileError(
                    f"IP file not found: {ip_file}",
                    file_path=ip_file,
                    operation="read",
                    suggestion="Try using --refresh flag to download a new IP list",
                )

            try:
                with open(ip_file) as f:
                    ip_lines = [line.strip() for line in f if line.strip()]
                    ip_count = len(ip_lines)

                if ip_count == 0:
                    raise FileError(
                        f"IP file is empty: {ip_file}",
                        file_path=ip_file,
                        suggestion="Use --refresh flag to download a new IP list",
                    )

                print(f"  ✓ IP file ready with {ip_count} IP addresses")
                return ip_file

            except OSError as e:
                raise FileError(
                    f"Cannot read IP file: {ip_file}",
                    file_path=ip_file,
                    operation="read",
                    suggestion="Check file permissions and ensure the file is not corrupted",
                ) from e

        except (IPSourceError, NetworkError, FileError):
            raise
        except Exception as e:
            raise IPSourceError(f"Unexpected error preparing IP data: {e}") from e

    def _run_speed_test(self, ip_file: str) -> str:
        """
        Run speed test using CloudflareSpeedTest binary.

        Args:
            ip_file: Path to IP list file

        Returns:
            str: Path to results file

        Raises:
            BinaryError: If binary management fails
            SpeedTestError: If speed test execution fails
            FileError: If file operations fail
        """
        print("\n⚡ Step 2: Running speed test...")

        results_file = "result.csv"

        try:
            # Check if we need to refresh results
            force_refresh = self.config.refresh or self.speedtest_manager.should_refresh_results(
                results_file
            )

            if force_refresh:
                # Remove existing results file to force regeneration
                if os.path.exists(results_file):
                    try:
                        os.remove(results_file)
                        print(f"  🗑️ Removed existing results file: {results_file}")
                    except OSError as e:
                        print(f"  ⚠️ Warning: Could not remove existing results file: {e}")
                        # Continue anyway, the speed test will overwrite it
                print("  🔧 Ensuring CloudflareSpeedTest binary is available...")
                try:
                    binary_path = self.speedtest_manager.ensure_binary_available()
                    print(f"  ✓ Binary ready: {binary_path}")
                except Exception as e:
                    if "not found" in str(e).lower():
                        raise BinaryError(
                            "CloudflareSpeedTest binary not found",
                            suggestion="The binary will be downloaded automatically. Ensure internet connectivity",
                        ) from e
                    elif "permission" in str(e).lower():
                        raise BinaryError(
                            f"Permission denied accessing binary: {e}",
                            suggestion="Check file permissions or run with appropriate privileges",
                        ) from e
                    elif "no binary available" in str(e).lower():
                        os_name, arch = self.speedtest_manager.get_system_info()
                        raise BinaryError(
                            f"CloudflareSpeedTest binary not available for {os_name}/{arch}",
                            platform_info=f"{os_name}/{arch}",
                            suggestion="Check supported platforms at https://github.com/XIU2/CloudflareSpeedTest/releases",
                        ) from e
                    else:
                        raise BinaryError(f"Binary setup failed: {e}") from e

                print("  🏃 Executing speed test...")
                print(f"    - IP file: {ip_file}")
                print(f"    - Speed threshold: {self.config.speed_threshold} MB/s")
                if self.config.speed_port:
                    print(f"    - Test port: {self.config.speed_port}")
                if self.config.speed_url:
                    print(f"    - Test URL: {self.config.speed_url}")
                if self.config.quantity > 0:
                    print(f"    - Result limit: {self.config.quantity}")

                try:
                    results_file = self.speedtest_manager.run_speed_test(ip_file, results_file)
                    print(f"  ✓ Speed test completed: {results_file}")
                except Exception as e:
                    if "timeout" in str(e).lower():
                        raise SpeedTestError(
                            "Speed test timed out",
                            suggestion="Try reducing the number of IPs with -n option or check network connectivity",
                        ) from e
                    elif "not found" in str(e).lower() and ip_file in str(e):
                        raise FileError(
                            f"IP file not found: {ip_file}",
                            file_path=ip_file,
                            operation="read",
                            suggestion="Ensure the IP file exists and is readable",
                        ) from e
                    elif "return code" in str(e).lower():
                        raise SpeedTestError(
                            f"Speed test binary failed: {e}",
                            suggestion="Check IP file format and network connectivity",
                        ) from e
                    else:
                        raise SpeedTestError(f"Speed test execution failed: {e}") from e
            else:
                print(f"  ✓ Using existing results file: {results_file}")

            # Verify results file exists
            if not os.path.exists(results_file):
                raise FileError(
                    f"Results file not created: {results_file}",
                    file_path=results_file,
                    operation="create",
                    suggestion="Try running with --refresh flag to force a new speed test",
                )

            return results_file

        except (BinaryError, SpeedTestError, FileError):
            raise
        except Exception as e:
            raise SpeedTestError(f"Unexpected error during speed test: {e}") from e

    def _process_results(self, results_file: str) -> list[SpeedTestResult]:
        """Process and filter speed test results."""
        print("\n📈 Step 3: Processing results...")

        try:
            # Parse results from CSV
            print(f"  📄 Parsing results from: {results_file}")
            results = self.speedtest_manager.parse_results(results_file)
            print(f"  ✓ Parsed {len(results)} results")

            # Validate results
            valid_results = self.speedtest_manager.validate_results(results)
            print(f"  ✓ {len(valid_results)} valid results")

            # Filter by speed threshold
            filtered_results = self.results_handler.filter_by_speed(
                valid_results, self.config.speed_threshold
            )
            print(
                f"  ✓ {len(filtered_results)} results above {self.config.speed_threshold} MB/s threshold"
            )

            if not filtered_results:
                print(
                    f"  ⚠️ No results meet the speed threshold of {self.config.speed_threshold} MB/s"
                )
                return []

            # Get top results
            if self.config.only_one:
                top_results = filtered_results[:1]
                print("  ✓ Selected best result (--only mode)")
            elif self.config.quantity > 0:
                top_results = self.results_handler.get_top_results(
                    filtered_results, self.config.quantity
                )
                print(f"  ✓ Selected top {len(top_results)} results")
            else:
                top_results = filtered_results
                print(f"  ✓ Using all {len(top_results)} qualifying results")

            # Display top results
            print("\n  📊 Top Results:")
            for i, result in enumerate(top_results[:5], 1):  # Show top 5
                print(
                    f"    {i}. {result.ip} - {result.speed:.2f} MB/s, {result.latency:.1f}ms ({result.data_center})"
                )

            if len(top_results) > 5:
                print(f"    ... and {len(top_results) - 5} more")

            return top_results

        except Exception as e:
            raise CDNBESTIPError(f"Failed to process results: {e}") from e

    def _update_dns_records(self, results: list[SpeedTestResult]) -> None:
        """
        Update DNS records with the best IP addresses.

        Args:
            results: List of speed test results to use for DNS updates

        Raises:
            AuthenticationError: If CloudFlare authentication fails
            DNSError: If DNS operations fail
            ConfigurationError: If DNS configuration is incomplete
        """
        print("\n🌐 Step 4: Updating DNS records...")

        if not results:
            print("  ⚠️ No results available for DNS update")
            return

        if not self.config.requires_dns_update():
            missing_items = []
            if not self.config.has_valid_credentials():
                missing_items.append("CloudFlare credentials")
            if not self.config.domain:
                missing_items.append("domain")
            if not self.config.prefix:
                missing_items.append("prefix")

            raise ConfigurationError(
                f"DNS update configuration incomplete: missing {', '.join(missing_items)}",
                suggestion="Provide CloudFlare credentials, domain (-d), and prefix (-p) for DNS operations",
            )

        try:
            # Authenticate with CloudFlare
            print("  🔐 Authenticating with CloudFlare API...")
            try:
                self.dns_manager.authenticate()
                print("  ✓ Authentication successful")
            except Exception as e:
                if "invalid" in str(e).lower() or "unauthorized" in str(e).lower():
                    raise AuthenticationError(
                        "CloudFlare authentication failed: Invalid credentials",
                        suggestion="Check your API token/key and ensure it has DNS edit permissions",
                    ) from e
                elif "connection" in str(e).lower() or "timeout" in str(e).lower():
                    raise NetworkError(
                        "Cannot connect to CloudFlare API",
                        suggestion="Check your internet connection and firewall settings",
                    ) from e
                else:
                    raise AuthenticationError(f"Authentication failed: {e}") from e

            # Get zone ID
            print(f"  🔍 Looking up zone for domain: {self.config.domain}")
            try:
                zone_id = self.dns_manager.get_zone_id(self.config.domain)
                print(f"  ✓ Zone ID: {zone_id}")
            except Exception as e:
                if "zone not found" in str(e).lower() or "not found" in str(e).lower():
                    raise DNSError(
                        f"Zone not found for domain: {self.config.domain}",
                        operation="zone_lookup",
                        suggestion="Verify the domain is added to your CloudFlare email and DNS is managed by CloudFlare",
                    ) from e
                elif "permission" in str(e).lower():
                    raise DNSError(
                        f"Permission denied accessing zone for domain: {self.config.domain}",
                        operation="zone_lookup",
                        suggestion="Ensure your API credentials have Zone:Read permissions",
                    ) from e
                else:
                    raise DNSError(f"Failed to get zone ID for {self.config.domain}: {e}") from e

            # Get IP addresses to use
            ip_addresses = [result.ip for result in results]

            try:
                if self.config.only_one:
                    # Update single record
                    record_name = f"{self.config.prefix}.{self.config.domain}"
                    print(f"  📝 Updating single DNS record: {record_name}")

                    dns_record = self.dns_manager.upsert_record(
                        zone_id=zone_id,
                        name=record_name,
                        content=ip_addresses[0],
                        record_type=self.config.zone_type,
                    )
                    print(f"  ✓ Updated: {dns_record.name} -> {dns_record.content}")

                else:
                    # Update multiple records with prefix (cf1, cf2, etc.)
                    print(f"  📝 Updating batch DNS records with prefix: {self.config.prefix}")

                    dns_records = self.dns_manager.batch_upsert_records(
                        zone_id=zone_id,
                        base_name=self.config.prefix,
                        ip_addresses=ip_addresses,
                        record_type=self.config.zone_type,
                    )

                    print(f"  ✓ Updated {len(dns_records)} DNS records:")
                    for record in dns_records:
                        print(f"    - {record.name} -> {record.content}")

                print("  ✅ DNS update completed successfully")

            except Exception as e:
                if "rate limit" in str(e).lower():
                    raise DNSError(
                        "CloudFlare API rate limit exceeded",
                        operation="dns_update",
                        suggestion="Wait a moment and try again. CloudFlare has API rate limits",
                    ) from e
                elif "permission" in str(e).lower():
                    raise DNSError(
                        "Permission denied for DNS operations",
                        operation="dns_update",
                        suggestion="Ensure your API credentials have DNS:Edit permissions for this zone",
                    ) from e
                elif "invalid" in str(e).lower() and "record" in str(e).lower():
                    raise DNSError(
                        f"Invalid DNS record data: {e}",
                        operation="dns_update",
                        suggestion="Check the IP addresses and record configuration",
                    ) from e
                else:
                    raise DNSError(f"DNS update failed: {e}", operation="dns_update") from e

        except (AuthenticationError, DNSError, NetworkError, ConfigurationError):
            raise
        except Exception as e:
            raise DNSError(f"Unexpected error during DNS update: {e}") from e

    def _display_summary(self, results: list[SpeedTestResult]) -> None:
        """Display workflow summary."""
        print("\n" + "=" * 60)
        print("📋 WORKFLOW SUMMARY")
        print("=" * 60)

        if results:
            # Performance summary
            summary = self.results_handler.get_performance_summary(results)

            print("📊 Performance Results:")
            print(f"  • Total results: {summary['total_results']}")
            print(f"  • Above threshold: {summary['results_above_threshold']}")
            print(f"  • Best speed: {summary['max_speed']:.2f} MB/s")
            print(f"  • Average speed: {summary['avg_speed']:.2f} MB/s")
            print(f"  • Best latency: {summary['min_latency']:.1f} ms")
            print(f"  • Average latency: {summary['avg_latency']:.1f} ms")

            # Best result
            best_result = max(results, key=lambda x: x.speed)
            print("\n🏆 Best Result:")
            print(f"  • IP: {best_result.ip}")
            print(f"  • Speed: {best_result.speed:.2f} MB/s")
            print(f"  • Latency: {best_result.latency:.1f} ms")
            print(f"  • Location: {best_result.city}, {best_result.region}")
            print(f"  • Data Center: {best_result.data_center}")

        else:
            print("⚠️ No results met the performance criteria")

        # DNS update status
        if self.config.update_dns:
            if results and self.config.requires_dns_update():
                print("\n🌐 DNS Update Status: ✅ Completed")
                print(f"  • Domain: {self.config.domain}")
                print(f"  • Prefix: {self.config.prefix}")
                print(f"  • Record Type: {self.config.zone_type}")
                if self.config.only_one:
                    print("  • Mode: Single record")
                else:
                    print(f"  • Mode: Multiple records ({len(results)} total)")
            else:
                print("\n🌐 DNS Update Status: ❌ Skipped")
                if not results:
                    print("  • Reason: No qualifying results")
                else:
                    print("  • Reason: Configuration incomplete")
        else:
            print("\n🌐 DNS Update Status: ➖ Not requested")

        print("\n" + "=" * 60)


@log_performance("Command Execution")
def execute_command(args: argparse.Namespace) -> None:
    """
    Execute the requested operation based on CLI arguments.

    Args:
        args: Parsed command line arguments

    Raises:
        ValidationError: If arguments are invalid
        ConfigurationError: If configuration is invalid
        CDNBESTIPError: If workflow execution fails
    """
    # Configure logging based on arguments
    configure_logging(
        level=args.log_level,
        console=not args.no_console_log,
        file_logging=not args.no_file_log,
        debug_mode=args.debug,
        verbose=args.verbose,
    )

    logger.info("Starting CDNBESTIP command execution")
    logger.debug(f"Command line arguments: {vars(args)}")

    # Validate CLI arguments first
    try:
        validate_arguments(args)
        logger.debug("Argument validation successful")
    except ValidationError as e:
        logger.error(f"Argument validation failed: {e}")
        print(f"❌ Validation Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)

    # Load configurationnvironment and CLI args
    try:
        config = load_config(args)
        logger.info("Configuration loaded successfully")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        print(f"❌ Configuration Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected configuration error: {e}")
        print(f"❌ Configuration Error: {e}", file=sys.stderr)
        print("💡 Check your environment variables and command line arguments", file=sys.stderr)
        sys.exit(1)

    # Display configuration summary
    print_configuration_summary(config)

    # Execute the workflow
    try:
        print("\n🚀 Starting CDNBESTIP workflow...")
        workflow = WorkflowOrchestrator(config)
        workflow.execute()
        print("\n✅ Workflow completed successfully!")
        logger.info("Workflow completed successfully")

    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        print(f"\n❌ Authentication Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)

    except DNSError as e:
        logger.error(f"DNS operation failed: {e}")
        print(f"\n❌ DNS Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)

    except SpeedTestError as e:
        logger.error(f"Speed test failed: {e}")
        print(f"\n❌ Speed Test Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)

    except BinaryError as e:
        logger.error(f"Binary error: {e}")
        print(f"\n❌ Binary Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)

    except IPSourceError as e:
        logger.error(f"IP source error: {e}")
        print(f"\n❌ IP Source Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)

    except NetworkError as e:
        logger.error(f"Network error: {e}")
        print(f"\n❌ Network Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)

    except FileError as e:
        logger.error(f"File error: {e}")
        print(f"\n❌ File Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)

    except CDNBESTIPError as e:
        logger.error(f"CDNBESTIP error: {e}")
        print(f"\n❌ Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user")
        print("\n⚠️ Workflow interrupted by user", file=sys.stderr)
        sys.exit(130)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        print(
            "💡 This is an unexpected error. Please check the logs for more details.",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    """
    Main CLI entry point for CDNBESTIP.

    Handles argument parsing, configuration loading, validation,
    and orchestrates the speed test and DNS update workflow.

    Exit codes:
        0: Success
        1: General error
        2: Configuration error
        3: Authentication error
        4: Network error
        130: Interrupted by user (SIGINT)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()
        logger.info("Starting CDNBESTIP application")

        # Execute the requested command
        execute_command(args)

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        print(f"❌ Validation Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        print(f"❌ Configuration Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(2)

    except AuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        print(f"❌ Authentication Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(3)

    except NetworkError as e:
        logger.error(f"Network error: {e}")
        print(f"❌ Network Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(4)

    except CDNBESTIPError as e:
        logger.error(f"CDNBESTIP error: {e}")
        print(f"❌ Error: {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"💡 {e.suggestion}", file=sys.stderr)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        print("\n⚠️ Operation cancelled by user", file=sys.stderr)
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        print(
            "💡 This is an unexpected error. Please report this issue with the error details.",
            file=sys.stderr,
        )

        # Show debug info if available
        debug_info = getattr(e, "get_debug_info", None)
        if debug_info and callable(debug_info):
            print(f"Debug info: {debug_info()}", file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    main()
