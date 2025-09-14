"""
Unit tests for DNS record attribute handling with missing CloudFlare API attributes.

This module tests the robustness of DNS operations when CloudFlare API response
objects lack certain attributes like zone_id, zone_name, etc.
"""

from unittest.mock import Mock, patch

import pytest

from cdnbestip.config import Config
from cdnbestip.dns import DNSManager
from cdnbestip.exceptions import AuthenticationError


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
            record.zone_id = self.zone_id
            record.zone_name = "example.com"
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
        # Create minimal mock record and explicitly remove attributes
        mock_record = Mock()
        mock_record.content = "192.168.1.100"

        # Delete all other attributes to simulate they don't exist
        del mock_record.id
        del mock_record.zone_id
        del mock_record.zone_name
        del mock_record.name
        del mock_record.type
        del mock_record.ttl
        del mock_record.proxied

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

    def test_upsert_record_with_missing_attributes_create_path(self):
        """Test upsert_record create path when list_records returns records with missing attributes."""
        # Mock list_records to return no existing records (triggers create path)
        with patch.object(self.dns_manager, "list_records") as mock_list:
            mock_list.return_value = []

            # Mock create_record
            with patch.object(self.dns_manager, "create_record") as mock_create:
                mock_record = Mock()
                mock_record.id = "created_record"
                mock_record.zone_id = self.zone_id
                mock_record.zone_name = None  # Simulate missing zone_name
                mock_create.return_value = mock_record

                record = self.dns_manager.upsert_record(
                    zone_id=self.zone_id, name="new.example.com", content="192.168.1.200"
                )

                assert record.id == "created_record"
                mock_create.assert_called_once()

    def test_upsert_record_with_missing_attributes_update_path(self):
        """Test upsert_record update path when existing records have missing attributes."""
        from cdnbestip.models import DNSRecord

        # Mock existing record with missing zone_name
        existing_record = DNSRecord(
            id="existing_record",
            zone_id=self.zone_id,
            zone_name=None,  # Missing zone_name
            name="existing.example.com",
            content="192.168.1.5",
            type="A",
        )

        # Mock list_records to return existing record
        with patch.object(self.dns_manager, "list_records") as mock_list:
            mock_list.return_value = [existing_record]

            # Mock update_record
            with patch.object(self.dns_manager, "update_record") as mock_update:
                updated_record = Mock()
                updated_record.id = "existing_record"
                updated_record.content = "192.168.1.6"
                mock_update.return_value = updated_record

                record = self.dns_manager.upsert_record(
                    zone_id=self.zone_id, name="existing.example.com", content="192.168.1.6"
                )

                assert record.id == "existing_record"
                mock_update.assert_called_once_with(
                    zone_id=self.zone_id,
                    record_id="existing_record",
                    content="192.168.1.6",
                    proxied=False,
                    ttl=1,
                )

    def test_error_handling_with_missing_attributes(self):
        """Test that error handling still works when attributes are missing."""
        # Mock record with missing attributes
        mock_record = Mock()
        mock_record.content = "192.168.1.1"
        # Simulate missing most attributes including id
        del mock_record.id

        mock_response = Mock()
        mock_response.result = [mock_record]
        self.dns_manager.client.dns.records.list.return_value = mock_response

        # Should handle the missing attributes gracefully
        records = self.dns_manager.list_records(self.zone_id)

        assert len(records) == 1
        record = records[0]
        assert record.id is None  # Fallback for missing id
        assert record.content == "192.168.1.1"  # Original value preserved

    def test_authentication_check_still_works(self):
        """Test that authentication checks still work with attribute handling."""
        # Set client to None to simulate not authenticated
        self.dns_manager.client = None

        with pytest.raises(AuthenticationError):
            self.dns_manager.list_records(self.zone_id)

        with pytest.raises(AuthenticationError):
            self.dns_manager.create_record(
                zone_id=self.zone_id, name="test.example.com", content="192.168.1.1"
            )

        with pytest.raises(AuthenticationError):
            self.dns_manager.update_record(
                zone_id=self.zone_id, record_id="test_record", content="192.168.1.2"
            )
