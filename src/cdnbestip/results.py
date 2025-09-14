"""Results processing and filtering."""

import csv
import os
import time

from .config import Config
from .exceptions import CDNBESTIPError
from .models import SpeedTestResult


class ResultsHandler:
    """Handles speed test result processing and filtering."""

    def __init__(self, config: Config):
        """Initialize results handler with configuration."""
        self.config = config

    def filter_by_speed(
        self, results: list[SpeedTestResult], threshold: float
    ) -> list[SpeedTestResult]:
        """
        Filter results by speed threshold.

        Args:
            results: List of speed test results
            threshold: Minimum speed threshold in MB/s

        Returns:
            List of results that meet or exceed the speed threshold
        """
        return [result for result in results if result.speed >= threshold]

    def filter_by_latency(
        self, results: list[SpeedTestResult], max_latency: float
    ) -> list[SpeedTestResult]:
        """
        Filter results by maximum latency threshold.

        Args:
            results: List of speed test results
            max_latency: Maximum acceptable latency in ms

        Returns:
            List of results with latency below the threshold
        """
        return [result for result in results if result.latency <= max_latency]

    def filter_by_region(
        self, results: list[SpeedTestResult], preferred_regions: list[str]
    ) -> list[SpeedTestResult]:
        """
        Filter results by preferred regions.

        Args:
            results: List of speed test results
            preferred_regions: List of preferred region names

        Returns:
            List of results from preferred regions
        """
        if not preferred_regions:
            return results

        return [
            result
            for result in results
            if result.region.lower() in [r.lower() for r in preferred_regions]
        ]

    def get_top_ips(self, results: list[SpeedTestResult], count: int = 0) -> list[str]:
        """
        Get top N IP addresses based on speed and latency ranking.

        Args:
            results: List of speed test results
            count: Number of top IPs to return (0 = all)

        Returns:
            List of IP addresses sorted by performance
        """
        if not results:
            return []

        # Apply speed threshold filter first
        filtered_results = self.filter_by_speed(results, self.config.speed_threshold)

        if not filtered_results:
            return []

        # Sort by speed (descending) then by latency (ascending)
        sorted_results = sorted(filtered_results, key=lambda x: (-x.speed, x.latency))

        # Apply quantity limit if specified
        if count > 0:
            sorted_results = sorted_results[:count]
        elif self.config.quantity > 0:
            sorted_results = sorted_results[: self.config.quantity]

        return [result.ip for result in sorted_results]

    def get_top_results(
        self, results: list[SpeedTestResult], count: int = 0
    ) -> list[SpeedTestResult]:
        """
        Get top N speed test results based on performance ranking.

        Args:
            results: List of speed test results
            count: Number of top results to return (0 = all that meet threshold)

        Returns:
            List of SpeedTestResult objects sorted by performance
        """
        if not results:
            return []

        # Apply speed threshold filter first
        filtered_results = self.filter_by_speed(results, self.config.speed_threshold)

        if not filtered_results:
            return []

        # Sort by speed (descending) then by latency (ascending)
        sorted_results = sorted(filtered_results, key=lambda x: (-x.speed, x.latency))

        # Apply quantity limit if specified
        if count > 0:
            return sorted_results[:count]
        elif self.config.quantity > 0:
            return sorted_results[: self.config.quantity]

        return sorted_results

    def get_weighted_score(
        self, result: SpeedTestResult, speed_weight: float = 0.7, latency_weight: float = 0.3
    ) -> float:
        """
        Calculate a weighted performance score for a result.

        Args:
            result: Speed test result
            speed_weight: Weight for speed component (0-1)
            latency_weight: Weight for latency component (0-1)

        Returns:
            Weighted performance score (higher is better)
        """
        # Normalize speed (higher is better)
        speed_score = result.speed

        # Normalize latency (lower is better, so invert)
        # Use 1000ms as baseline for normalization
        latency_score = max(0, 1000 - result.latency) / 1000

        return (speed_score * speed_weight) + (latency_score * latency_weight)

    def get_top_ips_weighted(
        self,
        results: list[SpeedTestResult],
        count: int = 0,
        speed_weight: float = 0.7,
        latency_weight: float = 0.3,
    ) -> list[str]:
        """
        Get top N IP addresses using weighted scoring algorithm.

        Args:
            results: List of speed test results
            count: Number of top IPs to return (0 = all)
            speed_weight: Weight for speed component (0-1)
            latency_weight: Weight for latency component (0-1)

        Returns:
            List of IP addresses sorted by weighted performance score
        """
        if not results:
            return []

        # Apply speed threshold filter first
        filtered_results = self.filter_by_speed(results, self.config.speed_threshold)

        if not filtered_results:
            return []

        # Calculate weighted scores and sort
        scored_results = [
            (self.get_weighted_score(result, speed_weight, latency_weight), result)
            for result in filtered_results
        ]
        sorted_results = sorted(scored_results, key=lambda x: -x[0])  # Sort by score descending

        # Apply quantity limit if specified
        if count > 0:
            sorted_results = sorted_results[:count]
        elif self.config.quantity > 0:
            sorted_results = sorted_results[: self.config.quantity]

        return [result.ip for _, result in sorted_results]

    def get_diverse_ips(
        self, results: list[SpeedTestResult], count: int = 0, max_per_datacenter: int = 2
    ) -> list[str]:
        """
        Get diverse IP addresses ensuring geographic distribution.

        Args:
            results: List of speed test results
            count: Number of IPs to return (0 = all)
            max_per_datacenter: Maximum IPs per data center

        Returns:
            List of IP addresses with geographic diversity
        """
        if not results:
            return []

        # Apply speed threshold filter first
        filtered_results = self.filter_by_speed(results, self.config.speed_threshold)

        if not filtered_results:
            return []

        # Sort by performance first
        sorted_results = sorted(filtered_results, key=lambda x: (-x.speed, x.latency))

        # Group by data center and select diverse IPs
        datacenter_counts = {}
        selected_ips = []

        for result in sorted_results:
            dc_key = f"{result.data_center}_{result.region}"
            dc_count = datacenter_counts.get(dc_key, 0)

            if dc_count < max_per_datacenter:
                selected_ips.append(result.ip)
                datacenter_counts[dc_key] = dc_count + 1

                # Stop if we've reached the desired count
                if count > 0 and len(selected_ips) >= count:
                    break
                elif self.config.quantity > 0 and len(selected_ips) >= self.config.quantity:
                    break

        return selected_ips

    def should_update_dns(self, results: list[SpeedTestResult]) -> bool:
        """
        Determine if DNS should be updated based on results.

        Args:
            results: List of speed test results

        Returns:
            True if DNS should be updated, False otherwise
        """
        if not results:
            return False

        # Check if we have at least one result meeting the speed threshold
        filtered_results = self.filter_by_speed(results, self.config.speed_threshold)
        return len(filtered_results) > 0

    def get_best_ip(self, results: list[SpeedTestResult]) -> str:
        """
        Get the single best IP address.

        Args:
            results: List of speed test results

        Returns:
            IP address of the best performing result

        Raises:
            ValueError: If no results available or none meet threshold
        """
        if not results:
            raise ValueError("No results available")

        # Filter by speed threshold first
        filtered_results = self.filter_by_speed(results, self.config.speed_threshold)

        if not filtered_results:
            raise ValueError(
                f"No results meet speed threshold of {self.config.speed_threshold} MB/s"
            )

        # Sort by speed (descending) then by latency (ascending)
        best_result = min(filtered_results, key=lambda x: (-x.speed, x.latency))
        return best_result.ip

    def get_performance_summary(self, results: list[SpeedTestResult]) -> dict:
        """
        Get performance summary statistics for results.

        Args:
            results: List of speed test results

        Returns:
            Dictionary with performance statistics
        """
        if not results:
            return {
                "total_results": 0,
                "results_above_threshold": 0,
                "avg_speed": 0.0,
                "max_speed": 0.0,
                "min_speed": 0.0,
                "avg_latency": 0.0,
                "min_latency": 0.0,
                "max_latency": 0.0,
            }

        filtered_results = self.filter_by_speed(results, self.config.speed_threshold)

        speeds = [r.speed for r in results]
        latencies = [r.latency for r in results]

        return {
            "total_results": len(results),
            "results_above_threshold": len(filtered_results),
            "avg_speed": sum(speeds) / len(speeds),
            "max_speed": max(speeds),
            "min_speed": min(speeds),
            "avg_latency": sum(latencies) / len(latencies),
            "min_latency": min(latencies),
            "max_latency": max(latencies),
        }

    # File management and caching methods

    def should_refresh_results(self, results_file: str, max_age_hours: int = 24) -> bool:
        """
        Check if results file should be refreshed based on age.

        Args:
            results_file: Path to the results file
            max_age_hours: Maximum age in hours before refresh is needed

        Returns:
            True if file should be refreshed, False otherwise
        """
        if not os.path.exists(results_file):
            return True

        # Check file age
        file_age_seconds = time.time() - os.path.getmtime(results_file)
        file_age_hours = file_age_seconds / 3600

        return file_age_hours >= max_age_hours

    def is_results_file_valid(self, results_file: str) -> bool:
        """
        Validate that results file exists and is not corrupted.

        Args:
            results_file: Path to the results file

        Returns:
            True if file is valid, False otherwise
        """
        if not os.path.exists(results_file):
            return False

        try:
            # Check if file is empty
            if os.path.getsize(results_file) == 0:
                return False

            # Try to parse the file
            results = self.load_results_from_file(results_file)
            return len(results) > 0

        except Exception:
            return False

    def load_results_from_file(self, results_file: str) -> list[SpeedTestResult]:
        """
        Load speed test results from CSV file.

        Args:
            results_file: Path to the CSV results file

        Returns:
            List of SpeedTestResult objects

        Raises:
            CDNBESTIPError: If file cannot be read or parsed
        """
        if not os.path.exists(results_file):
            raise CDNBESTIPError(f"Results file not found: {results_file}")

        results = []

        try:
            # Try different encodings to handle various system outputs
            encodings_to_try = ["utf-8", "gbk", "cp1252", "latin1"]
            f = None

            for encoding in encodings_to_try:
                try:
                    f = open(results_file, encoding=encoding)
                    # Test read the first line to verify encoding works
                    pos = f.tell()
                    f.readline()
                    f.seek(pos)
                    break
                except UnicodeDecodeError:
                    if f:
                        f.close()
                    continue

            if f is None:
                # If all encodings fail, try with error handling
                f = open(results_file, encoding="utf-8", errors="ignore")

            try:
                # Skip the header line if it exists
                first_line = f.readline().strip()
                if not first_line:
                    return results

                # Check if first line looks like a header
                if "IP" in first_line or "Speed" in first_line or "Latency" in first_line:
                    # It's a header, continue with CSV reader
                    f.seek(0)
                    reader = csv.DictReader(f)
                else:
                    # No header, reset and use positional parsing
                    f.seek(0)
                    reader = csv.reader(f)

                for row in reader:
                    try:
                        if isinstance(row, dict):
                            # DictReader format - support both English and Chinese headers
                            # Try English headers first
                            ip = row.get("IP", row.get("IP 地址", "")).strip()
                            port = 443  # Default port

                            # For Chinese format, we need to map the fields differently
                            if "IP 地址" in row:
                                # Chinese format: IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码
                                data_center = row.get("地区码", "").strip()
                                region = row.get("地区码", "").strip()  # Use region code as region
                                city = row.get("地区码", "").strip()  # Use region code as city

                                # Handle potential formatting issues in numeric fields
                                speed_str = row.get("下载速度(MB/s)", "0")
                                if isinstance(speed_str, str):
                                    speed_str = speed_str.replace(",", ".")
                                speed = float(speed_str)

                                latency_str = row.get("平均延迟", "0")
                                if isinstance(latency_str, str):
                                    latency_str = latency_str.replace(",", ".")
                                latency = float(latency_str)
                            else:
                                # English format
                                data_center = row.get("Data Center", "").strip()
                                region = row.get("Region", "").strip()
                                city = row.get("City", "").strip()
                                speed = float(row.get("Speed (MB/s)", 0))
                                latency = float(row.get("Latency (ms)", 0))

                            result = SpeedTestResult(
                                ip=ip,
                                port=port,
                                data_center=data_center,
                                region=region,
                                city=city,
                                speed=speed,
                                latency=latency,
                            )
                        else:
                            # CSV reader format (positional)
                            if len(row) >= 6:
                                # Try to detect format by checking column patterns
                                # Chinese format: IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码
                                # English format: IP,Port,Data Center,Region,City,Speed (MB/s),Latency (ms)

                                is_chinese_format = False
                                if len(row) == 7:
                                    # Check if this looks like Chinese format by examining the data pattern
                                    # Chinese format has: IP, sent_count, received_count, loss_rate, latency, speed, region_code
                                    # English format has: IP, port, datacenter, region, city, speed, latency

                                    # Heuristic to detect Chinese format
                                    try:
                                        # Check if first line matches Chinese format pattern
                                        # Chinese format: IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码
                                        # Example: 104.17.110.237,4,4,0.00,31.60,18.75,HKG

                                        # Check if column 2 (index 1) is a small integer (< 100)
                                        col1_val = int(row[1])  # 已发送 or Port

                                        # Check if column 7 (index 6) is a 3-letter region code
                                        col7_val = row[6].strip()  # 地区码 or Latency

                                        # Chinese format typically has:
                                        # 1. Small integers in columns 2-3 (sent/received counts, usually < 100)
                                        # 2. A 3-letter region code in column 7
                                        if (
                                            col1_val < 100
                                            and len(col7_val) == 3
                                            and col7_val.isalpha()
                                        ):
                                            is_chinese_format = True
                                        # English format typically has:
                                        # 1. Port number in column 2 (usually >= 100, often 443)
                                        # 2. Numeric latency in column 7
                                        else:
                                            try:
                                                float(col7_val)  # Should be latency (numeric)
                                                is_chinese_format = False
                                            except ValueError:
                                                # If column 7 is not numeric, it's likely a region code
                                                is_chinese_format = True
                                    except ValueError:
                                        # If parsing fails, try to make a best guess
                                        # Check if column 7 looks like a region code
                                        col7_val = row[6].strip() if len(row) > 6 else ""
                                        if len(col7_val) == 3 and col7_val.isalpha():
                                            is_chinese_format = True
                                        else:
                                            is_chinese_format = False

                                if is_chinese_format:
                                    # Chinese format: IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码
                                    # Handle potential formatting issues in numeric fields
                                    speed_str = row[5].strip() if row[5].strip() else "0"
                                    if isinstance(speed_str, str):
                                        speed_str = speed_str.replace(",", ".")

                                    latency_str = row[4].strip() if row[4].strip() else "0"
                                    if isinstance(latency_str, str):
                                        latency_str = latency_str.replace(",", ".")

                                    result = SpeedTestResult(
                                        ip=row[0].strip(),
                                        port=443,  # Default port for Chinese format
                                        data_center=row[6].strip(),  # 地区码
                                        region=row[6].strip(),  # Use region code as region
                                        city=row[6].strip(),  # Use region code as city
                                        speed=float(speed_str),  # 下载速度(MB/s)
                                        latency=float(latency_str),  # 平均延迟
                                    )
                                else:
                                    # English format: IP,Port,Data Center,Region,City,Speed (MB/s),Latency (ms)
                                    result = SpeedTestResult(
                                        ip=row[0].strip(),
                                        port=int(row[1]) if row[1].strip() else 443,
                                        data_center=row[2].strip(),
                                        region=row[3].strip(),
                                        city=row[4].strip(),
                                        speed=float(row[5]) if row[5].strip() else 0.0,
                                        latency=float(row[6]) if row[6].strip() else 0.0,
                                    )
                            else:
                                continue  # Skip malformed rows

                        # Validate the result
                        if result.ip and result.speed >= 0 and result.latency >= 0:
                            results.append(result)

                    except (ValueError, IndexError):
                        # Skip malformed rows but continue processing
                        continue
            finally:
                if f:
                    f.close()

        except Exception as e:
            raise CDNBESTIPError(f"Failed to read results file {results_file}: {str(e)}") from e

        return results

    def save_results_to_file(self, results: list[SpeedTestResult], results_file: str) -> None:
        """
        Save speed test results to CSV file.

        Args:
            results: List of SpeedTestResult objects to save
            results_file: Path to the CSV file to write

        Raises:
            CDNBESTIPError: If file cannot be written
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(results_file), exist_ok=True)

            with open(results_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow(
                    ["IP", "Port", "Data Center", "Region", "City", "Speed (MB/s)", "Latency (ms)"]
                )

                # Write results
                for result in results:
                    writer.writerow(
                        [
                            result.ip,
                            result.port,
                            result.data_center,
                            result.region,
                            result.city,
                            result.speed,
                            result.latency,
                        ]
                    )

        except Exception as e:
            raise CDNBESTIPError(f"Failed to save results to {results_file}: {str(e)}") from e

    def get_results_file_info(self, results_file: str) -> dict:
        """
        Get information about a results file.

        Args:
            results_file: Path to the results file

        Returns:
            Dictionary with file information
        """
        if not os.path.exists(results_file):
            return {
                "exists": False,
                "size": 0,
                "age_hours": 0,
                "modified_time": None,
                "result_count": 0,
                "is_valid": False,
            }

        stat = os.stat(results_file)
        age_hours = (time.time() - stat.st_mtime) / 3600

        try:
            results = self.load_results_from_file(results_file)
            result_count = len(results)
            is_valid = True
        except Exception:
            result_count = 0
            is_valid = False

        return {
            "exists": True,
            "size": stat.st_size,
            "age_hours": age_hours,
            "modified_time": stat.st_mtime,
            "result_count": result_count,
            "is_valid": is_valid,
        }

    def cleanup_old_results(self, results_dir: str, max_age_days: int = 7) -> int:
        """
        Clean up old result files from the results directory.

        Args:
            results_dir: Directory containing result files
            max_age_days: Maximum age in days before files are deleted

        Returns:
            Number of files deleted
        """
        if not os.path.exists(results_dir):
            return 0

        deleted_count = 0
        max_age_seconds = max_age_days * 24 * 3600
        current_time = time.time()

        try:
            for filename in os.listdir(results_dir):
                if filename.endswith(".csv"):
                    filepath = os.path.join(results_dir, filename)

                    try:
                        file_age = current_time - os.path.getmtime(filepath)
                        if file_age > max_age_seconds:
                            os.remove(filepath)
                            deleted_count += 1
                    except OSError:
                        # Skip files that can't be accessed
                        continue

        except OSError:
            # Directory access error
            pass

        return deleted_count

    def get_cached_results(
        self, cache_key: str, max_age_hours: int = 24, cache_dir: str = "."
    ) -> list[SpeedTestResult] | None:
        """
        Get cached results if they exist and are not too old.

        Args:
            cache_key: Unique key for the cached results
            max_age_hours: Maximum age in hours for cached results
            cache_dir: Directory to store cache files

        Returns:
            List of cached results or None if not available/expired
        """
        cache_file = os.path.join(cache_dir, f"result_{cache_key}.csv")

        if not self.is_results_file_valid(cache_file):
            return None

        if self.should_refresh_results(cache_file, max_age_hours):
            return None

        try:
            return self.load_results_from_file(cache_file)
        except Exception:
            return None

    def cache_results(
        self, results: list[SpeedTestResult], cache_key: str, cache_dir: str = "."
    ) -> bool:
        """
        Cache results for future use.

        Args:
            results: List of results to cache
            cache_key: Unique key for the cached results
            cache_dir: Directory to store cache files

        Returns:
            True if caching succeeded, False otherwise
        """
        try:
            cache_file = os.path.join(cache_dir, f"result_{cache_key}.csv")
            self.save_results_to_file(results, cache_file)
            return True
        except Exception:
            return False

    def force_refresh_results(self, results_file: str) -> bool:
        """
        Force refresh by removing the existing results file.

        Args:
            results_file: Path to the results file to remove

        Returns:
            True if file was removed or didn't exist, False on error
        """
        try:
            if os.path.exists(results_file):
                os.remove(results_file)
            return True
        except OSError:
            return False
