"""
Integration tests for CloudFlare API operations.

This module tests actual CloudFlare API integration with mocked responses
that simulate real API behavior and error conditions.
"""

from unittest.mock import Mock, patch

import cloudflare
import pytest

from cdnbestip.config import Config
from cdnbestip.dns import DNSManager
from cdnbestip.exceptions import AuthenticationError, DNSError


class TestCloudFlareAPIAuthentication:
    """Test CloudFlare API authentication scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config()
        self.config._skip_validation = True

    @patch("cdnbestip.dns.Cloudflare")
    def test_api_token_authentication_flow(self, mock_cloudflare):
        """Test complete API token authentication flow."""
        self.config.cloudflare_api_token = "test_token_12345"

        # Mock CloudFlare client
        mock_client = Mock()
        mock_cloudflare.return_value = mock_client

        # Mock successful user.get() call
        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_client.user.get.return_value = mock_user

        dns_manager = DNSManager(self.config)
        dns_manager.authenticate()

        # Verify authentication
        assert dns_manager.is_authenticated()
        mock_cloudflare.assert_called_once_with(api_token="test_token_12345")
        mock_client.user.get.assert_called_once()

    @patch("cdnbestip.dns.Cloudflare")
    def test_api_key_email_authentication_flow(self, mock_cloudflare):
        """Test complete API key + email authentication flow."""
        self.config.cloudflare_api_key = "test_key_67890"
        self.config.cloudflare_email = "test@example.com"

        # Mock CloudFlare client
        mock_client = Mock()
        mock_cloudflare.return_value = mock_client

        # Mock successful zones.list() call for validation
        mock_zone = Mock()
        mock_zone.id = "zone123"
        mock_zone.name = "example.com"
        mock_zones = Mock()
        mock_zones.result = [mock_zone]
        mock_client.zones.list.return_value = mock_zones

        dns_manager = DNSManager(self.config)
        dns_manager.authenticate()

        # Verify authentication
        assert dns_manager.is_authenticated()
        mock_cloudflare.assert_called_once_with(
            api_key="test_key_67890", api_email="test@example.com"
        )
        mock_client.zones.list.assert_called_once_with(per_page=1)

    @patch("cdnbestip.dns.Cloudflare")
    def test_authentication_with_invalid_token(self, mock_cloudflare):
        """Test authentication with invalid API token."""
        self.config.cloudflare_api_token = "invalid_token"

        mock_client = Mock()
        mock_cloudflare.return_value = mock_client

        # Mock authentication error
        mock_response = Mock()
        mock_response.status_code = 401
        mock_client.user.get.side_effect = cloudflare.AuthenticationError(
            message="Invalid API token",
            response=mock_response,
            body={"errors": [{"code": 10000, "message": "Invalid API token"}]},
        )

        dns_manager = DNSManager(self.config)

        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            dns_manager.authenticate()

        assert not dns_manager.is_authenticated()

    @patch("cdnbestip.dns.Cloudflare")
    def test_authentication_with_insufficient_permissions(self, mock_cloudflare):
        """Test authentication with insufficient permissions."""
        self.config.cloudflare_api_key = "limited_key"
        self.config.cloudflare_email = "test@example.com"

        mock_client = Mock()
        mock_cloudflare.return_value = mock_client

        # Mock permission error
        mock_response = Mock()
        mock_response.status_code = 403
        mock_client.zones.list.side_effect = cloudflare.PermissionDeniedError(
            message="Insufficient permissions",
            response=mock_response,
            body={"errors": [{"code": 10001, "message": "Insufficient permissions"}]},
        )

        dns_manager = DNSManager(self.config)

        with pytest.raises(AuthenticationError, match="Insufficient permissions"):
            dns_manager.authenticate()

    @patch("cdnbestip.dns.Cloudflare")
    def test_authentication_with_network_error(self, mock_cloudflare):
        """Test authentication with network connectivity issues."""
        self.config.cloudflare_api_token = "test_token"

        # Mock connection error during client creation
        mock_request = Mock()
        mock_cloudflare.side_effect = cloudflare.APIConnectionError(
            message="Connection failed", request=mock_request
        )

        dns_manager = DNSManager(self.config)

        with pytest.raises(AuthenticationError, match="Failed to connect"):
            dns_manager.authenticate()


class TestCloudFlareZoneOperations:
    """Test CloudFlare zone operations."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config(cloudflare_api_token="test_token")
        self.config._skip_validation = True
        self.dns_manager = DNSManager(self.config)

        # Mock authenticated client
        self.mock_client = Mock()
        self.dns_manager.client = self.mock_client

    def test_list_zones_with_multiple_zones(self):
        """Test listing zones with multiple zones."""
        # Mock multiple zones
        mock_zones = [
            Mock(id="zone1", name="example.com", status="active", paused=False, type="full"),
            Mock(id="zone2", name="test.com", status="active", paused=False, type="full"),
            Mock(id="zone3", name="demo.org", status="pending", paused=True, type="partial"),
        ]

        mock_zones_response = Mock()
        mock_zones_response.result = mock_zones
        self.mock_client.zones.list.return_value = mock_zones_response

        zones = self.dns_manager.list_zones()

        assert len(zones) == 3
        assert zones[0]["name"] == "example.com"
        assert zones[0]["status"] == "active"
        assert zones[1]["name"] == "test.com"
        assert zones[2]["name"] == "demo.org"
        assert zones[2]["status"] == "pending"

    def test_get_zone_id_with_exact_match(self):
        """Test getting zone ID with exact domain match."""
        mock_zone = Mock()
        mock_zone.id = "zone123"
        mock_zone.name = "example.com"

        mock_zones = Mock()
        mock_zones.result = [mock_zone]
        self.mock_client.zones.list.return_value = mock_zones

        zone_id = self.dns_manager.get_zone_id("example.com")

        assert zone_id == "zone123"
        self.mock_client.zones.list.assert_called_once_with(name="example.com")

    def test_get_zone_id_with_subdomain(self):
        """Test getting zone ID for subdomain (should find parent zone)."""
        mock_zone = Mock()
        mock_zone.id = "zone123"
        mock_zone.name = "example.com"

        # First call for exact match returns empty, second for parent domain succeeds
        empty_result = Mock()
        empty_result.result = []

        parent_result = Mock()
        parent_result.result = [mock_zone]

        self.mock_client.zones.list.side_effect = [empty_result, parent_result]

        zone_id = self.dns_manager.get_zone_id("sub.example.com")

        assert zone_id == "zone123"
        assert self.mock_client.zones.list.call_count == 2

    def test_get_zone_id_not_found(self):
        """Test getting zone ID when zone doesn't exist."""
        mock_zones = Mock()
        mock_zones.result = []
        self.mock_client.zones.list.return_value = mock_zones

        with pytest.raises(DNSError, match="Zone not found"):
            self.dns_manager.get_zone_id("nonexistent.com")

    def test_zone_operations_with_rate_limiting(self):
        """Test zone operations with rate limiting."""
        # Mock rate limit error then success
        mock_response = Mock()
        mock_response.status_code = 429

        rate_limit_error = cloudflare.RateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body={"errors": [{"code": 10037, "message": "Rate limit exceeded"}]},
        )

        mock_zone = Mock()
        mock_zone.id = "zone123"
        mock_zone.name = "example.com"
        mock_zones = Mock()
        mock_zones.result = [mock_zone]

        self.mock_client.zones.list.side_effect = [rate_limit_error, mock_zones]

        with patch("time.sleep"):  # Speed up test
            zone_id = self.dns_manager.get_zone_id("example.com")

        assert zone_id == "zone123"
        assert self.mock_client.zones.list.call_count == 2


