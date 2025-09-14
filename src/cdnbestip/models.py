"""Data models for CDNBESTIP operations."""

from dataclasses import dataclass


@dataclass
class SpeedTestResult:
    """Speed test result data model."""

    ip: str
    port: int
    data_center: str
    region: str
    city: str
    speed: float  # MB/s
    latency: float  # ms


@dataclass
class DNSRecord:
    """DNS record data model."""

    id: str | None = None
    zone_id: str | None = None
    zone_name: str | None = None
    name: str = ""
    content: str = ""
    type: str = "A"
    ttl: int = 1
    proxied: bool = False
