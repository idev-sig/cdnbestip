"""Unit tests for workflow orchestration."""

from io import StringIO
from unittest.mock import MagicMock, mock_open, patch

import pytest

from cdnbestip.cli import WorkflowOrchestrator
from cdnbestip.config import Config
from cdnbestip.models import SpeedTestResult


class TestWorkflowOrchestrator:
    """Test workflow orchestration functionality."""

    def create_config(self, **kwargs):
        """Helper to create test configuration."""
        defaults = {
            "domain": "example.com",
            "prefix": "cf",
            "zone_type": "A",
            "speed_threshold": 2.0,
            "quantity": 0,
            "refresh": False,
            "update_dns": False,
            "only_one": False,
            "ip_data_url": "cf",
            "cloudflare_api_token": None,
            "cloudflare_api_key": None,
            "cloudflare_account": None,
        }
        defaults.update(kwargs)

        # Add credentials if DNS update is enabled
        if defaults.get("update_dns", False) and not defaults.get("cloudflare_api_token"):
            defaults["cloudflare_api_token"] = "test_token"

        config = Config(**defaults)
        config._skip_validation = True
        return config

    def create_sample_results(self):
        """Create sample speed test results for testing."""
        return [
            SpeedTestResult(
                ip="1.1.1.1",
                port=443,
                data_center="LAX",
                region="US-West",
                city="Los Angeles",
                speed=5.2,
                latency=15.3,
            ),
            SpeedTestResult(
                ip="1.0.0.1",
                port=443,
                data_center="SJC",
                region="US-West",
                city="San Jose",
                speed=4.8,
                latency=12.1,
            ),
            SpeedTestResult(
                ip="8.8.8.8",
                port=443,
                data_center="NYC",
                region="US-East",
                city="New York",
                speed=3.1,
                latency=25.7,
            ),
        ]

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    @patch("builtins.open", new_callable=mock_open, read_data="1.1.1.1\n1.0.0.1\n8.8.8.8\n")
    @patch("os.path.exists")
    def test_prepare_ip_data_new_download(
        self,
        mock_exists,
        mock_file,
        mock_results_handler,
        mock_speedtest_manager,
        mock_ip_source_manager,
    ):
        """Test IP data preparation with new download."""
        # Setup
        config = self.create_config(refresh=True)
        workflow = WorkflowOrchestrator(config)

        # When refresh=True, force_refresh is always True regardless of file existence
        # But we still need to mock the verification check after download
        mock_exists.side_effect = [True]  # Only the verification check after download
        mock_ip_manager = mock_ip_source_manager.return_value

        # Execute
        ip_file = workflow._prepare_ip_data()

        # Verify
        assert ip_file == "ip_list.txt"
        mock_ip_manager.download_ip_list.assert_called_once_with(
            "cf", "ip_list.txt", force_refresh=True
        )

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    @patch("builtins.open", new_callable=mock_open, read_data="1.1.1.1\n1.0.0.1\n8.8.8.8\n")
    @patch("os.path.exists")
    def test_prepare_ip_data_existing_file(
        self,
        mock_exists,
        mock_file,
        mock_results_handler,
        mock_speedtest_manager,
        mock_ip_source_manager,
    ):
        """Test IP data preparation with existing file."""
        # Setup
        config = self.create_config(refresh=False)
        workflow = WorkflowOrchestrator(config)

        mock_exists.return_value = True
        mock_ip_manager = mock_ip_source_manager.return_value

        # Execute
        ip_file = workflow._prepare_ip_data()

        # Verify
        assert ip_file == "ip_list.txt"
        mock_ip_manager.download_ip_list.assert_not_called()

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    def test_run_speed_test_new_execution(
        self, mock_results_handler, mock_speedtest_manager, mock_ip_source_manager
    ):
        """Test speed test execution with new run."""
        # Setup
        config = self.create_config(refresh=True)
        workflow = WorkflowOrchestrator(config)

        mock_st_manager = mock_speedtest_manager.return_value
        mock_st_manager.should_refresh_results.return_value = True
        mock_st_manager.ensure_binary_available.return_value = "/path/to/cfst"
        mock_st_manager.run_speed_test.return_value = "result.csv"

        # Execute
        results_file = workflow._run_speed_test("ip_list.txt")

        # Verify
        assert results_file == "result.csv"
        mock_st_manager.ensure_binary_available.assert_called_once()
        mock_st_manager.run_speed_test.assert_called_once_with("ip_list.txt", "result.csv")

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    def test_run_speed_test_existing_results(
        self, mock_results_handler, mock_speedtest_manager, mock_ip_source_manager
    ):
        """Test speed test with existing results."""
        # Setup
        config = self.create_config(refresh=False)
        workflow = WorkflowOrchestrator(config)

        mock_st_manager = mock_speedtest_manager.return_value
        mock_st_manager.should_refresh_results.return_value = False

        # Execute
        results_file = workflow._run_speed_test("ip_list.txt")

        # Verify
        assert results_file == "result.csv"
        mock_st_manager.ensure_binary_available.assert_not_called()
        mock_st_manager.run_speed_test.assert_not_called()

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    def test_process_results_success(
        self, mock_results_handler, mock_speedtest_manager, mock_ip_source_manager
    ):
        """Test successful results processing."""
        # Setup
        config = self.create_config(speed_threshold=3.0, quantity=2)
        workflow = WorkflowOrchestrator(config)

        sample_results = self.create_sample_results()

        mock_st_manager = mock_speedtest_manager.return_value
        mock_st_manager.parse_results.return_value = sample_results
        mock_st_manager.validate_results.return_value = sample_results

        mock_rh = mock_results_handler.return_value
        mock_rh.filter_by_speed.return_value = sample_results[:2]  # First 2 results above threshold
        mock_rh.get_top_results.return_value = sample_results[:2]

        # Execute
        results = workflow._process_results("result.csv")

        # Verify
        assert len(results) == 2
        mock_st_manager.parse_results.assert_called_once_with("result.csv")
        mock_rh.filter_by_speed.assert_called_once_with(sample_results, 3.0)
        mock_rh.get_top_results.assert_called_once_with(sample_results[:2], 2)

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    def test_process_results_only_one_mode(
        self, mock_results_handler, mock_speedtest_manager, mock_ip_source_manager
    ):
        """Test results processing in only-one mode."""
        # Setup
        config = self.create_config(only_one=True)
        workflow = WorkflowOrchestrator(config)

        sample_results = self.create_sample_results()

        mock_st_manager = mock_speedtest_manager.return_value
        mock_st_manager.parse_results.return_value = sample_results
        mock_st_manager.validate_results.return_value = sample_results

        mock_rh = mock_results_handler.return_value
        mock_rh.filter_by_speed.return_value = sample_results

        # Execute
        results = workflow._process_results("result.csv")

        # Verify
        assert len(results) == 1  # Only one result in only-one mode

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    @patch("cdnbestip.cli.DNSManager")
    def test_update_dns_records_single_record(
        self,
        mock_dns_manager_class,
        mock_results_handler,
        mock_speedtest_manager,
        mock_ip_source_manager,
    ):
        """Test DNS update with single record."""
        # Setup
        config = self.create_config(
            update_dns=True, only_one=True, cloudflare_api_token="test_token"
        )
        workflow = WorkflowOrchestrator(config)

        sample_results = self.create_sample_results()[:1]

        mock_dns_manager = mock_dns_manager_class.return_value
        mock_dns_manager.get_zone_id.return_value = "zone123"
        mock_dns_record = MagicMock()
        mock_dns_record.name = "cf.example.com"
        mock_dns_record.content = "1.1.1.1"
        mock_dns_manager.upsert_record.return_value = mock_dns_record

        # Execute
        workflow._update_dns_records(sample_results)

        # Verify
        mock_dns_manager.authenticate.assert_called_once()
        mock_dns_manager.get_zone_id.assert_called_once_with("example.com")
        mock_dns_manager.upsert_record.assert_called_once_with(
            zone_id="zone123", name="cf.example.com", content="1.1.1.1", record_type="A"
        )

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    @patch("cdnbestip.cli.DNSManager")
    def test_update_dns_records_batch_records(
        self,
        mock_dns_manager_class,
        mock_results_handler,
        mock_speedtest_manager,
        mock_ip_source_manager,
    ):
        """Test DNS update with batch records."""
        # Setup
        config = self.create_config(
            update_dns=True, only_one=False, cloudflare_api_token="test_token"
        )
        workflow = WorkflowOrchestrator(config)

        sample_results = self.create_sample_results()

        mock_dns_manager = mock_dns_manager_class.return_value
        mock_dns_manager.get_zone_id.return_value = "zone123"
        mock_dns_records = [MagicMock() for _ in range(3)]
        mock_dns_manager.batch_upsert_records.return_value = mock_dns_records

        # Execute
        workflow._update_dns_records(sample_results)

        # Verify
        mock_dns_manager.authenticate.assert_called_once()
        mock_dns_manager.get_zone_id.assert_called_once_with("example.com")
        mock_dns_manager.batch_upsert_records.assert_called_once_with(
            zone_id="zone123",
            base_name="cf",
            ip_addresses=["1.1.1.1", "1.0.0.1", "8.8.8.8"],
            record_type="A",
        )

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    def test_update_dns_records_no_results(
        self, mock_results_handler, mock_speedtest_manager, mock_ip_source_manager
    ):
        """Test DNS update with no results."""
        # Setup
        config = self.create_config(update_dns=True)
        workflow = WorkflowOrchestrator(config)

        # Execute (should not raise exception)
        workflow._update_dns_records([])

        # No DNS manager should be created since no results
        assert (
            workflow.dns_manager is not None
        )  # DNS manager is created in __init__ when update_dns=True

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    @patch("sys.stdout", new_callable=StringIO)
    def test_display_summary_with_results(
        self, mock_stdout, mock_results_handler, mock_speedtest_manager, mock_ip_source_manager
    ):
        """Test summary display with results."""
        # Setup
        config = self.create_config()
        workflow = WorkflowOrchestrator(config)

        sample_results = self.create_sample_results()

        mock_rh = mock_results_handler.return_value
        mock_rh.get_performance_summary.return_value = {
            "total_results": 3,
            "results_above_threshold": 2,
            "avg_speed": 4.37,
            "max_speed": 5.2,
            "min_speed": 3.1,
            "avg_latency": 17.7,
            "min_latency": 12.1,
            "max_latency": 25.7,
        }

        # Execute
        workflow._display_summary(sample_results)

        # Verify
        output = mock_stdout.getvalue()
        assert "WORKFLOW SUMMARY" in output
        assert "Performance Results" in output
        assert "Best Result" in output
        assert "1.1.1.1" in output  # Best IP
        assert "5.2" in output  # Best speed

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    @patch("sys.stdout", new_callable=StringIO)
    def test_display_summary_no_results(
        self, mock_stdout, mock_results_handler, mock_speedtest_manager, mock_ip_source_manager
    ):
        """Test summary display with no results."""
        # Setup
        config = self.create_config()
        workflow = WorkflowOrchestrator(config)

        # Execute
        workflow._display_summary([])

        # Verify
        output = mock_stdout.getvalue()
        assert "WORKFLOW SUMMARY" in output
        assert "No results met the performance criteria" in output

    @patch("cdnbestip.cli.WorkflowOrchestrator._prepare_ip_data")
    @patch("cdnbestip.cli.WorkflowOrchestrator._run_speed_test")
    @patch("cdnbestip.cli.WorkflowOrchestrator._process_results")
    @patch("cdnbestip.cli.WorkflowOrchestrator._display_summary")
    def test_execute_workflow_speed_test_only(
        self, mock_display_summary, mock_process_results, mock_run_speed_test, mock_prepare_ip_data
    ):
        """Test complete workflow execution for speed test only."""
        # Setup
        config = self.create_config(update_dns=False)
        workflow = WorkflowOrchestrator(config)

        mock_prepare_ip_data.return_value = "ip_list.txt"
        mock_run_speed_test.return_value = "result.csv"
        mock_process_results.return_value = self.create_sample_results()

        # Execute
        workflow.execute()

        # Verify
        mock_prepare_ip_data.assert_called_once()
        mock_run_speed_test.assert_called_once_with("ip_list.txt")
        mock_process_results.assert_called_once_with("result.csv")
        mock_display_summary.assert_called_once()

    @patch("cdnbestip.cli.WorkflowOrchestrator._prepare_ip_data")
    @patch("cdnbestip.cli.WorkflowOrchestrator._run_speed_test")
    @patch("cdnbestip.cli.WorkflowOrchestrator._process_results")
    @patch("cdnbestip.cli.WorkflowOrchestrator._update_dns_records")
    @patch("cdnbestip.cli.WorkflowOrchestrator._display_summary")
    def test_execute_workflow_with_dns_update(
        self,
        mock_display_summary,
        mock_update_dns_records,
        mock_process_results,
        mock_run_speed_test,
        mock_prepare_ip_data,
    ):
        """Test complete workflow execution with DNS update."""
        # Setup
        config = self.create_config(update_dns=True)
        workflow = WorkflowOrchestrator(config)

        mock_prepare_ip_data.return_value = "ip_list.txt"
        mock_run_speed_test.return_value = "result.csv"
        sample_results = self.create_sample_results()
        mock_process_results.return_value = sample_results

        # Execute
        workflow.execute()

        # Verify
        mock_prepare_ip_data.assert_called_once()
        mock_run_speed_test.assert_called_once_with("ip_list.txt")
        mock_process_results.assert_called_once_with("result.csv")
        mock_update_dns_records.assert_called_once_with(sample_results)
        mock_display_summary.assert_called_once()

    def test_workflow_error_handling(self):
        """Test workflow error handling."""
        # Setup
        config = self.create_config()
        workflow = WorkflowOrchestrator(config)

        # Mock a method to raise an exception
        with patch.object(workflow, "_prepare_ip_data", side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                workflow.execute()


class TestWorkflowIntegration:
    """Integration tests for workflow components."""

    @patch("cdnbestip.cli.IPSourceManager")
    @patch("cdnbestip.cli.SpeedTestManager")
    @patch("cdnbestip.cli.ResultsHandler")
    @patch("cdnbestip.cli.DNSManager")
    def test_workflow_initialization(
        self,
        mock_dns_manager_class,
        mock_results_handler_class,
        mock_speedtest_manager_class,
        mock_ip_source_manager_class,
    ):
        """Test workflow orchestrator initialization."""
        # Test without DNS update
        config = Config(update_dns=False)
        config._skip_validation = True

        workflow = WorkflowOrchestrator(config)

        assert workflow.config == config
        assert workflow.dns_manager is None
        mock_speedtest_manager_class.assert_called_once_with(config)
        mock_results_handler_class.assert_called_once_with(config)
        mock_ip_source_manager_class.assert_called_once_with(config)

        # Test with DNS update
        config = Config(
            update_dns=True, cloudflare_api_token="test_token", domain="example.com", prefix="cf"
        )
        config._skip_validation = True

        workflow = WorkflowOrchestrator(config)

        assert workflow.dns_manager is not None
        mock_dns_manager_class.assert_called_with(config)
