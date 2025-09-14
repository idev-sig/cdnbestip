"""Unit tests for IP data source management."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cdnbestip.config import Config
from cdnbestip.exceptions import IPSourceError
from cdnbestip.ip_sources import IPSourceManager


class TestIPSourceManager:
    """Test IP data source management functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.manager = IPSourceManager(self.config)

    def test_get_available_sources(self):
        """Test getting list of available IP sources."""
        sources = self.manager.get_available_sources()
        expected_sources = ["cf", "gc", "ct", "aws"]
        assert all(source in sources for source in expected_sources)

    def test_get_source_info_valid_source(self):
        """Test getting information for a valid source."""
        info = self.manager.get_source_info("cf")
        assert info["name"] == "CloudFlare"
        assert info["url"] == "https://www.cloudflare.com/ips-v4"
        assert info["type"] == "text"

    def test_get_source_info_invalid_source(self):
        """Test getting information for an invalid source."""
        with pytest.raises(IPSourceError, match="Unknown IP source"):
            self.manager.get_source_info("invalid")

    def test_process_text_response(self):
        """Test processing plain text response."""
        text_response = "192.168.1.0/24\n192.168.2.0/24\n# Comment\n10.0.0.0/8"
        result = self.manager._process_text_response(text_response)
        expected = ["192.168.1.0/24", "192.168.2.0/24", "10.0.0.0/8"]
        assert result == expected

    def test_process_json_response_simple_array(self):
        """Test processing JSON response with simple array."""
        json_data = {"addresses": ["192.168.1.1", "192.168.1.2"]}
        source_info = {"json_path": "addresses"}
        result = self.manager._process_json_response(json_data, source_info)
        assert result == ["192.168.1.1", "192.168.1.2"]

    def test_process_json_response_object_array(self):
        """Test processing JSON response with object array."""
        json_data = {"prefixes": [{"ip_prefix": "192.168.1.0/24"}, {"ip_prefix": "192.168.2.0/24"}]}
        source_info = {"json_path": "prefixes", "json_field": "ip_prefix"}
        result = self.manager._process_json_response(json_data, source_info)
        assert result == ["192.168.1.0/24", "192.168.2.0/24"]

    @patch("requests.get")
    def test_download_ip_list_text_source(self, mock_get):
        """Test downloading from text source."""
        mock_response = Mock()
        mock_response.text = "192.168.1.0/24\n192.168.2.0/24"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            self.manager.download_ip_list("cf", temp_path, force_refresh=True)
            with open(temp_path) as f:
                content = f.read()
            assert "192.168.1.0/24" in content
            assert "192.168.2.0/24" in content
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_save_ip_list(self):
        """Test saving IP list to file."""
        ip_list = ["192.168.1.0/24", "192.168.2.0/24"]

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            self.manager._save_ip_list(ip_list, temp_path)
            with open(temp_path) as f:
                lines = f.read().strip().split("\n")
            assert lines == ip_list
        finally:
            Path(temp_path).unlink(missing_ok=True)
