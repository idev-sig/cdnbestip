"""CloudFlare DNS speed testing and management tool."""

from .cli import main
from .config import Config
from .exceptions import (
    AuthenticationError,
    BinaryError,
    CDNBESTIPError,
    ConfigurationError,
    DNSError,
    IPSourceError,
    SpeedTestError,
)
from .models import DNSRecord, SpeedTestResult

__version__ = "1.0.0"
__all__ = [
    "main",
    "Config",
    "SpeedTestResult",
    "DNSRecord",
    "CDNBESTIPError",
    "ConfigurationError",
    "SpeedTestError",
    "DNSError",
    "AuthenticationError",
    "BinaryError",
    "IPSourceError",
]


if __name__ == "__main__":
    main()
