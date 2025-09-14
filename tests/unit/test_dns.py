"""Unit tests for DNS management functionality."""

from unittest.mock import Mock, patch

import cloudflare
import pytest

from cdnbestip.config import Config
from cdnbestip.dns import DNSManager
from cdnbestip.exceptions import AuthenticationError, DNSError


class TestDNSAuthentication:
    """Test DNS authentication functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a config with validation disabled for testing
        self.config = Config()
        self.config._skip_validation = True

    def test_authenticate_with_api_token_success(self):
        """Test successful authentication with API token."""
        # Setup config with API token
        self.config.cloudflare_api_token = "test_token_123"

        dns_manager = DNSManager(self.config)

        with patch("cdnbestip.dns.Cloudflare") as mock_cloudflare:
            mock_client = Mock()
            mock_cloudflare.return_value = mock_client

            # Mock successful user.get() call for token validation
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_client.user.get.return_value = mock_user

            # Authenticate
            dns_manager.authenticate()

            # Verify client was created with token
            mock_cloudflare.assert_called_once_with(api_token="test_token_123")
            assert dns_manager.client == mock_client
            assert dns_manager.is_authenticated()

            # Verify validation call was made
            mock_client.user.get.assert_called_once()

    def test_authenticate_with_api_key_email_success(self):
        """Test successful authentication with API key and email."""
        # Setup config with API key and email
        self.config.cloudflare_api_key = "test_key_123"
        self.config.cloudflare_account = "test@example.com"

        dns_manager = DNSManager(self.config)

        with patch("cdnbestip.dns.Cloudflare") as mock_cloudflare:
            mock_client = Mock()
            mock_cloudflare.return_value = mock_client

            # Mock successful zones.list() call for key validation
            mock_zones = Mock()
            mock_zones.result = []
            mock_client.zones.list.return_value = mock_zones

            # Authenticate
            dns_manager.authenticate()

            # Verify client was created with key and email
            mock_cloudflare.assert_called_once_with(
                api_key="test_key_123", api_email="test@example.com"
            )
            assert dns_manager.client == mock_client
            assert dns_manager.is_authenticated()

            # Verify validation call was made
            mock_client.zones.list.assert_called_once_with(per_page=1)

    def test_authenticate_no_credentials(self):
        """Test authentication failure when no credentials provided."""
        # Config with no credentials
        dns_manager = DNSManager(self.config)

        with pytest.raises(AuthenticationError) as exc_info:
            dns_manager.authenticate()

        assert "No valid CloudFlare credentials found" in str(exc_info.value)
        assert not dns_manager.is_authenticated()

    def test_authenticate_api_connection_error(self):
        """Test authentication failure due to API connection error."""
        self.config.cloudflare_api_token = "test_token_123"
        dns_manager = DNSManager(self.config)

        with patch("cdnbestip.dns.Cloudflare") as mock_cloudflare:
            # Create a mock request object for APIConnectionError
            mock_request = Mock()
            mock_cloudflare.side_effect = cloudflare.APIConnectionError(
                message="Connection failed", request=mock_request
            )

            with pytest.raises(AuthenticationError) as exc_info:
                dns_manager.authenticate()

            assert "Failed to connect to CloudFlare API" in str(exc_info.value)
            assert not dns_manager.is_authenticated()

    def test_authenticate_invalid_credentials(self):
        """Test authentication failure due to invalid credentials."""
        self.config.cloudflare_api_token = "invalid_token"
        dns_manager = DNSManager(self.config)

        with patch("cdnbestip.dns.Cloudflare") as mock_cloudflare:
            mock_client = Mock()
            mock_cloudflare.return_value = mock_client

            # Mock authentication error during validation
            mock_response = Mock()
            mock_client.user.get.side_effect = cloudflare.AuthenticationError(
                message="Invalid token", response=mock_response, body=None
            )

            with pytest.raises(AuthenticationError) as exc_info:
                dns_manager.authenticate()

            assert "Invalid credentials" in str(exc_info.value)
            assert not dns_manager.is_authenticated()

    def test_authenticate_permission_error(self):
        """Test authentication failure due to insufficient permissions."""
        self.config.cloudflare_api_key = "test_key_123"
        self.config.cloudflare_account = "test@example.com"
        dns_manager = DNSManager(self.config)

        with patch("cdnbestip.dns.Cloudflare") as mock_cloudflare:
            mock_client = Mock()
            mock_cloudflare.return_value = mock_client

            # Mock permission error during validation
            mock_response = Mock()
            mock_client.zones.list.side_effect = cloudflare.PermissionDeniedError(
                message="Insufficient permissions", response=mock_response, body=None
            )

            with pytest.raises(AuthenticationError) as exc_info:
                dns_manager.authenticate()

            assert "Insufficient permissions" in str(exc_info.value)
            assert not dns_manager.is_authenticated()

    def test_authenticate_prefers_token_over_key(self):
        """Test that API token is preferred over API key when both are provided."""
        # Setup config with both token and key/email
        self.config.cloudflare_api_token = "test_token_123"
        self.config.cloudflare_api_key = "test_key_123"
        self.config.cloudflare_account = "test@example.com"

        dns_manager = DNSManager(self.config)

        with patch("cdnbestip.dns.Cloudflare") as mock_cloudflare:
            mock_client = Mock()
            mock_cloudflare.return_value = mock_client

            # Mock successful user.get() call for token validation
            mock_user = Mock()
            mock_user.email = "test@example.com"
            mock_client.user.get.return_value = mock_user

            # Authenticate
            dns_manager.authenticate()

            # Verify client was created with token (not key/email)
            mock_cloudflare.assert_called_once_with(api_token="test_token_123")
            mock_client.user.get.assert_called_once()
            # zones.list should not be called for token auth
            mock_client.zones.list.assert_not_called()

    def test_validate_credentials_no_client(self):
        """Test credential validation when client is not initialized."""
        dns_manager = DNSManager(self.config)

        with pytest.raises(AuthenticationError) as exc_info:
            dns_manager._validate_credentials()

        assert "Client not initialized" in str(exc_info.value)

    def test_validate_credentials_with_client_token_success(self):
        """Test credential validation with token using specific client."""
        self.config.cloudflare_api_token = "test_token_123"
        dns_manager = DNSManager(self.config)

        mock_client = Mock()
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_client.user.get.return_value = mock_user

        # Should not raise any exception
        dns_manager._validate_credentials_with_client(mock_client)
        mock_client.user.get.assert_called_once()

    def test_validate_credentials_with_client_key_success(self):
        """Test credential validation with key/email using specific client."""
        self.config.cloudflare_api_key = "test_key_123"
        self.config.cloudflare_account = "test@example.com"
        dns_manager = DNSManager(self.config)

        mock_client = Mock()
        mock_zones = Mock()
        mock_zones.result = []
        mock_client.zones.list.return_value = mock_zones

        # Should not raise any exception
        dns_manager._validate_credentials_with_client(mock_client)
        mock_client.zones.list.assert_called_once_with(per_page=1)

    def test_is_authenticated_false_when_no_client(self):
        """Test is_authenticated returns False when no client is set."""
        dns_manager = DNSManager(self.config)
        assert not dns_manager.is_authenticated()

    def test_is_authenticated_true_when_client_exists(self):
        """Test is_authenticated returns True when client is set."""
        dns_manager = DNSManager(self.config)
        dns_manager.client = Mock()
        assert dns_manager.is_authenticated()


class TestDNSManagerInitialization:
    """Test DNS manager initialization."""

    def test_init_with_config(self):
        """Test DNS manager initialization with config."""
        config = Config()
        config._skip_validation = True

        dns_manager = DNSManager(config)

        assert dns_manager.config == config
        assert dns_manager.client is None
        assert not dns_manager.is_authenticated()


class TestDNSZoneOperations:
    """Test DNS zone operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.config._skip_validation = True
        self.dns_manager = DNSManager(self.config)
        self.dns_manager.client = Mock()

    def test_get_zone_id_success(self):
        """Test successful zone ID retrieval."""
        # Mock zone response
        mock_zone = Mock()
        mock_zone.id = "zone123"
        mock_zone.name = "example.com"

        mock_zones = Mock()
        mock_zones.result = [mock_zone]
        self.dns_manager.client.zones.list.return_value = mock_zones

        zone_id = self.dns_manager.get_zone_id("example.com")

        assert zone_id == "zone123"
        self.dns_manager.client.zones.list.assert_called_once_with(name="example.com")

    def test_get_zone_id_not_found(self):
        """Test zone ID retrieval when zone not found."""
        mock_zones = Mock()
        mock_zones.result = []
        self.dns_manager.client.zones.list.return_value = mock_zones

        with pytest.raises(DNSError) as exc_info:
            self.dns_manager.get_zone_id("nonexistent.com")

        assert "Zone not found for domain: nonexistent.com" in str(exc_info.value)

    def test_get_zone_id_not_authenticated(self):
        """Test zone ID retrieval when not authenticated."""
        self.dns_manager.client = None

        with pytest.raises(AuthenticationError) as exc_info:
            self.dns_manager.get_zone_id("example.com")

        assert "Not authenticated" in str(exc_info.value)

    def test_list_zones_success(self):
        """Test successful zone listing."""
        # Mock zone objects
        mock_zone1 = Mock()
        mock_zone1.id = "zone1"
        mock_zone1.name = "example.com"
        mock_zone1.status = "active"
        mock_zone1.paused = False
        mock_zone1.type = "full"
        mock_zone1.development_mode = 0

        mock_zone2 = Mock()
        mock_zone2.id = "zone2"
        mock_zone2.name = "test.com"
        mock_zone2.status = "active"
        mock_zone2.paused = False
        mock_zone2.type = "full"
        mock_zone2.development_mode = 0

        mock_zones = Mock()
        mock_zones.result = [mock_zone1, mock_zone2]
        self.dns_manager.client.zones.list.return_value = mock_zones

        zones = self.dns_manager.list_zones()

        assert len(zones) == 2
        assert zones[0]["id"] == "zone1"
        assert zones[0]["name"] == "example.com"
        assert zones[1]["id"] == "zone2"
        assert zones[1]["name"] == "test.com"

    def test_list_zones_not_authenticated(self):
        """Test zone listing when not authenticated."""
        self.dns_manager.client = None

        with pytest.raises(AuthenticationError) as exc_info:
            self.dns_manager.list_zones()

        assert "Not authenticated" in str(exc_info.value)


