"""Speed test management and binary handling."""

import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

import requests

from .config import Config, is_china_network
from .exceptions import BinaryError, SpeedTestError
from .logging_config import get_logger, log_function_call, log_performance
from .models import SpeedTestResult

logger = get_logger(__name__)


class SpeedTestManager:
    """Manages CloudflareSpeedTest binary and execution."""

    BINARY_NAMES = ["CloudflareSpeedTest", "CloudflareST", "cfst"]
    GITHUB_REPO = "XIU2/CloudflareSpeedTest"
    BINARY_VERSION = "v2.3.4"  # Current stable version

    def __init__(self, config: Config):
        """Initialize speed test manager with configuration."""
        self.config = config
        self.binary_path: str | None = None
        self.binary_dir = Path.home() / ".cdnbestip" / "bin"
        self.binary_dir.mkdir(parents=True, exist_ok=True)

    @log_function_call
    @log_performance("Binary Availability Check")
    def ensure_binary_available(self) -> str:
        """Ensure CloudflareSpeedTest binary is available."""
        logger.info("Ensuring CloudflareSpeedTest binary is available")

        # First check if binary is already available in system PATH
        existing_binary = self._find_existing_binary()
        if existing_binary:
            logger.info(f"Found existing binary in PATH: {existing_binary}")
            self.binary_path = existing_binary
            return existing_binary

        # Check if we have a cached binary
        cached_binary = self._get_cached_binary_path()
        if cached_binary and self._verify_binary(cached_binary):
            logger.info(f"Using cached binary: {cached_binary}")
            self.binary_path = cached_binary
            return cached_binary

        # Download and install binary
        logger.info("No existing binary found, downloading...")
        return self._download_and_install_binary()

    def _find_existing_binary(self) -> str | None:
        """Find existing CloudflareSpeedTest binary in system PATH."""
        for binary_name in self.BINARY_NAMES:
            if shutil.which(binary_name):
                return binary_name
        return None

    def _get_cached_binary_path(self) -> str | None:
        """Get path to cached binary."""
        os_name, arch = self.get_system_info()
        binary_name = "cfst"
        if os_name == "windows":
            binary_name += ".exe"

        cached_path = self.binary_dir / binary_name
        return str(cached_path) if cached_path.exists() else None

    def _verify_binary(self, binary_path: str) -> bool:
        """Verify that binary is executable and working."""
        try:
            result = subprocess.run(
                [binary_path, "-h"],
                capture_output=True,
                timeout=10,
                check=False,
                encoding="utf-8",
                errors="ignore",
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            return False

    def _download_and_install_binary(self) -> str:
        """Download and install CloudflareSpeedTest binary."""
        os_name, arch = self.get_system_info()

        # Get download URL from GitHub releases
        download_url = self._get_download_url(os_name, arch)
        if not download_url:
            raise BinaryError(f"No binary available for {os_name}/{arch}")

        # Download and extract binary
        binary_path = self._download_binary(download_url, os_name, arch)

        # Verify the downloaded binary
        if not self._verify_binary(binary_path):
            raise BinaryError(f"Downloaded binary is not working: {binary_path}")

        self.binary_path = binary_path
        return binary_path

    def _get_download_url(self, os_name: str, arch: str) -> str | None:
        """Get download URL for the binary from GitHub releases."""
        try:
            # Use CDN URL only if in China network and not using proxy
            # When using proxy, access original URL directly
            api_url = f"https://api.github.com/repos/{self.GITHUB_REPO}/releases/latest"
            use_cdn = (
                is_china_network()
                and hasattr(self.config, "cdn_url")
                and self.config.cdn_url
                and not (hasattr(self.config, "proxy_url") and self.config.proxy_url)
            )
            if use_cdn:
                api_url = self.config.cdn_url + api_url

            # Prepare request parameters
            request_kwargs = {"timeout": 30}

            # Add proxy configuration if available
            if hasattr(self.config, "proxy_url") and self.config.proxy_url:
                proxies = self._get_proxy_config(self.config.proxy_url)
                request_kwargs["proxies"] = proxies

            response = requests.get(api_url, **request_kwargs)
            response.raise_for_status()

            release_data = response.json()

            # Find matching asset
            for asset in release_data.get("assets", []):
                asset_name = asset["name"].lower()
                if os_name in asset_name and arch in asset_name:
                    download_url = asset["browser_download_url"]
                    # Apply CDN URL only if in China network and not using proxy
                    if use_cdn:
                        download_url = self.config.cdn_url + download_url
                    return download_url

            return None

        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            raise BinaryError(f"Failed to get download URL: {e}") from e

    def _download_binary(self, download_url: str, os_name: str, arch: str) -> str:
        """Download and extract binary from URL."""
        try:
            # Create temporary directory for download
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Determine archive type from URL
                if download_url.lower().endswith(".zip"):
                    archive_path = temp_path / "binary.zip"
                    is_zip = True
                else:
                    archive_path = temp_path / "binary.tar.gz"
                    is_zip = False

                # Prepare request parameters
                request_kwargs = {"timeout": 300, "stream": True}

                # Add proxy configuration if available
                if hasattr(self.config, "proxy_url") and self.config.proxy_url:
                    proxies = self._get_proxy_config(self.config.proxy_url)
                    request_kwargs["proxies"] = proxies

                # Download archive
                response = requests.get(download_url, **request_kwargs)
                response.raise_for_status()

                with open(archive_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Extract archive based on type
                if is_zip:
                    with zipfile.ZipFile(archive_path) as zip_file:
                        zip_file.extractall(temp_path)
                else:
                    with tarfile.open(archive_path, "r:gz") as tar:
                        tar.extractall(temp_path)

                # Find the binary in extracted files
                binary_name = "cfst"
                if os_name == "windows":
                    binary_name += ".exe"

                # Look for the binary file
                extracted_binary = None
                for file_path in temp_path.rglob("*"):
                    if file_path.is_file() and file_path.name.lower() in [
                        "cloudflare-speedtest",
                        "cloudflarest",
                        "cfst",
                        "cloudflare-speedtest.exe",
                        "cloudflarest.exe",
                        "cfst.exe",
                    ]:
                        extracted_binary = file_path
                        break

                if not extracted_binary:
                    raise BinaryError("Binary not found in downloaded archive")

                # Copy to final location
                final_path = self.binary_dir / binary_name
                shutil.copy2(extracted_binary, final_path)

                # Make executable on Unix systems
                if os_name != "windows":
                    final_path.chmod(0o755)

                return str(final_path)

        except (requests.RequestException, tarfile.TarError, zipfile.BadZipFile, OSError) as e:
            raise BinaryError(f"Failed to download binary: {e}") from e

    def _get_proxy_config(self, proxy_url: str) -> dict[str, str]:
        """Convert proxy URL to requests-compatible proxy configuration."""
        # requests library expects proxies in format: {'http': 'proxy_url', 'https': 'proxy_url'}
        return {"http": proxy_url, "https": proxy_url}

    def get_binary_version(self) -> str | None:
        """Get version of the currently available binary."""
        if not self.binary_path:
            return None

        try:
            result = subprocess.run(
                [self.binary_path, "-v"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="ignore",
            )
            if result.returncode == 0:
                # Parse version from output
                output = result.stdout.strip()
                # Version output format may vary, try to extract version number
                import re

                version_match = re.search(r"v?(\d+\.\d+\.\d+)", output)
                if version_match:
                    return version_match.group(1)
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def update_binary(self) -> bool:
        """Update binary to latest version if needed."""
        current_version = self.get_binary_version()
        if not current_version:
            # No version info, force update
            try:
                self._download_and_install_binary()
                return True
            except BinaryError:
                return False

        # For now, we'll use a simple version comparison
        # In a real implementation, you might want to check GitHub for latest version
        expected_version = self.BINARY_VERSION.lstrip("v")
        if current_version != expected_version:
            try:
                self._download_and_install_binary()
                return True
            except BinaryError:
                return False

        return False

    def get_system_info(self) -> tuple[str, str]:
        """Get OS and architecture information."""
        os_name = platform.system().lower()
        arch = platform.machine().lower()

        # Normalize OS names
        if os_name == "darwin":
            os_name = "darwin"
        elif os_name == "linux":
            os_name = "linux"
        elif os_name == "windows":
            os_name = "windows"

        # Normalize architecture names
        if arch in ["x86_64", "amd64"]:
            arch = "amd64"
        elif arch in ["i386", "i686"]:
            arch = "386"
        elif arch in ["aarch64", "arm64"]:
            arch = "arm64"
        elif arch.startswith("arm"):
            arch = "armv6l"

        return os_name, arch

    @log_function_call
    @log_performance("Speed Test Execution")
    def run_speed_test(self, ip_file: str, output_file: str = "result.csv") -> str:
        """Run speed test and return results file path."""
        logger.info(f"Starting speed test with IP file: {ip_file}")

        if not self.binary_path:
            logger.debug("Binary path not set, ensuring binary availability")
            self.ensure_binary_available()

        if not os.path.exists(ip_file):
            logger.error(f"IP file not found: {ip_file}")
            raise SpeedTestError(f"IP file not found: {ip_file}")

        # Build command arguments
        cmd_args = [self.binary_path]

        # Add IP file
        cmd_args.extend(["-f", ip_file])

        # Add output file
        cmd_args.extend(["-o", output_file])

        # Add configuration parameters
        if hasattr(self.config, "speed_port") and self.config.speed_port:
            cmd_args.extend(["-tp", str(self.config.speed_port)])
            logger.debug(f"Using custom port: {self.config.speed_port}")

        # Only add URL parameter if explicitly configured
        # When no IP source is specified or no URL is set, let CloudflareSpeedTest use its defaults
        if hasattr(self.config, "speed_url") and self.config.speed_url:
            cmd_args.extend(["-url", self.config.speed_url])
            logger.debug(f"Using test URL: {self.config.speed_url}")
        else:
            logger.debug("No test URL specified, using CloudflareSpeedTest defaults")

        # Add quantity limit if specified
        # if hasattr(self.config, 'quantity') and self.config.quantity > 0:
        #     cmd_args.extend(["-n", str(self.config.quantity)])
        #     logger.debug(f"Limiting results to: {self.config.quantity}")

        # Add speed threshold if specified
        if hasattr(self.config, "speed_threshold") and self.config.speed_threshold > 0:
            cmd_args.extend(["-sl", str(self.config.speed_threshold)])
            logger.debug(f"Speed threshold: {self.config.speed_threshold} MB/s")
            cmd_args.extend(["-tl", "200"])
            logger.debug("Average latency maximum: 200ms")

        # Add extended parameters if specified
        if hasattr(self.config, "extend_string") and self.config.extend_string:
            # Parse the extend string and add individual arguments
            import shlex

            try:
                extend_args = shlex.split(self.config.extend_string)
                cmd_args.extend(extend_args)
                logger.debug(f"Added extended parameters: {extend_args}")
            except ValueError as e:
                logger.warning(f"Failed to parse extend string '{self.config.extend_string}': {e}")
                # Fallback: split by spaces (less robust but still functional)
                extend_args = self.config.extend_string.split()
                cmd_args.extend(extend_args)
                logger.debug(f"Added extended parameters (fallback): {extend_args}")

        logger.debug(f"Speed test command: {' '.join(cmd_args)}")

        try:
            # Run the speed test
            logger.info("Executing CloudflareSpeedTest binary...")
            timeout_seconds = getattr(
                self.config, "timeout", 600
            )  # Default to 10 minutes if not set
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                input="\n",  # Simulate carriage return, no need for stdin=subprocess.PIPE
                encoding="utf-8",
                errors="ignore",
            )

            logger.debug(f"Speed test completed with return code: {result.returncode}")
            if result.stdout:
                logger.debug(f"Speed test stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"Speed test stderr: {result.stderr}")

            if result.returncode != 0:
                error_msg = f"Speed test failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                logger.error(error_msg)
                raise SpeedTestError(error_msg)

            # Verify output file was created
            if not os.path.exists(output_file):
                logger.error(f"Speed test output file not created: {output_file}")
                raise SpeedTestError(f"Speed test output file not created: {output_file}")

            logger.info(f"Speed test completed successfully, results saved to: {output_file}")
            return output_file

        except subprocess.TimeoutExpired:
            timeout_minutes = timeout_seconds // 60
            logger.error(f"Speed test timed out after {timeout_minutes} minutes")
            raise SpeedTestError(f"Speed test timed out after {timeout_minutes} minutes") from None
        except FileNotFoundError:
            logger.error(f"Speed test binary not found: {self.binary_path}")
            raise SpeedTestError(f"Speed test binary not found: {self.binary_path}") from None
        except Exception as e:
            logger.error(f"Speed test execution failed: {e}")
            raise SpeedTestError(f"Speed test execution failed: {e}") from e

    def parse_results(self, results_file: str) -> list[SpeedTestResult]:
        """Parse speed test results from CSV."""
        if not os.path.exists(results_file):
            raise SpeedTestError(f"Results file not found: {results_file}")

        results = []

        try:
            # Try different encodings to handle various system outputs
            encodings_to_try = ["utf-8", "gbk", "cp1252", "latin1"]
            lines = None

            for encoding in encodings_to_try:
                try:
                    with open(results_file, encoding=encoding) as f:
                        lines = f.readlines()
                    break
                except UnicodeDecodeError:
                    continue

            if lines is None:
                # If all encodings fail, try with error handling
                with open(results_file, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

            if len(lines) < 2:
                raise SpeedTestError("Results file is empty or missing header")

            # Skip header line
            for line_num, line in enumerate(lines[1:], start=2):
                line = line.strip()
                if not line:
                    continue

                try:
                    result = self._parse_csv_line(line, line_num)
                    if result:
                        results.append(result)
                except ValueError as e:
                    # Log warning but continue parsing other lines
                    print(f"Warning: Failed to parse line {line_num}: {e}")
                    continue

            if not results:
                raise SpeedTestError("No valid results found in CSV file")

            return results

        except OSError as e:
            raise SpeedTestError(f"Failed to read results file: {e}") from e

    def _parse_csv_line(self, line: str, line_num: int) -> SpeedTestResult | None:
        """Parse a single CSV line into SpeedTestResult."""
        # CSV format can be either:
        # English: IP,Port,DataCenter,Region,City,Speed,Latency
        # Chinese: IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码
        parts = line.split(",")

        if len(parts) < 7:
            raise ValueError(f"Invalid CSV format: expected 7 columns, got {len(parts)}")

        try:
            ip = parts[0].strip()

            # Check if column 2 (index 1) is a small integer (< 100)
            int(parts[1].strip())

            # Check if column 7 (index 6) is a 3-letter region code
            parts[6].strip()

            # format: IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码
            port = 443  # Default port for Chinese format
            data_center = parts[6].strip()  # 地区码
            region = parts[6].strip()  # Use region code as region
            city = parts[6].strip()  # Use region code as city

            # Parse speed (MB/s)
            speed_str = parts[5].strip()
            if speed_str and speed_str != "N/A":
                speed_str = speed_str.replace(",", ".")
                speed = float(speed_str)
            else:
                speed = 0.0

            # Parse latency (ms)
            latency_str = parts[4].strip()
            if latency_str and latency_str != "N/A":
                latency_str = latency_str.replace(",", ".")
                latency = float(latency_str)
            else:
                latency = 0.0

            # Validate IP address format (basic check)
            if not ip or "." not in ip:
                raise ValueError(f"Invalid IP address: {ip}")

            return SpeedTestResult(
                ip=ip,
                port=port,
                data_center=data_center,
                region=region,
                city=city,
                speed=speed,
                latency=latency,
            )

        except (ValueError, IndexError) as e:
            raise ValueError(f"Failed to parse CSV line: {e}") from e

    def validate_results(self, results: list[SpeedTestResult]) -> list[SpeedTestResult]:
        """Validate and filter speed test results."""
        valid_results = []

        for result in results:
            # Basic validation
            if not result.ip:
                continue

            # Speed validation
            if result.speed < 0:
                continue

            # Latency validation
            if result.latency < 0:
                continue

            valid_results.append(result)

        return valid_results

    def filter_results_by_speed(
        self, results: list[SpeedTestResult], min_speed: float
    ) -> list[SpeedTestResult]:
        """Filter results by minimum speed threshold."""
        return [result for result in results if result.speed >= min_speed]

    def sort_results_by_speed(
        self, results: list[SpeedTestResult], reverse: bool = True
    ) -> list[SpeedTestResult]:
        """Sort results by speed (fastest first by default)."""
        return sorted(results, key=lambda x: x.speed, reverse=reverse)

    def get_top_results(self, results: list[SpeedTestResult], count: int) -> list[SpeedTestResult]:
        """Get top N results by speed."""
        sorted_results = self.sort_results_by_speed(results)
        return sorted_results[:count] if count > 0 else sorted_results

    def should_refresh_results(self, results_file: str) -> bool:
        """Check if results need refreshing based on file age."""
        if not os.path.exists(results_file):
            return True

        if self.config.refresh:
            return True

        # Check if file is older than 24 hours
        file_age = os.path.getmtime(results_file)
        import time

        current_time = time.time()
        return (current_time - file_age) > 86400  # 24 hours in seconds
