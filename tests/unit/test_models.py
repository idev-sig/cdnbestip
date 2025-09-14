"""Unit tests for data models."""

import pytest

from cdnbestip.models import DNSRecord, SpeedTestResult


class TestSpeedTestResult:
    """Test SpeedTestResult data model."""

    def test_speedtest_result_creation(self):
        """Test creating a SpeedTestResult instance."""
        result = SpeedTestResult(
            ip="192.168.1.1",
            port=443,
            data_center="LAX",
            region="US-West",
            city="Los Angeles",
            speed=15.5,
            latency=25.3,
        )

        assert result.ip == "192.168.1.1"
        assert result.port == 443
        assert result.data_center == "LAX"
        assert result.region == "US-West"
        assert result.city == "Los Angeles"
        assert result.speed == 15.5
        assert result.latency == 25.3

    def test_speedtest_result_equality(self):
        """Test SpeedTestResult equality comparison."""
        result1 = SpeedTestResult("1.1.1.1", 443, "LAX", "US", "LA", 10.0, 20.0)
        result2 = SpeedTestResult("1.1.1.1", 443, "LAX", "US", "LA", 10.0, 20.0)
        result3 = SpeedTestResult("1.1.1.2", 443, "LAX", "US", "LA", 10.0, 20.0)

        assert result1 == result2
        assert result1 != result3

    def test_speedtest_result_repr(self):
        """Test SpeedTestResult string representation."""
        result = SpeedTestResult("1.1.1.1", 443, "LAX", "US", "LA", 10.0, 20.0)
        repr_str = repr(result)

        assert "SpeedTestResult" in repr_str
        assert "1.1.1.1" in repr_str
        assert "10.0" in repr_str
        assert "20.0" in repr_str

    def test_speedtest_result_with_zero_values(self):
        """Test SpeedTestResult with zero speed and latency."""
        result = SpeedTestResult("1.1.1.1", 80, "NYC", "US", "NY", 0.0, 0.0)

        assert result.speed == 0.0
        assert result.latency == 0.0

    def test_speedtest_result_with_high_values(self):
        """Test SpeedTestResult with high speed and latency values."""
        result = SpeedTestResult("1.1.1.1", 443, "FRA", "EU", "Frankfurt", 999.9, 1000.0)

        assert result.speed == 999.9
        assert result.latency == 1000.0


class TestDNSRecord:
    """Test DNSRecord data model."""

    def test_dns_record_creation_minimal(self):
        """Test creating a minimal DNSRecord instance."""
        record = DNSRecord()

        assert record.id is None
        assert record.zone_id is None
        assert record.zone_name is None
        assert record.name == ""
        assert record.content == ""
        assert record.type == "A"
        assert record.ttl == 1
        assert record.proxied is False

    def test_dns_record_creation_complete(self):
        """Test creating a complete DNSRecord instance."""
        record = DNSRecord(
            id="record123",
            zone_id="zone456",
            zone_name="example.com",
            name="www.example.com",
            content="192.168.1.1",
            type="A",
            ttl=300,
            proxied=True,
        )

        assert record.id == "record123"
        assert record.zone_id == "zone456"
        assert record.zone_name == "example.com"
        assert record.name == "www.example.com"
        assert record.content == "192.168.1.1"
        assert record.type == "A"
        assert record.ttl == 300
        assert record.proxied is True

    def test_dns_record_equality(self):
        """Test DNSRecord equality comparison."""
        record1 = DNSRecord(id="123", name="test.com", content="1.1.1.1")
        record2 = DNSRecord(id="123", name="test.com", content="1.1.1.1")
        record3 = DNSRecord(id="456", name="test.com", content="1.1.1.1")

        assert record1 == record2
        assert record1 != record3

    def test_dns_record_repr(self):
        """Test DNSRecord string representation."""
        record = DNSRecord(id="123", name="test.example.com", content="192.168.1.1", type="A")
        repr_str = repr(record)

        assert "DNSRecord" in repr_str
        assert "test.example.com" in repr_str
        assert "192.168.1.1" in repr_str

    def test_dns_record_different_types(self):
        """Test DNSRecord with different record types."""
        # A record
        a_record = DNSRecord(name="test.com", content="192.168.1.1", type="A")
        assert a_record.type == "A"

        # AAAA record
        aaaa_record = DNSRecord(name="test.com", content="2001:db8::1", type="AAAA")
        assert aaaa_record.type == "AAAA"

        # CNAME record
        cname_record = DNSRecord(name="www.test.com", content="test.com", type="CNAME")
        assert cname_record.type == "CNAME"

        # MX record
        mx_record = DNSRecord(name="test.com", content="10 mail.test.com", type="MX")
        assert mx_record.type == "MX"

    def test_dns_record_ttl_values(self):
        """Test DNSRecord with different TTL values."""
        # Default TTL
        record1 = DNSRecord()
        assert record1.ttl == 1

        # Custom TTL
        record2 = DNSRecord(ttl=3600)
        assert record2.ttl == 3600

        # Auto TTL (1)
        record3 = DNSRecord(ttl=1)
        assert record3.ttl == 1

    def test_dns_record_proxied_values(self):
        """Test DNSRecord with different proxied values."""
        # Not proxied (default)
        record1 = DNSRecord()
        assert record1.proxied is False

        # Proxied
        record2 = DNSRecord(proxied=True)
        assert record2.proxied is True

        # Explicitly not proxied
        record3 = DNSRecord(proxied=False)
        assert record3.proxied is False

    def test_dns_record_optional_fields(self):
        """Test DNSRecord with optional fields as None."""
        record = DNSRecord(
            name="test.com", content="192.168.1.1", id=None, zone_id=None, zone_name=None
        )

        assert record.id is None
        assert record.zone_id is None
        assert record.zone_name is None
        assert record.name == "test.com"
        assert record.content == "192.168.1.1"