class TestDNSRecordOperations:
    """Test DNS record CRUD operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.config._skip_validation = True
        self.dns_manager = DNSManager(self.config)
        self.dns_manager.client = Mock()
        self.zone_id = "zone123"

    def test_list_records_success(self):
        """Test successful record listing."""
        # Mock record objects
        mock_record1 = Mock()
        mock_record1.id = "record1"
        mock_record1.zone_id = self.zone_id
        mock_record1.zone_name = "example.com"
        mock_record1.name = "www.example.com"
        mock_record1.content = "192.168.1.1"
        mock_record1.type = "A"
        mock_record1.ttl = 300
        mock_record1.proxied = True

        mock_records = Mock()
        mock_records.result = [mock_record1]
        self.dns_manager.client.dns.records.list.return_value = mock_records

        records = self.dns_manager.list_records(self.zone_id)

        assert len(records) == 1
        record = records[0]
        assert record.id == "record1"
        assert record.name == "www.example.com"
        assert record.content == "192.168.1.1"
        assert record.type == "A"
        assert record.proxied is True

    def test_list_records_with_filters(self):
        """Test record listing with type and name filters."""
        mock_records = Mock()
        mock_records.result = []
        self.dns_manager.client.dns.records.list.return_value = mock_records

        self.dns_manager.list_records(self.zone_id, record_type="A", name="www.example.com")

        self.dns_manager.client.dns.records.list.assert_called_once_with(
            zone_id=self.zone_id, type="A", name="www.example.com"
        )

    def test_create_record_success(self):
        """Test successful record creation."""
        # Mock created record response
        mock_result = Mock()
        mock_result.id = "new_record_id"
        mock_result.zone_id = self.zone_id
        mock_result.zone_name = "example.com"
        mock_result.name = "api.example.com"
        mock_result.content = "192.168.1.2"
        mock_result.type = "A"
        mock_result.ttl = 1
        mock_result.proxied = False

        self.dns_manager.client.dns.records.create.return_value = mock_result

        record = self.dns_manager.create_record(
            zone_id=self.zone_id,
            name="api.example.com",
            content="192.168.1.2",
            record_type="A",
            proxied=False,
        )

        assert record.id == "new_record_id"
        assert record.name == "api.example.com"
        assert record.content == "192.168.1.2"
        assert record.type == "A"
        assert record.proxied is False

        self.dns_manager.client.dns.records.create.assert_called_once_with(
            zone_id=self.zone_id,
            name="api.example.com",
            content="192.168.1.2",
            type="A",
            ttl=1,
            proxied=False,
        )

    def test_update_record_success(self):
        """Test successful record update."""
        # Mock current record
        mock_current = Mock()
        mock_current.name = "api.example.com"
        mock_current.type = "A"
        mock_current.ttl = 300
        mock_current.proxied = False

        # Mock updated record response
        mock_result = Mock()
        mock_result.id = "record123"
        mock_result.zone_id = self.zone_id
        mock_result.zone_name = "example.com"
        mock_result.name = "api.example.com"
        mock_result.content = "192.168.1.3"
        mock_result.type = "A"
        mock_result.ttl = 300
        mock_result.proxied = False

        self.dns_manager.client.dns.records.get.return_value = mock_current
        self.dns_manager.client.dns.records.update.return_value = mock_result

        record = self.dns_manager.update_record(
            zone_id=self.zone_id, record_id="record123", content="192.168.1.3"
        )

        assert record.content == "192.168.1.3"

        self.dns_manager.client.dns.records.update.assert_called_once_with(
            zone_id=self.zone_id,
            dns_record_id="record123",
            name="api.example.com",
            content="192.168.1.3",
            type="A",
            ttl=300,
            proxied=False,
        )

    def test_delete_record_success(self):
        """Test successful record deletion."""
        mock_result = Mock()
        mock_result.id = "record123"

        self.dns_manager.client.dns.records.delete.return_value = mock_result

        success = self.dns_manager.delete_record(self.zone_id, "record123")

        assert success is True
        self.dns_manager.client.dns.records.delete.assert_called_once_with(
            zone_id=self.zone_id, dns_record_id="record123"
        )

    def test_upsert_record_create_new(self):
        """Test upsert operation when record doesn't exist (create)."""
        # Mock no existing records
        mock_records = Mock()
        mock_records.result = []
        self.dns_manager.client.dns.records.list.return_value = mock_records

        # Mock create response
        mock_result = Mock()
        mock_result.id = "new_record"
        mock_result.zone_id = self.zone_id
        mock_result.zone_name = "example.com"
        mock_result.name = "new.example.com"
        mock_result.content = "192.168.1.4"
        mock_result.type = "A"
        mock_result.ttl = 1
        mock_result.proxied = False

        self.dns_manager.client.dns.records.create.return_value = mock_result

        record = self.dns_manager.upsert_record(
            zone_id=self.zone_id, name="new.example.com", content="192.168.1.4"
        )

        assert record.id == "new_record"
        self.dns_manager.client.dns.records.create.assert_called_once()

    def test_upsert_record_update_existing(self):
        """Test upsert operation when record exists (update)."""
        from cdnbestip.models import DNSRecord

        # Mock existing record
        existing_record = DNSRecord(
            id="existing_record",
            zone_id=self.zone_id,
            name="existing.example.com",
            content="192.168.1.5",
            type="A",
        )

        # Mock list_records to return existing record
        with patch.object(self.dns_manager, "list_records") as mock_list:
            mock_list.return_value = [existing_record]

            # Mock update_record
            with patch.object(self.dns_manager, "update_record") as mock_update:
                mock_update.return_value = existing_record

                self.dns_manager.upsert_record(
                    zone_id=self.zone_id, name="existing.example.com", content="192.168.1.6"
                )

                mock_update.assert_called_once_with(
                    zone_id=self.zone_id,
                    record_id="existing_record",
                    content="192.168.1.6",
                    proxied=False,
                    ttl=1,
                )

    def test_record_operations_not_authenticated(self):
        """Test record operations when not authenticated."""
        self.dns_manager.client = None

        with pytest.raises(AuthenticationError):
            self.dns_manager.list_records(self.zone_id)

        with pytest.raises(AuthenticationError):
            self.dns_manager.create_record(self.zone_id, "test", "192.168.1.1")

        with pytest.raises(AuthenticationError):
            self.dns_manager.update_record(self.zone_id, "record123", "192.168.1.1")

        with pytest.raises(AuthenticationError):
            self.dns_manager.delete_record(self.zone_id, "record123")

        with pytest.raises(AuthenticationError):
            self.dns_manager.upsert_record(self.zone_id, "test", "192.168.1.1")


