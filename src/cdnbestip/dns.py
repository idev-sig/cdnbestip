"""DNS management using CloudFlare API."""

from typing import Any

import cloudflare
import httpx
from cloudflare import Cloudflare, DefaultHttpxClient

from .config import Config
from .exceptions import AuthenticationError, DNSError
from .logging_config import get_logger, log_function_call, log_performance
from .models import DNSRecord

logger = get_logger(__name__)


class DNSManager:
    """Manages CloudFlare DNS operations using the official Python library."""

    def __init__(self, config: Config):
        """Initialize DNS manager with configuration."""
        self.config = config
        self.client = None

    @log_function_call
    @log_performance("CloudFlare Authentication")
    def authenticate(self) -> None:
        """
        Authenticate with CloudFlare API.

        Supports both API token and API key/email authentication methods.

        Raises:
            AuthenticationError: If authentication fails or credentials are invalid
            ConfigurationError: If required credentials are missing
        """
        logger.info("Starting CloudFlare API authentication")

        if not self.config.has_valid_credentials():
            logger.error("No valid CloudFlare credentials found")
            raise AuthenticationError(
                "No valid CloudFlare credentials found. "
                "Provide either CLOUDFLARE_API_TOKEN or both CLOUDFLARE_API_KEY and cloudflare_email"
            )

        try:
            # Prepare client configuration
            client_kwargs = {}

            # Add proxy configuration if available
            if hasattr(self.config, "proxy_url") and self.config.proxy_url:
                logger.debug(f"Configuring proxy: {self.config.proxy_url}")
                # 直接使用代理URL字符串
                http_client = DefaultHttpxClient(
                    proxy=self.config.proxy_url,  # 直接传递字符串
                    transport=httpx.HTTPTransport(local_address="0.0.0.0"),
                )
                client_kwargs["http_client"] = http_client

            # Prefer API token authentication (more secure)
            if self.config.cloudflare_api_token:
                logger.debug("Authenticating with API token")
                client = Cloudflare(api_token=self.config.cloudflare_api_token, **client_kwargs)
            elif self.config.cloudflare_api_key and self.config.cloudflare_email:
                logger.debug("Authenticating with API key and email")
                client = Cloudflare(
                    api_key=self.config.cloudflare_api_key,
                    api_email=self.config.cloudflare_email,
                    **client_kwargs,
                )
            else:
                raise AuthenticationError("Invalid credential combination")

            # Validate credentials by making a test API call
            self._validate_credentials_with_client(client)

            # Only set the client if validation succeeds
            self.client = client
            logger.info("Successfully authenticated with CloudFlare API")

        except cloudflare.APIConnectionError as e:
            self.client = None
            raise AuthenticationError(f"Failed to connect to CloudFlare API: {e}") from e
        except cloudflare.AuthenticationError as e:
            self.client = None
            raise AuthenticationError(f"CloudFlare authentication failed: {e}") from e
        except AuthenticationError:
            self.client = None
            raise
        except Exception as e:
            self.client = None
            raise AuthenticationError(f"Unexpected authentication error: {e}") from e

    def _validate_credentials(self) -> None:
        """
        Validate credentials by making a test API call.

        Raises:
            AuthenticationError: If credentials are invalid
        """
        if not self.client:
            raise AuthenticationError("Client not initialized")

        self._validate_credentials_with_client(self.client)

    def _validate_credentials_with_client(self, client: Cloudflare) -> None:
        """
        Validate credentials with a specific client by making a test API call.

        Args:
            client: CloudFlare client to validate

        Raises:
            AuthenticationError: If credentials are invalid
        """
        try:
            # Make a simple API call to validate credentials
            # Using user.get() for token auth or zones.list() for key auth
            if self.config.cloudflare_api_token:
                # For token auth, verify token validity
                user_info = client.user.get()
                logger.debug(f"Authenticated as user: {user_info.email}")
            else:
                # For key auth, try to list zones (minimal permission required)
                zones = client.zones.list(per_page=1)
                logger.debug(f"Credential validation successful, found {len(zones.result)} zones")

        except cloudflare.AuthenticationError as e:
            raise AuthenticationError(f"Invalid credentials: {e}") from e
        except cloudflare.PermissionDeniedError as e:
            raise AuthenticationError(f"Insufficient permissions: {e}") from e
        except Exception as e:
            raise AuthenticationError(f"Credential validation failed: {e}") from e

    def is_authenticated(self) -> bool:
        """
        Check if client is authenticated.

        Returns:
            bool: True if client is initialized and authenticated
        """
        return self.client is not None

    @log_function_call
    @log_performance("Batch DNS Record Upsert")
    def batch_upsert_records(
        self,
        zone_id: str,
        base_name: str,
        ip_addresses: list[str],
        record_type: str = "A",
        proxied: bool = False,
        ttl: int = 1,
    ) -> list[DNSRecord]:
        """
        Batch upsert DNS records with prefix support (cf1, cf2, etc.).

        Creates or updates multiple DNS records with sequential prefixes.
        For example, with base_name="cf" and 3 IPs, creates:
        - cf1.example.com -> IP1
        - cf2.example.com -> IP2
        - cf3.example.com -> IP3

        Args:
            zone_id: Zone ID to create/update records in
            base_name: Base name for records (e.g., "cf")
            ip_addresses: List of IP addresses to assign
            record_type: Record type (A, AAAA, etc.)
            proxied: Whether records should be proxied through CloudFlare
            ttl: Time to live (1 for automatic)

        Returns:
            List[DNSRecord]: List of created/updated DNS records

        Raises:
            DNSError: If batch operation fails
            AuthenticationError: If not authenticated
        """
        logger.info(
            f"Starting batch upsert for {len(ip_addresses)} records with base name '{base_name}'"
        )
        logger.debug(
            f"Zone ID: {zone_id}, Record type: {record_type}, Proxied: {proxied}, TTL: {ttl}"
        )

        if not self.is_authenticated():
            logger.error("Not authenticated with CloudFlare API")
            raise AuthenticationError("Not authenticated with CloudFlare API")

        if not ip_addresses:
            logger.warning("No IP addresses provided for batch upsert")
            return []

        try:
            # Get zone name for constructing full record names
            zone_info = self.client.zones.get(zone_id=zone_id)
            zone_name = zone_info.name

            created_records = []

            for i, ip_address in enumerate(ip_addresses, 1):
                # Construct record name with prefix (cf1, cf2, etc.)
                record_name = f"{base_name}{i}.{zone_name}"

                logger.debug(f"Upserting record {record_name} -> {ip_address}")

                try:
                    record = self.upsert_record(
                        zone_id=zone_id,
                        name=record_name,
                        content=ip_address,
                        record_type=record_type,
                        proxied=proxied,
                        ttl=ttl,
                    )
                    created_records.append(record)

                except Exception as e:
                    logger.error(f"Failed to upsert record {record_name}: {e}")
                    # Continue with other records even if one fails
                    continue

            logger.info(
                f"Batch upsert completed: {len(created_records)}/{len(ip_addresses)} records processed"
            )
            return created_records

        except Exception as e:
            raise DNSError(f"Batch upsert operation failed: {e}") from e

    def batch_delete_records_by_prefix(self, zone_id: str, prefix: str) -> int:
        """
        Delete all DNS records matching a prefix pattern.

        Deletes records like cf1.example.com, cf2.example.com, etc.

        Args:
            zone_id: Zone ID to delete records from
            prefix: Prefix pattern to match (e.g., "cf")

        Returns:
            int: Number of records deleted

        Raises:
            DNSError: If batch deletion fails
            AuthenticationError: If not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("Not authenticated with CloudFlare API")

        try:
            # Get matching records using the prefix filter
            matching_records = self.list_records_by_prefix(zone_id, prefix)

            # Delete matching records
            deleted_count = 0
            for record in matching_records:
                try:
                    success = self.delete_record(zone_id, record.id)
                    if success:
                        deleted_count += 1
                        logger.debug(f"Deleted record {record.name}")
                except Exception as e:
                    logger.error(f"Failed to delete record {record.name}: {e}")
                    continue

            logger.info(f"Batch delete completed: {deleted_count} records deleted")
            return deleted_count

        except Exception as e:
            raise DNSError(f"Batch delete operation failed: {e}") from e

    def list_records_by_prefix(self, zone_id: str, prefix: str) -> list[DNSRecord]:
        """
        List DNS records matching a prefix pattern.

        Args:
            zone_id: Zone ID to search in
            prefix: Prefix pattern to match (e.g., "cf")

        Returns:
            List[DNSRecord]: List of matching DNS records

        Raises:
            DNSError: If listing fails
            AuthenticationError: If not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("Not authenticated with CloudFlare API")

        try:
            # Get zone name for pattern matching
            zone_info = self.client.zones.get(zone_id=zone_id)
            zone_name = zone_info.name

            # List all records in the zone
            all_records = self.list_records(zone_id)

            # Filter records matching the prefix pattern
            matching_records = []
            prefix_pattern = f"{prefix}\\d+\\.{zone_name.replace('.', '\\.')}"

            import re

            pattern = re.compile(prefix_pattern)

            for record in all_records:
                if pattern.match(record.name):
                    matching_records.append(record)

            logger.debug(f"Found {len(matching_records)} records matching prefix '{prefix}'")
            return matching_records

        except Exception as e:
            raise DNSError(f"Failed to list records by prefix: {e}") from e

    def update_batch_records(
        self,
        zone_id: str,
        prefix: str,
        ip_addresses: list[str],
        record_type: str = "A",
        proxied: bool = False,
        ttl: int = 1,
    ) -> list[DNSRecord]:
        """
        Update existing batch records or create new ones as needed.

        This method intelligently manages batch records:
        1. If there are more IPs than existing records, creates new ones
        2. If there are fewer IPs than existing records, deletes excess ones
        3. Updates existing records with new IP addresses

        Args:
            zone_id: Zone ID to update records in
            prefix: Prefix for records (e.g., "cf")
            ip_addresses: List of IP addresses to assign
            record_type: Record type (A, AAAA, etc.)
            proxied: Whether records should be proxied
            ttl: Time to live

        Returns:
            List[DNSRecord]: List of updated/created records

        Raises:
            DNSError: If batch update fails
            AuthenticationError: If not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("Not authenticated with CloudFlare API")

        try:
            # Get existing records with the prefix
            existing_records = self.list_records_by_prefix(zone_id, prefix)

            # Sort existing records by name to ensure consistent ordering
            existing_records.sort(key=lambda r: r.name)

            updated_records = []

            # Update/create records for each IP
            for i, ip_address in enumerate(ip_addresses):
                if i < len(existing_records):
                    # Update existing record
                    existing_record = existing_records[i]
                    logger.debug(f"Updating existing record {existing_record.name} -> {ip_address}")

                    updated_record = self.update_record(
                        zone_id=zone_id,
                        record_id=existing_record.id,
                        content=ip_address,
                        proxied=proxied,
                        ttl=ttl,
                    )
                    updated_records.append(updated_record)
                else:
                    # Create new record
                    zone_info = self.client.zones.get(zone_id=zone_id)
                    zone_name = zone_info.name
                    record_name = f"{prefix}{i + 1}.{zone_name}"

                    logger.debug(f"Creating new record {record_name} -> {ip_address}")

                    new_record = self.create_record(
                        zone_id=zone_id,
                        name=record_name,
                        content=ip_address,
                        record_type=record_type,
                        proxied=proxied,
                        ttl=ttl,
                    )
                    updated_records.append(new_record)

            # Delete excess records if we have fewer IPs than existing records
            if len(existing_records) > len(ip_addresses):
                excess_records = existing_records[len(ip_addresses) :]
                for record in excess_records:
                    logger.debug(f"Deleting excess record {record.name}")
                    try:
                        self.delete_record(zone_id, record.id)
                    except Exception as e:
                        logger.error(f"Failed to delete excess record {record.name}: {e}")

            logger.info(f"Batch update completed: {len(updated_records)} records processed")
            return updated_records

        except Exception as e:
            raise DNSError(f"Batch update operation failed: {e}") from e

    def get_zone_id(self, domain: str) -> str:
        """
        Get zone ID for domain.

        Args:
            domain: Domain name to find zone for

        Returns:
            str: Zone ID for the domain

        Raises:
            DNSError: If zone is not found or API call fails
            AuthenticationError: If not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("Not authenticated with CloudFlare API")

        try:
            # List zones and find matching domain
            zones = self.client.zones.list(name=domain)

            if not zones.result:
                raise DNSError(f"Zone not found for domain: {domain}")

            # Return the first matching zone ID
            zone = zones.result[0]
            logger.debug(f"Found zone ID {zone.id} for domain {domain}")
            return zone.id

        except cloudflare.APIError as e:
            raise DNSError(f"Failed to get zone ID for {domain}: {e}") from e
        except Exception as e:
            raise DNSError(f"Unexpected error getting zone ID for {domain}: {e}") from e

    def list_zones(self) -> list[dict[str, Any]]:
        """
        List available zones.

        Returns:
            List[Dict[str, Any]]: List of zone information

        Raises:
            DNSError: If API call fails
            AuthenticationError: If not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("Not authenticated with CloudFlare API")

        try:
            zones = self.client.zones.list()

            # Convert zone objects to dictionaries
            zone_list = []
            for zone in zones.result:
                zone_dict = {
                    "id": zone.id,
                    "name": zone.name,
                    "status": zone.status,
                    "paused": zone.paused,
                    "type": zone.type,
                    "development_mode": zone.development_mode,
                }
                zone_list.append(zone_dict)

            logger.debug(f"Listed {len(zone_list)} zones")
            return zone_list

        except cloudflare.APIError as e:
            raise DNSError(f"Failed to list zones: {e}") from e
        except Exception as e:
            raise DNSError(f"Unexpected error listing zones: {e}") from e

    def list_records(
        self, zone_id: str, record_type: str | None = None, name: str | None = None
    ) -> list[DNSRecord]:
        """
        List DNS records for a zone.

        Args:
            zone_id: Zone ID to list records for
            record_type: Optional record type filter (A, AAAA, CNAME, etc.)
            name: Optional record name filter

        Returns:
            List[DNSRecord]: List of DNS records

        Raises:
            DNSError: If API call fails
            AuthenticationError: If not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("Not authenticated with CloudFlare API")

        try:
            # Build query parameters
            params = {}
            if record_type:
                params["type"] = record_type.upper()
            if name:
                params["name"] = name

            # List records with optional filters
            records = self.client.dns.records.list(zone_id=zone_id, **params)

            # Convert to DNSRecord objects
            dns_records = []
            for record in records.result:
                dns_record = DNSRecord(
                    id=getattr(record, "id", None),
                    zone_id=getattr(record, "zone_id", zone_id),
                    zone_name=getattr(record, "zone_name", None),
                    name=getattr(record, "name", ""),
                    content=getattr(record, "content", ""),
                    type=getattr(record, "type", "A"),
                    ttl=getattr(record, "ttl", 1),
                    proxied=getattr(record, "proxied", False),
                )
                dns_records.append(dns_record)

            logger.debug(f"Listed {len(dns_records)} records for zone {zone_id}")
            return dns_records

        except cloudflare.APIError as e:
            raise DNSError(f"Failed to list records for zone {zone_id}: {e}") from e
        except Exception as e:
            raise DNSError(f"Unexpected error listing records for zone {zone_id}: {e}") from e

    def create_record(
        self,
        zone_id: str,
        name: str,
        content: str,
        record_type: str = "A",
        proxied: bool = False,
        ttl: int = 1,
    ) -> DNSRecord:
        """
        Create new DNS record.

        Args:
            zone_id: Zone ID to create record in
            name: Record name
            content: Record content (IP address, CNAME target, etc.)
            record_type: Record type (A, AAAA, CNAME, etc.)
            proxied: Whether record should be proxied through CloudFlare
            ttl: Time to live (1 for automatic)

        Returns:
            DNSRecord: Created DNS record

        Raises:
            DNSError: If record creation fails
            AuthenticationError: If not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("Not authenticated with CloudFlare API")

        try:
            # Prepare record data
            record_data = {
                "name": name,
                "content": content,
                "type": record_type.upper(),
                "ttl": ttl,
            }

            # Add proxied setting for supported record types
            if record_type.upper() in ["A", "AAAA", "CNAME"]:
                record_data["proxied"] = proxied

            # Create the record
            result = self.client.dns.records.create(zone_id=zone_id, **record_data)

            # Convert to DNSRecord object
            dns_record = DNSRecord(
                id=getattr(result, "id", None),
                zone_id=getattr(result, "zone_id", zone_id),
                zone_name=getattr(result, "zone_name", None),
                name=getattr(result, "name", name),
                content=getattr(result, "content", content),
                type=getattr(result, "type", record_type),
                ttl=getattr(result, "ttl", ttl),
                proxied=getattr(result, "proxied", False),
            )

            logger.info(f"Created DNS record: {name} ({record_type}) -> {content}")
            return dns_record

        except cloudflare.APIError as e:
            raise DNSError(f"Failed to create DNS record {name}: {e}") from e
        except Exception as e:
            raise DNSError(f"Unexpected error creating DNS record {name}: {e}") from e

    def update_record(
        self,
        zone_id: str,
        record_id: str,
        content: str,
        name: str | None = None,
        record_type: str | None = None,
        proxied: bool | None = None,
        ttl: int | None = None,
    ) -> DNSRecord:
        """
        Update existing DNS record.

        Args:
            zone_id: Zone ID containing the record
            record_id: Record ID to update
            content: New record content
            name: Optional new record name
            record_type: Optional new record type
            proxied: Optional new proxied setting
            ttl: Optional new TTL

        Returns:
            DNSRecord: Updated DNS record

        Raises:
            DNSError: If record update fails
            AuthenticationError: If not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("Not authenticated with CloudFlare API")

        try:
            # Get current record to preserve existing values
            current_record = self.client.dns.records.get(dns_record_id=record_id, zone_id=zone_id)

            # Prepare update data with current values as defaults
            update_data = {
                "name": name or current_record.name,
                "content": content,
                "type": (record_type or current_record.type).upper(),
                "ttl": ttl or current_record.ttl,
            }

            # Handle proxied setting for supported record types
            if update_data["type"] in ["A", "AAAA", "CNAME"]:
                if proxied is not None:
                    update_data["proxied"] = proxied
                else:
                    update_data["proxied"] = getattr(current_record, "proxied", False)

            # Update the record
            result = self.client.dns.records.update(
                dns_record_id=record_id, zone_id=zone_id, **update_data
            )

            # Convert to DNSRecord object
            dns_record = DNSRecord(
                id=getattr(result, "id", record_id),
                zone_id=getattr(result, "zone_id", zone_id),
                zone_name=getattr(result, "zone_name", None),
                name=getattr(result, "name", update_data.get("name", "")),
                content=getattr(result, "content", content),
                type=getattr(result, "type", update_data.get("type", "A")),
                ttl=getattr(result, "ttl", update_data.get("ttl", 1)),
                proxied=getattr(result, "proxied", False),
            )

            logger.info(f"Updated DNS record {record_id}: {dns_record.name} -> {content}")
            return dns_record

        except cloudflare.APIError as e:
            raise DNSError(f"Failed to update DNS record {record_id}: {e}") from e
        except Exception as e:
            raise DNSError(f"Unexpected error updating DNS record {record_id}: {e}") from e

    def upsert_record(
        self,
        zone_id: str,
        name: str,
        content: str,
        record_type: str = "A",
        proxied: bool = False,
        ttl: int = 1,
    ) -> DNSRecord:
        """
        Create or update DNS record (upsert operation).

        If a record with the same name and type exists, it will be updated.
        Otherwise, a new record will be created.

        Args:
            zone_id: Zone ID to create/update record in
            name: Record name
            content: Record content
            record_type: Record type (A, AAAA, CNAME, etc.)
            proxied: Whether record should be proxied through CloudFlare
            ttl: Time to live (1 for automatic)

        Returns:
            DNSRecord: Created or updated DNS record

        Raises:
            DNSError: If upsert operation fails
            AuthenticationError: If not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("Not authenticated with CloudFlare API")

        try:
            # Look for existing record with same name and type
            existing_records = self.list_records(zone_id, record_type=record_type, name=name)

            if existing_records:
                # Update the first matching record
                existing_record = existing_records[0]
                logger.debug(f"Updating existing record {existing_record.id}: {name}")
                return self.update_record(
                    zone_id=zone_id,
                    record_id=existing_record.id,
                    content=content,
                    proxied=proxied,
                    ttl=ttl,
                )
            else:
                # Create new record
                logger.debug(f"Creating new record: {name}")
                return self.create_record(
                    zone_id=zone_id,
                    name=name,
                    content=content,
                    record_type=record_type,
                    proxied=proxied,
                    ttl=ttl,
                )

        except DNSError:
            # Re-raise DNS errors as-is
            raise
        except Exception as e:
            raise DNSError(f"Unexpected error during upsert for {name}: {e}") from e

    def delete_record(self, zone_id: str, record_id: str) -> bool:
        """
        Delete DNS record.

        Args:
            zone_id: Zone ID containing the record
            record_id: Record ID to delete

        Returns:
            bool: True if deletion was successful

        Raises:
            DNSError: If record deletion fails
            AuthenticationError: If not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("Not authenticated with CloudFlare API")

        try:
            # Delete the record
            result = self.client.dns.records.delete(dns_record_id=record_id, zone_id=zone_id)

            # Check if deletion was successful
            success = getattr(result, "id", None) == record_id

            if success:
                logger.info(f"Deleted DNS record {record_id}")
            else:
                logger.warning(f"DNS record deletion may have failed for {record_id}")

            return success

        except cloudflare.APIError as e:
            raise DNSError(f"Failed to delete DNS record {record_id}: {e}") from e
        except Exception as e:
            raise DNSError(f"Unexpected error deleting DNS record {record_id}: {e}") from e
