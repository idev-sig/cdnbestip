"""Configuration management for CDNBESTIP."""

import os
import re
import socket
from dataclasses import dataclass

from .exceptions import ConfigurationError


def is_china_network() -> bool:
    """Detect if we're in China by testing google.com accessibility.

    Returns:
        bool: True if unable to access google.com (likely in China), False otherwise
    """
    # Check environment variable first
    cn_env = os.getenv("CN", "").strip()
    if cn_env == "1":
        return True

    try:
        # Try to connect to google.com:80 with a short timeout
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)  # 3 second timeout
        result = sock.connect_ex(("google.com", 80))
        sock.close()

        # If connection successful (result == 0), not in China
        # If connection failed, likely in China
        return result != 0

    except (TimeoutError, socket.gaierror, OSError):
        # DNS resolution failed or other network error
        # Assume we're in China
        return True


@dataclass
class Config:
    """Configuration data model for CDNBESTIP operations."""

    # CloudFlare credentials
    cloudflare_email: str | None = None
    cloudflare_api_key: str | None = None
    cloudflare_api_token: str | None = None

    # DNS settings
    domain: str | None = None
    prefix: str | None = None
    zone_type: str = "A"

    # Speed test settings
    speed_threshold: float = 2.0
    speed_port: int | None = None
    speed_url: str | None = None
    timeout: int = 600  # Speed test timeout in seconds (default: 10 minutes)
    quantity: int = 0

    # Operational settings
    refresh: bool = False
    update_dns: bool = False
    only_one: bool = False
    cdn_url: str = "https://fastfile.asfd.cn/"
    ip_data_url: str | None = None
    extend_string: str | None = None
    proxy_url: str | None = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Skip validation if _skip_validation is set (for testing)
        if not getattr(self, "_skip_validation", False):
            self.validate()

    def validate(self) -> None:
        """Validate all configuration parameters."""
        self._validate_credentials()
        self._validate_dns_settings()
        self._validate_speed_settings()
        self._validate_urls()

    def _validate_credentials(self) -> None:
        """Validate CloudFlare credentials."""
        # Must have either API token OR (API key + email/account_id)
        has_token = bool(self.cloudflare_api_token)
        has_key_email = bool(self.cloudflare_api_key and self.cloudflare_email)

        if self.update_dns and not (has_token or has_key_email):
            raise ConfigurationError(
                "CloudFlare credentials required for DNS operations. "
                "Provide either CLOUDFLARE_API_TOKEN or both CLOUDFLARE_API_KEY and CLOUDFLARE_EMAIL"
            )

        # Validate email format if provided
        if self.cloudflare_email and not self._is_valid_email(self.cloudflare_email):
            raise ConfigurationError(f"Invalid email format: {self.cloudflare_email}")

    def _validate_dns_settings(self) -> None:
        """Validate DNS-related settings."""
        if self.update_dns:
            if not self.domain:
                raise ConfigurationError("Domain is required for DNS operations")

            if not self.prefix:
                raise ConfigurationError("Prefix is required for DNS operations")

            # Validate domain format
            if not self._is_valid_domain(self.domain):
                raise ConfigurationError(f"Invalid domain format: {self.domain}")

        # Validate zone type
        valid_zone_types = ["A", "AAAA", "CNAME", "MX", "TXT", "SRV", "NS", "PTR"]
        if self.zone_type.upper() not in valid_zone_types:
            raise ConfigurationError(
                f"Invalid zone type: {self.zone_type}. Must be one of {valid_zone_types}"
            )

        # Normalize zone type to uppercase
        self.zone_type = self.zone_type.upper()

    def _validate_speed_settings(self) -> None:
        """Validate speed test settings."""
        # Validate speed threshold
        if self.speed_threshold < 0:
            raise ConfigurationError("Speed threshold must be greater than or equal to 0")

        # Validate port range
        if self.speed_port is not None:
            if not (0 <= self.speed_port <= 65535):
                raise ConfigurationError("Speed port must be between 0 and 65535")

        # Validate timeout
        if self.timeout <= 0:
            raise ConfigurationError("Timeout must be greater than 0")

        # Validate quantity
        if self.quantity < 0:
            raise ConfigurationError("Quantity must be greater than or equal to 0")

    def _validate_urls(self) -> None:
        """Validate URL parameters."""
        # Validate speed test URL
        if self.speed_url and not self._is_valid_url(self.speed_url):
            raise ConfigurationError(f"Invalid speed test URL: {self.speed_url}")

        # Validate CDN URL
        if self.cdn_url and not self._is_valid_url(self.cdn_url):
            raise ConfigurationError(f"Invalid CDN URL: {self.cdn_url}")

        # Validate IP data URL (if it's not a predefined source)
        if self.ip_data_url:
            predefined_sources = ["cf", "gc", "aws", "ct"]
            if self.ip_data_url.lower() not in predefined_sources:
                if not self._is_valid_url(self.ip_data_url):
                    raise ConfigurationError(f"Invalid IP data URL: {self.ip_data_url}")

        # Validate proxy URL
        if self.proxy_url and not self._is_valid_proxy_url(self.proxy_url):
            raise ConfigurationError(f"Invalid proxy URL: {self.proxy_url}")

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))



    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain format."""
        # Must contain at least one dot
        if "." not in domain:
            return False

        # Basic domain pattern validation
        pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        return bool(re.match(pattern, domain))

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        pattern = r"^https?://[^\s]+$"
        return bool(re.match(pattern, url))

    def _is_valid_proxy_url(self, proxy_url: str) -> bool:
        """Validate proxy URL format."""
        # Support only http and https proxies
        pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        return bool(re.match(pattern, proxy_url))

    def get_cloudflare_credentials(self) -> tuple[str | None, str | None, str | None]:
        """Get CloudFlare credentials in order: (email, api_key, api_token)."""
        return self.cloudflare_email, self.cloudflare_api_key, self.cloudflare_api_token

    def has_valid_credentials(self) -> bool:
        """Check if valid CloudFlare credentials are available."""
        has_token = bool(self.cloudflare_api_token)
        has_key_email = bool(self.cloudflare_api_key and self.cloudflare_email)
        return has_token or has_key_email

    def requires_dns_update(self) -> bool:
        """Check if DNS update is required and properly configured."""
        return (
            self.update_dns and self.has_valid_credentials() and bool(self.domain and self.prefix)
        )




def load_config_from_env() -> Config:
    """Load configurationnvironment variables."""
    config = Config()
    config._skip_validation = True

    # CloudFlare credentials
    config.cloudflare_email = os.getenv("CLOUDFLARE_EMAIL")
    config.cloudflare_api_key = os.getenv("CLOUDFLARE_API_KEY")
    config.cloudflare_api_token = os.getenv("CLOUDFLARE_API_TOKEN")

    # DNS settings
    config.domain = os.getenv("CDNBESTIP_DOMAIN")
    config.prefix = os.getenv("CDNBESTIP_PREFIX")
    config.zone_type = os.getenv("CDNBESTIP_TYPE", "A")

    # Speed test settings
    speed_env = os.getenv("CDNBESTIP_SPEED")
    if speed_env:
        try:
            config.speed_threshold = float(speed_env)
        except ValueError:
            pass  # Keep default value

    port_env = os.getenv("CDNBESTIP_PORT")
    if port_env:
        try:
            config.speed_port = int(port_env)
        except ValueError:
            pass

    config.speed_url = os.getenv("CDNBESTIP_URL")

    timeout_env = os.getenv("CDNBESTIP_TIMEOUT")
    if timeout_env:
        try:
            config.timeout = int(timeout_env)
        except ValueError:
            pass  # Keep default value

    quantity_env = os.getenv("CDNBESTIP_QUANTITY")
    if quantity_env:
        try:
            config.quantity = int(quantity_env)
        except ValueError:
            pass

    # IP data source
    config.ip_data_url = os.getenv("CDNBESTIP_IPURL")

    # CDN and other settings
    config.cdn_url = os.getenv("CDN", "https://fastfile.asfd.cn/")
    config.extend_string = os.getenv("CDNBESTIP_EXTEND")
    config.proxy_url = os.getenv("CDNBESTIP_PROXY")

    return config


def load_config(args) -> Config:
    """Load configurationnvironment variables and CLI arguments."""
    # Start with environment variables
    env_config = load_config_from_env()

    # Extract CLI arguments and merge with environment config
    cli_overrides = {}

    # CloudFlare credentials
    if hasattr(args, "email") and args.email:
        cli_overrides["cloudflare_email"] = args.email
    if hasattr(args, "key") and args.key:
        cli_overrides["cloudflare_api_key"] = args.key
    if hasattr(args, "token") and args.token:
        cli_overrides["cloudflare_api_token"] = args.token

    # DNS settings
    if hasattr(args, "domain") and args.domain:
        cli_overrides["domain"] = args.domain
    if hasattr(args, "prefix") and args.prefix:
        cli_overrides["prefix"] = args.prefix
    if hasattr(args, "zone_type"):
        cli_overrides["zone_type"] = args.zone_type

    # Speed test settings
    if hasattr(args, "speed") and args.speed is not None:
        cli_overrides["speed_threshold"] = args.speed
    if hasattr(args, "port") and args.port:
        cli_overrides["speed_port"] = args.port
    if hasattr(args, "url") and args.url:
        cli_overrides["speed_url"] = args.url
    if hasattr(args, "timeout") and args.timeout is not None:
        cli_overrides["timeout"] = args.timeout
    if hasattr(args, "quantity") and args.quantity is not None:
        cli_overrides["quantity"] = args.quantity

    # IP data source
    if hasattr(args, "ipurl") and args.ipurl:
        cli_overrides["ip_data_url"] = args.ipurl

    # Operational flags
    if hasattr(args, "refresh") and args.refresh:
        cli_overrides["refresh"] = args.refresh
    if hasattr(args, "dns") and args.dns:
        cli_overrides["update_dns"] = args.dns
    if hasattr(args, "only") and args.only:
        cli_overrides["only_one"] = args.only

    # CDN and extensions
    if hasattr(args, "cdn") and args.cdn:
        cli_overrides["cdn_url"] = args.cdn
    if hasattr(args, "extend") and args.extend:
        cli_overrides["extend_string"] = args.extend
    if hasattr(args, "proxy") and args.proxy:
        cli_overrides["proxy_url"] = args.proxy

    # Merge environment config with CLI overrides
    config = merge_config(env_config, **cli_overrides)

    # Apply IP source-specific test configuration
    _apply_ip_source_test_config(config, args)

    return config


def merge_config(base_config: Config, **overrides) -> Config:
    """Merge configuration with overrides."""
    # Create a new config with base values
    config_dict = {
        "cloudflare_email": overrides.get("cloudflare_email") or base_config.cloudflare_email,
        "cloudflare_api_key": overrides.get("cloudflare_api_key") or base_config.cloudflare_api_key,
        "cloudflare_api_token": overrides.get("cloudflare_api_token")
        or base_config.cloudflare_api_token,
        "domain": overrides.get("domain") or base_config.domain,
        "prefix": overrides.get("prefix") or base_config.prefix,
        "zone_type": overrides.get("zone_type", base_config.zone_type),
        "speed_threshold": overrides.get("speed_threshold", base_config.speed_threshold),
        "speed_port": overrides.get("speed_port") or base_config.speed_port,
        "speed_url": overrides.get("speed_url") or base_config.speed_url,
        "timeout": overrides.get("timeout", base_config.timeout),
        "quantity": overrides.get("quantity", base_config.quantity),
        "refresh": overrides.get("refresh", base_config.refresh),
        "update_dns": overrides.get("update_dns", base_config.update_dns),
        "only_one": overrides.get("only_one", base_config.only_one),
        "cdn_url": overrides.get("cdn_url") or base_config.cdn_url,
        "ip_data_url": overrides.get("ip_data_url") or base_config.ip_data_url,
        "extend_string": overrides.get("extend_string") or base_config.extend_string,
        "proxy_url": overrides.get("proxy_url") or base_config.proxy_url,
    }

    return Config(**config_dict)


def load_config_from_args(args) -> Config:
    """Load configuration from command line arguments."""
    # Convert argparse Namespace to dict, handling None values
    args_dict = vars(args)

    # Create config without validation since we'll merge with env later
    config = Config()
    config._skip_validation = True
    config.cloudflare_email = args_dict.get("email")
    config.cloudflare_api_key = args_dict.get("key")
    config.cloudflare_api_token = args_dict.get("token")
    config.domain = args_dict.get("domain")
    config.prefix = args_dict.get("prefix")
    config.zone_type = args_dict.get("zone_type", "A")
    config.speed_threshold = args_dict.get("speed", 2.0)
    config.speed_port = args_dict.get("port")
    config.speed_url = args_dict.get("url")
    config.timeout = args_dict.get("timeout", 600)
    config.quantity = args_dict.get("quantity", 0)
    config.refresh = args_dict.get("refresh", False)
    config.update_dns = args_dict.get("dns", False)
    config.only_one = args_dict.get("only", False)
    config.cdn_url = args_dict.get("cdn", "https://fastfile.asfd.cn/")
    config.ip_data_url = args_dict.get("ipurl")
    config.extend_string = args_dict.get("extend")
    config.proxy_url = args_dict.get("proxy")
    return config


def _apply_ip_source_test_config(config: Config, args) -> None:
    """Apply IP source-specific test configuration based on the correct logic."""
    if not config.ip_data_url:
        return  # No IP source specified, don't set test URL

    # Check if user explicitly set test URL via CLI
    user_set_url = hasattr(args, "url") and args.url is not None

    # Import here to avoid circular imports
    from .exceptions import ConfigurationError
    from .ip_sources import IPSourceManager

    try:
        ip_manager = IPSourceManager(config)
        ip_source = config.ip_data_url.lower()

        # Check if this IP source requires custom URL
        if ip_manager.requires_custom_url(ip_source):
            if not user_set_url:
                raise ConfigurationError(
                    f"IP source '{ip_source}' requires a custom test URL",
                    field="url",
                    suggestion=f"Use -u/--url option to specify test URL for {ip_source.upper()} (e.g., -u https://example.com/test)",
                )
            # For sources that require custom URL, don't set default
            return

        # For cf and gc, set default URL if user didn't specify one
        if not user_set_url:
            default_url = ip_manager.get_default_test_url(ip_source)
            # Set default URL even if it's empty string (for cf)
            if default_url is not None:
                config.speed_url = default_url
                if default_url:  # Only print message if URL is not empty
                    print(
                        f"  🔧 Using default test URL for {ip_source.upper()}: {config.speed_url}"
                    )

    except Exception as e:
        # Re-raise configuration errors
        if isinstance(e, ConfigurationError):
            raise
        # For other errors, continue with defaults
        pass
