"""IP data source management for downloading IP lists from various CDN providers."""

import json
from pathlib import Path
from typing import Any

import requests

from .config import Config
from .exceptions import IPSourceError


class IPSourceManager:
    """Manages IP list downloads from various CDN providers."""

    # Predefined IP data sources with their default test endpoints
    IP_SOURCES = {
        "cf": {
            "name": "CloudFlare",
            "url": "https://www.cloudflare.com/ips-v4",
            "type": "text",
            "description": "CloudFlare IPv4 ranges",
            "default_test_url": "",  # CloudFlare default test endpoint
        },
        "gc": {
            "name": "GCore",
            "url": "https://api.gcore.com/cdn/public-ip-list",
            "type": "json",
            "json_path": "addresses",
            "description": "GCore CDN IP addresses",
            "default_test_url": "https://hk2-speedtest.tools.gcore.com/speedtest-backend/garbage.php?ckSize=100",  # GCore default test endpoint
        },
        "ct": {
            "name": "CloudFront",
            "url": "https://d7uri8nf7uskq.cloudfront.net/tools/list-cloudfront-ips",
            "type": "json",
            "json_path": "CLOUDFRONT_GLOBAL_IP_LIST",
            "description": "AWS CloudFront IP ranges",
            "requires_custom_url": True,  # Requires -u parameter
        },
        "aws": {
            "name": "Amazon Web Services",
            "url": "https://ip-ranges.amazonaws.com/ip-ranges.json",
            "type": "json",
            "json_path": "prefixes",
            "json_field": "ip_prefix",
            "description": "AWS IP ranges",
            "requires_custom_url": True,  # Requires -u parameter
        },
    }

    def __init__(self, config: Config):
        """Initialize IP source manager with configuration."""
        self.config = config
        self.cache_dir = Path.home() / ".cdnbestip" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_available_sources(self) -> list[str]:
        """Get list of available IP sources."""
        return list(self.IP_SOURCES.keys())

    def get_source_info(self, source: str) -> dict[str, Any]:
        """Get information about a specific IP source."""
        if source not in self.IP_SOURCES:
            raise IPSourceError(f"Unknown IP source: {source}")
        return self.IP_SOURCES[source].copy()

    def get_default_test_url(self, source: str) -> str | None:
        """Get default test URL for a specific IP source."""
        if source not in self.IP_SOURCES:
            return None

        source_info = self.IP_SOURCES[source]
        return source_info.get("default_test_url")

    def requires_custom_url(self, source: str) -> bool:
        """Check if IP source requires custom URL (-u parameter)."""
        if source not in self.IP_SOURCES:
            return True  # Unknown sources require custom URL

        source_info = self.IP_SOURCES[source]
        return source_info.get("requires_custom_url", False)

    def download_ip_list(self, source: str, output_file: str, force_refresh: bool = False) -> None:
        """Download IP list from specified source and save to file."""
        if source in self.IP_SOURCES:
            # Use predefined source
            source_info = self.IP_SOURCES[source]
            url = source_info["url"]

            # Apply CDN URL if configured and not using proxy
            # When using proxy, access original URL directly
            if (
                hasattr(self.config, "cdn_url")
                and self.config.cdn_url
                and not (hasattr(self.config, "proxy_url") and self.config.proxy_url)
            ):
                url = self._apply_cdn_url(url)

            self._download_from_source(source_info, url, output_file, force_refresh)
        else:
            # Treat as custom URL
            if not source.startswith(("http://", "https://")):
                raise IPSourceError(f"Invalid URL or unknown source: {source}")

            # Apply CDN URL if configured and not using proxy
            # When using proxy, access original URL directly
            url = source
            if (
                hasattr(self.config, "cdn_url")
                and self.config.cdn_url
                and not (hasattr(self.config, "proxy_url") and self.config.proxy_url)
            ):
                url = self._apply_cdn_url(url)

            # Assume text format for custom URLs
            source_info = {"type": "text", "name": "Custom"}
            self._download_from_source(source_info, url, output_file, force_refresh)

    def _apply_cdn_url(self, url: str) -> str:
        """Apply CDN URL prefix if configured."""
        if not hasattr(self.config, "cdn_url") or not self.config.cdn_url:
            return url

        cdn_url = self.config.cdn_url.rstrip("/")

        # Check if CDN URL ends with '/' - different handling for different CDN types
        if self.config.cdn_url.endswith("/"):
            # Format: https://cdn.example.com/https://original-url.com
            return f"{cdn_url}/{url}"
        else:
            # Format: https://cdn.example.com/original-url.com (remove https://)
            if url.startswith("https://"):
                return f"{cdn_url}/{url[8:]}"  # Remove 'https://'
            elif url.startswith("http://"):
                return f"{cdn_url}/{url[7:]}"  # Remove 'http://'
            else:
                return f"{cdn_url}/{url}"

    def _download_from_source(
        self, source_info: dict[str, Any], url: str, output_file: str, force_refresh: bool = False
    ) -> None:
        """Download and process IP list from a source."""
        try:
            # Check cache first
            cache_file = self._get_cache_file(url)
            if not force_refresh and cache_file.exists() and self._is_cache_valid(cache_file):
                self._copy_from_cache(cache_file, output_file)
                return

            # Prepare request parameters
            request_kwargs = {"timeout": 30}

            # Add proxy configuration if available
            if hasattr(self.config, "proxy_url") and self.config.proxy_url:
                proxies = self._get_proxy_config(self.config.proxy_url)
                request_kwargs["proxies"] = proxies

            # Download from source
            response = requests.get(url, **request_kwargs)
            response.raise_for_status()

            # Process based on source type
            if source_info["type"] == "text":
                ip_list = self._process_text_response(response.text)
            elif source_info["type"] == "json":
                ip_list = self._process_json_response(response.json(), source_info)
            else:
                raise IPSourceError(f"Unsupported source type: {source_info['type']}")

            # Save to output file
            self._save_ip_list(ip_list, output_file)

            # Cache the result
            self._save_to_cache(ip_list, cache_file)

        except requests.RequestException as e:
            raise IPSourceError(f"Failed to download from {url}: {e}") from e
        except (json.JSONDecodeError, KeyError) as e:
            raise IPSourceError(f"Failed to parse response from {url}: {e}") from e

    def _process_text_response(self, text: str) -> list[str]:
        """Process plain text response containing IP addresses/ranges."""
        lines = text.strip().split("\n")
        ip_list = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):  # Skip empty lines and comments
                ip_list.append(line)

        return ip_list

    def _process_json_response(
        self, data: dict[str, Any], source_info: dict[str, Any]
    ) -> list[str]:
        """Process JSON response to extract IP addresses."""
        json_path = source_info.get("json_path")
        json_field = source_info.get("json_field")

        if not json_path:
            raise IPSourceError("JSON path not specified for JSON source")

        # Navigate to the data using json_path
        current_data = data
        for path_part in json_path.split("."):
            if path_part in current_data:
                current_data = current_data[path_part]
            else:
                raise IPSourceError(f"JSON path '{json_path}' not found in response")

        # Extract IP addresses
        if isinstance(current_data, list):
            if json_field:
                # Extract specific fieldach object
                ip_list = []
                for item in current_data:
                    if isinstance(item, dict) and json_field in item:
                        ip_list.append(item[json_field])
                return ip_list
            else:
                # Use items directly (should be strings)
                return [str(item) for item in current_data]
        else:
            raise IPSourceError(
                f"Expected list at JSON path '{json_path}', got {type(current_data)}"
            )

    def _save_ip_list(self, ip_list: list[str], output_file: str) -> None:
        """Save IP list to output file."""
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                for ip in ip_list:
                    f.write(f"{ip}\n")
        except OSError as e:
            raise IPSourceError(f"Failed to save IP list to {output_file}: {e}") from e

    def _get_cache_file(self, url: str) -> Path:
        """Get cache file path for a URL."""
        # Create a safe filename from URL
        import hashlib

        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"ip_list_{url_hash}.txt"

    def _is_cache_valid(self, cache_file: Path, max_age_hours: int = 24) -> bool:
        """Check if cache file is still valid."""
        if not cache_file.exists():
            return False

        import time

        file_age = time.time() - cache_file.stat().st_mtime
        max_age_seconds = max_age_hours * 3600

        return file_age < max_age_seconds

    def _copy_from_cache(self, cache_file: Path, output_file: str) -> None:
        """Copy IP list from cache to output file."""
        try:
            import shutil

            shutil.copy2(cache_file, output_file)
        except OSError as e:
            raise IPSourceError(f"Failed to copy from cache: {e}") from e

    def _save_to_cache(self, ip_list: list[str], cache_file: Path) -> None:
        """Save IP list to cache file."""
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                for ip in ip_list:
                    f.write(f"{ip}\n")
        except OSError:
            # Cache failure shouldn't be fatal
            pass

    def clear_cache(self) -> None:
        """Clear all cached IP lists."""
        try:
            import shutil

            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Cache clearing failure shouldn't be fatal
            pass

    def _get_proxy_config(self, proxy_url: str) -> dict[str, str]:
        """Convert proxy URL to requests-compatible proxy configuration."""
        # requests library expects proxies in format: {'http': 'proxy_url', 'https': 'proxy_url'}
        return {"http": proxy_url, "https": proxy_url}

    def get_cache_info(self) -> dict[str, Any]:
        """Get information about cached files."""
        cache_info = {"cache_dir": str(self.cache_dir), "files": []}

        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("ip_list_*.txt"):
                try:
                    stat = cache_file.stat()
                    cache_info["files"].append(
                        {
                            "file": cache_file.name,
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                            "valid": self._is_cache_valid(cache_file),
                        }
                    )
                except OSError:
                    continue

        return cache_info