class TestCloudFlareDNSRecordOperations:
    """Test CloudFlare DNS record CRUD operations."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config(cloudflare_api_token="test_token")
        self.config._skip_validation = True
        self.dns_manager = DNSManager(self.config)

        # Mock authenticated client
        self.mock_client = Mock()
        self.dns_manager.client = self.mock_client
        self.zone_id = "zone123"

    def test_list_records_with_pagination(self):
        """Test listing records with pagination."""
        # Mock paginated response
        page1_records = [
            Mock(
                id="rec1",
                name="www.example.com",
                content="1.1.1.1",
                type="A",
                ttl=300,
                proxied=True,
            ),
            Mock(
                id="rec2",
                name="api.example.com",
                content="1.0.0.1",
                type="A",
                ttl=300,
                proxied=False,
            ),
        ]

        page2_records = [
            Mock(
                id="rec3",
                name="mail.example.com",
                content="8.8.8.8",
                type="A",
                ttl=300,
                proxied=False,
            )
        ]

        # Mock multiple pages
        page1_response = Mock()
        page1_response.result = page1_records
        page1_response.result_info = Mock(page=1, per_page=2, total_pages=2, total_count=3)

        page2_response = Mock()
        page2_response.result = page2_records
        page2_response.result_info = Mock(page=2, per_page=2, total_pages=2, total_count=3)

        self.mock_client.zones.dns_records.list.side_effect = [page1_response, page2_response]

        # List all records (should handle pagination automatically)
        records = self.dns_manager.list_records(self.zone_id)

        assert len(records) == 3
        assert records[0].name == "www.example.com"
        assert records[1].name == "api.example.com"
        assert records[2].name == "mail.example.com"

    def test_create_record_with_different_types(self):
        """Test creating records of different types."""
        record_configs = [
            {"name": "www.example.com", "content": "192.168.1.1", "type": "A"},
            {"name": "ipv6.example.com", "content": "2001:db8::1", "type": "AAAA"},
            {"name": "alias.example.com", "content": "www.example.com", "type": "CNAME"},
            {"name": "example.com", "content": "10 mail.example.com", "type": "MX"},
            {
                "name": "example.com",
                "content": "v=spf1 include:_spf.google.com ~all",
                "type": "TXT",
            },
        ]

        for i, config in enumerate(record_configs):
            mock_result = Mock()
            mock_result.id = f"record{i}"
            mock_result.zone_id = self.zone_id
            mock_result.name = config["name"]
            mock_result.content = config["content"]
            mock_result.type = config["type"]
            mock_result.ttl = 1
            mock_result.proxied = False

            self.mock_client.zones.dns_records.create.return_value = mock_result

            record = self.dns_manager.create_record(
                zone_id=self.zone_id,
                name=config["name"],
                content=config["content"],
                record_type=config["type"],
            )

            assert record.name == config["name"]
            assert record.content == config["content"]
            assert record.type == config["type"]

    def test_update_record_with_different_fields(self):
        """Test updating records with different field changes."""
        # Mock existing record
        existing_record = Mock()
        existing_record.name = "www.example.com"
        existing_record.content = "192.168.1.1"
        existing_record.type = "A"
        existing_record.ttl = 300
        existing_record.proxied = False

        self.mock_client.zones.dns_records.get.return_value = existing_record

        # Test different update scenarios
        update_scenarios = [
            {"content": "192.168.1.2"},  # Content change
            {"ttl": 3600},  # TTL change
            {"proxied": True},  # Proxy status change
            {"content": "192.168.1.3", "ttl": 1800, "proxied": True},  # Multiple changes
        ]

        for i, updates in enumerate(update_scenarios):
            mock_result = Mock()
            mock_result.id = f"record{i}"
            mock_result.zone_id = self.zone_id
            mock_result.name = existing_record.name
            mock_result.content = updates.get("content", existing_record.content)
            mock_result.type = existing_record.type
            mock_result.ttl = updates.get("ttl", existing_record.ttl)
            mock_result.proxied = updates.get("proxied", existing_record.proxied)

            self.mock_client.zones.dns_records.update.return_value = mock_result

            record = self.dns_manager.update_record(
                zone_id=self.zone_id, record_id=f"record{i}", **updates
            )

            for field, value in updates.items():
                assert getattr(record, field) == value

    def test_delete_record_success_and_failure(self):
        """Test record deletion success and failure scenarios."""
        # Test successful deletion
        mock_result = Mock()
        mock_result.id = "record123"
        self.mock_client.zones.dns_records.delete.return_value = mock_result

        success = self.dns_manager.delete_record(self.zone_id, "record123")
        assert success is True

        # Test deletion failure
        mock_response = Mock()
        mock_response.status_code = 404
        self.mock_client.zones.dns_records.delete.side_effect = cloudflare.NotFoundError(
            message="Record not found",
            response=mock_response,
            body={"errors": [{"code": 81044, "message": "Record not found"}]},
        )

        with pytest.raises(DNSError, match="Record not found"):
            self.dns_manager.delete_record(self.zone_id, "nonexistent")

    def test_upsert_record_create_vs_update_logic(self):
        """Test upsert record logic for create vs update scenarios."""
        # Scenario 1: No existing record (should create)
        empty_records = Mock()
        empty_records.result = []
        self.mock_client.zones.dns_records.list.return_value = empty_records

        create_result = Mock()
        create_result.id = "new_record"
        create_result.name = "new.example.com"
        create_result.content = "192.168.1.1"
        create_result.type = "A"
        self.mock_client.zones.dns_records.create.return_value = create_result

        record = self.dns_manager.upsert_record(
            zone_id=self.zone_id, name="new.example.com", content="192.168.1.1"
        )

        assert record.id == "new_record"
        self.mock_client.zones.dns_records.create.assert_called_once()

        # Reset mocks
        self.mock_client.reset_mock()

        # Scenario 2: Existing record (should update)
        existing_record = Mock()
        existing_record.id = "existing_record"
        existing_record.name = "existing.example.com"
        existing_record.content = "192.168.1.1"
        existing_record.type = "A"
        existing_record.ttl = 300
        existing_record.proxied = False

        existing_records = Mock()
        existing_records.result = [existing_record]
        self.mock_client.zones.dns_records.list.return_value = existing_records

        # Mock get for update operation
        self.mock_client.zones.dns_records.get.return_value = existing_record

        update_result = Mock()
        update_result.id = "existing_record"
        update_result.name = "existing.example.com"
        update_result.content = "192.168.1.2"  # Updated content
        update_result.type = "A"
        update_result.ttl = 300
        update_result.proxied = False
        self.mock_client.zones.dns_records.update.return_value = update_result

        record = self.dns_manager.upsert_record(
            zone_id=self.zone_id, name="existing.example.com", content="192.168.1.2"
        )

        assert record.content == "192.168.1.2"
        self.mock_client.zones.dns_records.update.assert_called_once()
        self.mock_client.zones.dns_records.create.assert_not_called()


class TestCloudFlareBatchOperations:
    """Test CloudFlare batch operations and error handling."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config(cloudflare_api_token="test_token")
        self.config._skip_validation = True
        self.dns_manager = DNSManager(self.config)

        # Mock authenticated client
        self.mock_client = Mock()
        self.dns_manager.client = self.mock_client
        self.zone_id = "zone123"

        # Mock zone info
        mock_zone = Mock()
        mock_zone.name = "example.com"
        self.mock_client.zones.get.return_value = mock_zone

    def test_batch_upsert_with_mixed_operations(self):
        """Test batch upsert with mix of creates and updates."""
        ip_addresses = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]

        # Mock existing records (cf2 exists, cf1 and cf3 don't)
        existing_record = Mock()
        existing_record.id = "existing_cf2"
        existing_record.name = "cf2.example.com"
        existing_record.content = "10.0.0.1"  # Different IP
        existing_record.type = "A"
        existing_record.ttl = 300
        existing_record.proxied = False

        def list_records_side_effect(zone_id, **kwargs):
            if kwargs.get("name") == "cf2.example.com":
                mock_result = Mock()
                mock_result.result = [existing_record]
                return mock_result
            else:
                mock_result = Mock()
                mock_result.result = []
                return mock_result

        self.mock_client.zones.dns_records.list.side_effect = list_records_side_effect

        # Mock get for update operation
        self.mock_client.zones.dns_records.get.return_value = existing_record

        # Mock create operations for cf1 and cf3
        def create_side_effect(**kwargs):
            mock_record = Mock()
            mock_record.id = f"new_{kwargs['name']}"
            mock_record.name = kwargs["name"]
            mock_record.content = kwargs["content"]
            mock_record.type = kwargs["type"]
            return mock_record

        self.mock_client.zones.dns_records.create.side_effect = create_side_effect

        # Mock update operation for cf2
        update_result = Mock()
        update_result.id = "existing_cf2"
        update_result.name = "cf2.example.com"
        update_result.content = "192.168.1.2"  # Updated
        update_result.type = "A"
        self.mock_client.zones.dns_records.update.return_value = update_result

        # Execute batch upsert
        records = self.dns_manager.batch_upsert_records(
            zone_id=self.zone_id, base_name="cf", ip_addresses=ip_addresses
        )

        assert len(records) == 3

        # Verify operations
        assert self.mock_client.zones.dns_records.create.call_count == 2  # cf1, cf3
        assert self.mock_client.zones.dns_records.update.call_count == 1  # cf2

    def test_batch_operations_with_partial_failures(self):
        """Test batch operations with some failures."""
        ip_addresses = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]

        # Mock no existing records
        empty_result = Mock()
        empty_result.result = []
        self.mock_client.zones.dns_records.list.return_value = empty_result

        # Mock create operations with failure on second record
        def create_side_effect(**kwargs):
            if "cf2" in kwargs["name"]:
                mock_response = Mock()
                mock_response.status_code = 400
                raise cloudflare.BadRequestError(
                    message="Invalid record",
                    response=mock_response,
                    body={"errors": [{"code": 81053, "message": "Invalid record"}]},
                )

            mock_record = Mock()
            mock_record.id = f"new_{kwargs['name']}"
            mock_record.name = kwargs["name"]
            mock_record.content = kwargs["content"]
            mock_record.type = kwargs["type"]
            return mock_record

        self.mock_client.zones.dns_records.create.side_effect = create_side_effect

        # Execute batch upsert (should handle partial failures)
        records = self.dns_manager.batch_upsert_records(
            zone_id=self.zone_id, base_name="cf", ip_addresses=ip_addresses
        )

        # Should have 2 successful records (cf1, cf3)
        assert len(records) == 2
        assert self.mock_client.zones.dns_records.create.call_count == 3  # All attempted

    def test_batch_delete_by_prefix(self):
        """Test batch deletion by prefix."""
        # Mock existing records with prefix
        existing_records = [
            Mock(id="cf1_id", name="cf1.example.com", content="1.1.1.1", type="A"),
            Mock(id="cf2_id", name="cf2.example.com", content="1.0.0.1", type="A"),
            Mock(id="other_id", name="other.example.com", content="8.8.8.8", type="A"),
        ]

        mock_result = Mock()
        mock_result.result = existing_records
        self.mock_client.zones.dns_records.list.return_value = mock_result

        # Mock successful deletions
        delete_result = Mock()
        delete_result.id = "deleted"
        self.mock_client.zones.dns_records.delete.return_value = delete_result

        # Execute batch delete
        deleted_count = self.dns_manager.batch_delete_records_by_prefix(self.zone_id, "cf")

        assert deleted_count == 2  # Only cf1 and cf2 should be deleted
        assert self.mock_client.zones.dns_records.delete.call_count == 2

        # Verify correct records were deleted
        delete_calls = self.mock_client.zones.dns_records.delete.call_args_list
        deleted_ids = [call[1]["dns_record_id"] for call in delete_calls]
        assert "cf1_id" in deleted_ids
        assert "cf2_id" in deleted_ids
        assert "other_id" not in deleted_ids