class TestModelInteractions:
    """Test interactions between models."""

    def test_speedtest_result_to_dns_record_conversion(self):
        """Test conceptual conversion from SpeedTestResult to DNSRecord."""
        # This tests the concept of using speed test results to create DNS records
        speed_result = SpeedTestResult(
            ip="192.168.1.1",
            port=443,
            data_center="LAX",
            region="US-West",
            city="Los Angeles",
            speed=15.5,
            latency=25.3,
        )

        # Create DNS record based on speed test result
        dns_record = DNSRecord(
            name="cf1.example.com", content=speed_result.ip, type="A", ttl=1, proxied=False
        )

        assert dns_record.content == speed_result.ip
        assert dns_record.name == "cf1.example.com"
        assert dns_record.type == "A"

    def test_multiple_dns_records_from_speed_results(self):
        """Test creating multiple DNS records from speed test results."""
        speed_results = [
            SpeedTestResult("1.1.1.1", 443, "LAX", "US", "LA", 15.0, 20.0),
            SpeedTestResult("1.0.0.1", 443, "NYC", "US", "NY", 12.0, 25.0),
            SpeedTestResult("8.8.8.8", 443, "SJC", "US", "SJ", 18.0, 15.0),
        ]

        # Create DNS records with prefix
        dns_records = []
        for i, result in enumerate(speed_results, 1):
            record = DNSRecord(name=f"cf{i}.example.com", content=result.ip, type="A")
            dns_records.append(record)

        assert len(dns_records) == 3
        assert dns_records[0].name == "cf1.example.com"
        assert dns_records[0].content == "1.1.1.1"
        assert dns_records[1].name == "cf2.example.com"
        assert dns_records[1].content == "1.0.0.1"
        assert dns_records[2].name == "cf3.example.com"
        assert dns_records[2].content == "8.8.8.8"


class TestModelValidation:
    """Test model validation scenarios."""

    def test_speedtest_result_with_empty_strings(self):
        """Test SpeedTestResult with empty string values."""
        result = SpeedTestResult(
            ip="", port=0, data_center="", region="", city="", speed=0.0, latency=0.0
        )

        # Should still create the object (validation happens elsewhere)
        assert result.ip == ""
        assert result.port == 0
        assert result.data_center == ""

    def test_dns_record_with_empty_strings(self):
        """Test DNSRecord with empty string values."""
        record = DNSRecord(name="", content="", type="")

        # Should still create the object (validation happens elsewhere)
        assert record.name == ""
        assert record.content == ""
        assert record.type == ""

    def test_speedtest_result_negative_values(self):
        """Test SpeedTestResult with negative values."""
        result = SpeedTestResult(
            ip="1.1.1.1",
            port=-1,
            data_center="LAX",
            region="US",
            city="LA",
            speed=-5.0,
            latency=-10.0,
        )

        # Should still create the object (validation happens elsewhere)
        assert result.port == -1
        assert result.speed == -5.0
        assert result.latency == -10.0

    def test_dns_record_negative_ttl(self):
        """Test DNSRecord with negative TTL."""
        record = DNSRecord(ttl=-1)

        # Should still create the object (validation happens elsewhere)
        assert record.ttl == -1


if __name__ == "__main__":
    pytest.main([__file__])