class TestDNSBatchOperations:
    """Test DNS batch record management operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.config._skip_validation = True
        self.dns_manager = DNSManager(self.config)
        self.dns_manager.client = Mock()
        self.zone_id = "zone123"

        # Mock zone info
        self.mock_zone = Mock()
        self.mock_zone.name = "example.com"
        self.dns_manager.client.zones.get.return_value = self.mock_zone

    def test_batch_upsert_records_success(self):
        """Test successful batch upsert of records."""
        ip_addresses = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]

        # Mock upsert_record calls
        mock_records = []
        for i, ip in enumerate(ip_addresses, 1):
            mock_record = Mock()
            mock_record.id = f"record{i}"
            mock_record.name = f"cf{i}.example.com"
            mock_record.content = ip
            mock_records.append(mock_record)

        with patch.object(self.dns_manager, "upsert_record") as mock_upsert:
            mock_upsert.side_effect = mock_records

            records = self.dns_manager.batch_upsert_records(
                zone_id=self.zone_id, base_name="cf", ip_addresses=ip_addresses
            )

            assert len(records) == 3
            assert mock_upsert.call_count == 3

            # Verify each upsert call
            expected_calls = [
                (self.zone_id, "cf1.example.com", "192.168.1.1"),
                (self.zone_id, "cf2.example.com", "192.168.1.2"),
                (self.zone_id, "cf3.example.com", "192.168.1.3"),
            ]

            for i, (zone_id, name, content) in enumerate(expected_calls):
                call_args = mock_upsert.call_args_list[i]
                assert call_args[1]["zone_id"] == zone_id
                assert call_args[1]["name"] == name
                assert call_args[1]["content"] == content

    def test_batch_upsert_records_empty_list(self):
        """Test batch upsert with empty IP list."""
        records = self.dns_manager.batch_upsert_records(
            zone_id=self.zone_id, base_name="cf", ip_addresses=[]
        )

        assert records == []

    def test_batch_upsert_records_partial_failure(self):
        """Test batch upsert with some records failing."""
        ip_addresses = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]

        # Mock first and third records succeed, second fails
        mock_record1 = Mock()
        mock_record1.name = "cf1.example.com"
        mock_record3 = Mock()
        mock_record3.name = "cf3.example.com"

        def mock_upsert_side_effect(*args, **kwargs):
            if "cf2" in kwargs["name"]:
                raise DNSError("Failed to create record")
            elif "cf1" in kwargs["name"]:
                return mock_record1
            elif "cf3" in kwargs["name"]:
                return mock_record3

        with patch.object(self.dns_manager, "upsert_record") as mock_upsert:
            mock_upsert.side_effect = mock_upsert_side_effect

            records = self.dns_manager.batch_upsert_records(
                zone_id=self.zone_id, base_name="cf", ip_addresses=ip_addresses
            )

            # Should return 2 successful records (cf1 and cf3)
            assert len(records) == 2
            assert mock_upsert.call_count == 3

    def test_list_records_by_prefix_success(self):
        """Test successful listing of records by prefix."""
        from cdnbestip.models import DNSRecord

        # Mock all records in zone
        all_records = [
            DNSRecord(id="1", name="cf1.example.com", content="192.168.1.1", type="A"),
            DNSRecord(id="2", name="cf2.example.com", content="192.168.1.2", type="A"),
            DNSRecord(id="3", name="other.example.com", content="192.168.1.3", type="A"),
            DNSRecord(id="4", name="cf10.example.com", content="192.168.1.4", type="A"),
        ]

        with patch.object(self.dns_manager, "list_records") as mock_list:
            mock_list.return_value = all_records

            matching_records = self.dns_manager.list_records_by_prefix(self.zone_id, "cf")

            # Should match cf1, cf2, cf10 but not "other"
            assert len(matching_records) == 3
            names = [r.name for r in matching_records]
            assert "cf1.example.com" in names
            assert "cf2.example.com" in names
            assert "cf10.example.com" in names
            assert "other.example.com" not in names

    def test_batch_delete_records_by_prefix_success(self):
        """Test successful batch deletion by prefix."""
        from cdnbestip.models import DNSRecord

        # Mock records matching prefix
        matching_records = [
            DNSRecord(id="1", name="cf1.example.com", content="192.168.1.1", type="A"),
            DNSRecord(id="2", name="cf2.example.com", content="192.168.1.2", type="A"),
        ]

        with patch.object(self.dns_manager, "list_records_by_prefix") as mock_list:
            mock_list.return_value = matching_records

            with patch.object(self.dns_manager, "delete_record") as mock_delete:
                mock_delete.return_value = True

                deleted_count = self.dns_manager.batch_delete_records_by_prefix(self.zone_id, "cf")

                assert deleted_count == 2
                assert mock_delete.call_count == 2
                mock_delete.assert_any_call(self.zone_id, "1")
                mock_delete.assert_any_call(self.zone_id, "2")

    def test_batch_delete_records_partial_failure(self):
        """Test batch deletion with some deletions failing."""
        from cdnbestip.models import DNSRecord

        matching_records = [
            DNSRecord(id="1", name="cf1.example.com", content="192.168.1.1", type="A"),
            DNSRecord(id="2", name="cf2.example.com", content="192.168.1.2", type="A"),
        ]

        with patch.object(self.dns_manager, "list_records_by_prefix") as mock_list:
            mock_list.return_value = matching_records

            def mock_delete_side_effect(zone_id, record_id):
                if record_id == "1":
                    return True
                else:
                    raise DNSError("Failed to delete")

            with patch.object(self.dns_manager, "delete_record") as mock_delete:
                mock_delete.side_effect = mock_delete_side_effect

                deleted_count = self.dns_manager.batch_delete_records_by_prefix(self.zone_id, "cf")

                # Should return 1 (only successful deletion)
                assert deleted_count == 1
                assert mock_delete.call_count == 2

    def test_update_batch_records_create_new(self):
        """Test batch update when no existing records exist."""
        ip_addresses = ["192.168.1.1", "192.168.1.2"]

        # Mock no existing records
        with patch.object(self.dns_manager, "list_records_by_prefix") as mock_list:
            mock_list.return_value = []

            # Mock create_record calls
            mock_records = []
            for i, ip in enumerate(ip_addresses, 1):
                mock_record = Mock()
                mock_record.name = f"cf{i}.example.com"
                mock_record.content = ip
                mock_records.append(mock_record)

            with patch.object(self.dns_manager, "create_record") as mock_create:
                mock_create.side_effect = mock_records

                records = self.dns_manager.update_batch_records(
                    zone_id=self.zone_id, prefix="cf", ip_addresses=ip_addresses
                )

                assert len(records) == 2
                assert mock_create.call_count == 2

    def test_update_batch_records_update_existing(self):
        """Test batch update when existing records exist."""
        from cdnbestip.models import DNSRecord

        ip_addresses = ["192.168.1.10", "192.168.1.20"]

        # Mock existing records
        existing_records = [
            DNSRecord(id="1", name="cf1.example.com", content="192.168.1.1", type="A"),
            DNSRecord(id="2", name="cf2.example.com", content="192.168.1.2", type="A"),
        ]

        with patch.object(self.dns_manager, "list_records_by_prefix") as mock_list:
            mock_list.return_value = existing_records

            # Mock update_record calls
            updated_records = []
            for i, ip in enumerate(ip_addresses):
                mock_record = Mock()
                mock_record.id = existing_records[i].id
                mock_record.content = ip
                updated_records.append(mock_record)

            with patch.object(self.dns_manager, "update_record") as mock_update:
                mock_update.side_effect = updated_records

                records = self.dns_manager.update_batch_records(
                    zone_id=self.zone_id, prefix="cf", ip_addresses=ip_addresses
                )

                assert len(records) == 2
                assert mock_update.call_count == 2

                # Verify update calls
                mock_update.assert_any_call(
                    zone_id=self.zone_id,
                    record_id="1",
                    content="192.168.1.10",
                    proxied=False,
                    ttl=1,
                )
                mock_update.assert_any_call(
                    zone_id=self.zone_id,
                    record_id="2",
                    content="192.168.1.20",
                    proxied=False,
                    ttl=1,
                )

    def test_update_batch_records_delete_excess(self):
        """Test batch update when there are more existing records than IPs."""
        from cdnbestip.models import DNSRecord

        ip_addresses = ["192.168.1.10"]  # Only 1 IP

        # Mock 3 existing records
        existing_records = [
            DNSRecord(id="1", name="cf1.example.com", content="192.168.1.1", type="A"),
            DNSRecord(id="2", name="cf2.example.com", content="192.168.1.2", type="A"),
            DNSRecord(id="3", name="cf3.example.com", content="192.168.1.3", type="A"),
        ]

        with patch.object(self.dns_manager, "list_records_by_prefix") as mock_list:
            mock_list.return_value = existing_records

            # Mock update for first record
            mock_updated = Mock()
            mock_updated.content = "192.168.1.10"

            with patch.object(self.dns_manager, "update_record") as mock_update:
                mock_update.return_value = mock_updated

                with patch.object(self.dns_manager, "delete_record") as mock_delete:
                    mock_delete.return_value = True

                    records = self.dns_manager.update_batch_records(
                        zone_id=self.zone_id, prefix="cf", ip_addresses=ip_addresses
                    )

                    # Should update 1 record and delete 2 excess records
                    assert len(records) == 1
                    assert mock_update.call_count == 1
                    assert mock_delete.call_count == 2

                    # Verify delete calls for excess records
                    mock_delete.assert_any_call(self.zone_id, "2")
                    mock_delete.assert_any_call(self.zone_id, "3")

    def test_batch_operations_not_authenticated(self):
        """Test batch operations when not authenticated."""
        self.dns_manager.client = None

        with pytest.raises(AuthenticationError):
            self.dns_manager.batch_upsert_records(self.zone_id, "cf", ["192.168.1.1"])

        with pytest.raises(AuthenticationError):
            self.dns_manager.list_records_by_prefix(self.zone_id, "cf")

        with pytest.raises(AuthenticationError):
            self.dns_manager.batch_delete_records_by_prefix(self.zone_id, "cf")

        with pytest.raises(AuthenticationError):
            self.dns_manager.update_batch_records(self.zone_id, "cf", ["192.168.1.1"])


class TestDNSRecordAttributeHandling:
    """Test DNS record attribute handling with missing CloudFlare API attributes."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.config._skip_validation = True
        self.dns_manager = DNSManager(self.config)
        self.dns_manager.client = Mock()
        self.zone_id = "test_zone_123"

    def test_list_records_with_missing_zone_id(self):
        """Test list_records when CloudFlare record objects lack zone_id attribute."""
        # Create mock record without zone_id and zone_name attributes
        mock_record = Mock()
        mock_record.id = "record123"
        mock_record.name = "test.example.com"
        mock_record.content = "192.168.1.1"
        mock_record.type = "A"
        mock_record.ttl = 300
        mock_record.proxied = False

        # Simulate missing attributes by deleting them
        del mock_record.zone_id
        del mock_record.zone_name

        # Mock API response
        mock_response = Mock()
        mock_response.result = [mock_record]
        self.dns_manager.client.dns.records.list.return_value = mock_response

        # Should not raise AttributeError
        records = self.dns_manager.list_records(self.zone_id)

        assert len(records) == 1
        record = records[0]
        assert record.id == "record123"
        assert record.name == "test.example.com"
        assert record.content == "192.168.1.1"
        assert record.type == "A"
        assert record.zone_id == self.zone_id  # Should fallback to provided zone_id
        assert record.zone_name is None  # Should fallback to None

    def test_list_records_with_partial_missing_attributes(self):
        """Test list_records when some attributes are missing from different records."""
        # First record missing zone_id
        mock_record1 = Mock()
        mock_record1.id = "record1"
        mock_record1.zone_name = "example.com"
        mock_record1.name = "test1.example.com"
        mock_record1.content = "192.168.1.1"
        mock_record1.type = "A"
        mock_record1.ttl = 300
        mock_record1.proxied = False
        del mock_record1.zone_id

        # Second record missing zone_name
        mock_record2 = Mock()
        mock_record2.id = "record2"
        mock_record2.zone_id = "different_zone"
        mock_record2.name = "test2.example.com"
        mock_record2.content = "192.168.1.2"
        mock_record2.type = "A"
        mock_record2.ttl = 300
        mock_record2.proxied = False
        del mock_record2.zone_name

        # Mock API response
        mock_response = Mock()
        mock_response.result = [mock_record1, mock_record2]
        self.dns_manager.client.dns.records.list.return_value = mock_response

        records = self.dns_manager.list_records(self.zone_id)

        assert len(records) == 2

        # First record should use fallback zone_id but keep zone_name
        record1 = records[0]
        assert record1.zone_id == self.zone_id  # Fallback
        assert record1.zone_name == "example.com"  # Original value

        # Second record should keep zone_id but fallback zone_name
        record2 = records[1]
        assert record2.zone_id == "different_zone"  # Original value
        assert record2.zone_name is None  # Fallback

    def test_create_record_with_missing_attributes(self):
        """Test create_record when result lacks some attributes."""
        # Mock create result missing zone_id and zone_name
        mock_result = Mock()
        mock_result.id = "new_record"
        mock_result.name = "new.example.com"
        mock_result.content = "192.168.1.5"
        mock_result.type = "A"
        mock_result.ttl = 1
        mock_result.proxied = False
        del mock_result.zone_id
        del mock_result.zone_name

        self.dns_manager.client.dns.records.create.return_value = mock_result

        record = self.dns_manager.create_record(
            zone_id=self.zone_id, name="new.example.com", content="192.168.1.5"
        )

        assert record.id == "new_record"
        assert record.name == "new.example.com"
        assert record.content == "192.168.1.5"
        assert record.zone_id == self.zone_id  # Should fallback
        assert record.zone_name is None  # Should fallback

    def test_update_record_with_missing_attributes(self):
        """Test update_record when result lacks some attributes."""
        # Mock current record for getting existing values
        mock_current = Mock()
        mock_current.name = "existing.example.com"
        mock_current.type = "A"
        mock_current.ttl = 300
        mock_current.proxied = False

        # Mock update result missing zone_id and zone_name
        mock_result = Mock()
        mock_result.id = "updated_record"
        mock_result.name = "existing.example.com"
        mock_result.content = "192.168.1.10"
        mock_result.type = "A"
        mock_result.ttl = 300
        mock_result.proxied = False
        del mock_result.zone_id
        del mock_result.zone_name

        self.dns_manager.client.dns.records.get.return_value = mock_current
        self.dns_manager.client.dns.records.update.return_value = mock_result

        record = self.dns_manager.update_record(
            zone_id=self.zone_id, record_id="updated_record", content="192.168.1.10"
        )

        assert record.id == "updated_record"
        assert record.content == "192.168.1.10"
        assert record.zone_id == self.zone_id  # Should fallback
        assert record.zone_name is None  # Should fallback

    def test_arecord_simulation(self):
        """Test simulation of the original ARecord error scenario."""

        # Simulate CloudFlare ARecord type that caused the original error
        class MockARecord:
            def __init__(self):
                self.id = "arecord_123"
                self.name = "xf1.222029.xyz"
                self.content = "1.1.1.1"
                self.type = "A"
                self.ttl = 1
                self.proxied = False
                # Intentionally NOT setting zone_id and zone_name

        arecord = MockARecord()

        # Verify ARecord lacks the problematic attributes
        assert not hasattr(arecord, "zone_id")
        assert not hasattr(arecord, "zone_name")

        # Mock API response with ARecord
        mock_response = Mock()
        mock_response.result = [arecord]
        self.dns_manager.client.dns.records.list.return_value = mock_response

        # This should NOT raise 'ARecord' object has no attribute 'zone_id'
        zone_id = "4965ab73e1c48b6cb7aa780947568bcd"  # From original error
        records = self.dns_manager.list_records(zone_id, record_type="A", name="xf1.222029.xyz")

        assert len(records) == 1
        record = records[0]
        assert record.id == "arecord_123"
        assert record.name == "xf1.222029.xyz"
        assert record.content == "1.1.1.1"
        assert record.zone_id == zone_id  # Fallback value
        assert record.zone_name is None  # Fallback value

    def test_batch_operations_with_missing_attributes(self):
        """Test that batch operations work correctly with missing attributes."""
        # Mock zone info
        mock_zone = Mock()
        mock_zone.name = "example.com"
        self.dns_manager.client.zones.get.return_value = mock_zone

        # Mock upsert_record to simulate records with missing attributes
        def mock_upsert_side_effect(*args, **kwargs):
            record = Mock()
            record.id = f"record_{kwargs['content'].replace('.', '_')}"
            record.name = kwargs["name"]
            record.content = kwargs["content"]
            record.type = kwargs.get("record_type", "A")
            # Simulate missing zone_id and zone_name in some responses
            if "1.1" in kwargs["content"]:
                del record.zone_id
            if "1.0" in kwargs["content"]:
                del record.zone_name
            return record

        with patch.object(self.dns_manager, "upsert_record") as mock_upsert:
            mock_upsert.side_effect = mock_upsert_side_effect

            # Should not raise any AttributeError
            records = self.dns_manager.batch_upsert_records(
                zone_id=self.zone_id, base_name="cf", ip_addresses=["1.1.1.1", "1.0.0.1", "8.8.8.8"]
            )

            assert len(records) == 3
            assert mock_upsert.call_count == 3

    def test_all_attributes_missing(self):
        """Test extreme case where most attributes are missing."""
        # Create minimal mock record with only required attributes
        mock_record = Mock()
        # Only set spec to prevent mock from having any attributes by default
        mock_record._spec_class = object

        # Manually set only a few attributes
        mock_record.content = "192.168.1.100"
        # All other attributes will be missing

        mock_response = Mock()
        mock_response.result = [mock_record]
        self.dns_manager.client.dns.records.list.return_value = mock_response

        records = self.dns_manager.list_records(self.zone_id)

        assert len(records) == 1
        record = records[0]

        # Should use fallback values for all missing attributes
        assert record.id is None  # Fallback
        assert record.zone_id == self.zone_id  # Fallback
        assert record.zone_name is None  # Fallback
        assert record.name == ""  # Fallback
        assert record.content == "192.168.1.100"  # Original value
        assert record.type == "A"  # Fallback
        assert record.ttl == 1  # Fallback
        assert record.proxied is False  # Fallback