class TestCloudFlareErrorHandling:
    """Test CloudFlare API error handling and recovery."""

    def setup_method(self):
        """Set up test environment."""
        self.config = Config(cloudflare_api_token="test_token")
        self.config._skip_validation = True
        self.dns_manager = DNSManager(self.config)

        # Mock authenticated client
        self.mock_client = Mock()
        self.dns_manager.client = self.mock_client

    def test_api_error_types_handling(self):
        """Test handling of different CloudFlare API error types."""
        error_scenarios = [
            {
                "exception": cloudflare.BadRequestError,
                "status_code": 400,
                "message": "Bad request",
                "expected_error": DNSError,
            },
            {
                "exception": cloudflare.NotFoundError,
                "status_code": 404,
                "message": "Not found",
                "expected_error": DNSError,
            },
            {
                "exception": cloudflare.RateLimitError,
                "status_code": 429,
                "message": "Rate limit exceeded",
                "expected_error": DNSError,
            },
            {
                "exception": cloudflare.InternalServerError,
                "status_code": 500,
                "message": "Internal server error",
                "expected_error": DNSError,
            },
        ]

        for scenario in error_scenarios:
            mock_response = Mock()
            mock_response.status_code = scenario["status_code"]

            self.mock_client.zones.list.side_effect = scenario["exception"](
                message=scenario["message"],
                response=mock_response,
                body={"errors": [{"code": 1000, "message": scenario["message"]}]},
            )

            with pytest.raises(scenario["expected_error"]):
                self.dns_manager.get_zone_id("example.com")

            # Reset for next scenario
            self.mock_client.reset_mock()

    def test_retry_logic_on_transient_errors(self):
        """Test retry logic for transient errors."""
        # Mock transient error followed by success
        mock_response = Mock()
        mock_response.status_code = 500

        transient_error = cloudflare.InternalServerError(
            message="Temporary server error",
            response=mock_response,
            body={"errors": [{"code": 1000, "message": "Temporary error"}]},
        )

        mock_zone = Mock()
        mock_zone.id = "zone123"
        mock_zone.name = "example.com"
        mock_zones = Mock()
        mock_zones.result = [mock_zone]

        # First call fails, second succeeds
        self.mock_client.zones.list.side_effect = [transient_error, mock_zones]

        with patch("time.sleep"):  # Speed up test
            zone_id = self.dns_manager.get_zone_id("example.com")

        assert zone_id == "zone123"
        assert self.mock_client.zones.list.call_count == 2

    def test_timeout_handling(self):
        """Test handling of request timeouts."""
        import requests

        # Mock timeout error
        self.mock_client.zones.list.side_effect = requests.Timeout("Request timeout")

        with pytest.raises(DNSError, match="timeout"):
            self.dns_manager.get_zone_id("example.com")

    def test_connection_error_handling(self):
        """Test handling of connection errors."""
        import requests

        # Mock connection error
        self.mock_client.zones.list.side_effect = requests.ConnectionError("Connection failed")

        with pytest.raises(DNSError, match="connection"):
            self.dns_manager.get_zone_id("example.com")


if __name__ == "__main__":
    pytest.main([__file__])
