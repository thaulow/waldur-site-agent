"""Tests for NScale backend implementation."""

import pytest
from unittest.mock import MagicMock, patch

from waldur_site_agent.backend.exceptions import BackendError
from waldur_site_agent_nscale.backend import NscaleBackend
from waldur_site_agent_nscale.exceptions import NscaleAPIError

from .conftest import SAMPLE_CLUSTER, SAMPLE_INSTANCE


class TestNscaleBackendInit:
    """Test cases for NscaleBackend initialization."""

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_initialization(self, mock_client_class, nscale_settings, nscale_components):
        backend = NscaleBackend(nscale_settings, nscale_components)

        assert backend.backend_type == "nscale"
        assert backend.resource_prefix == "waldur_"
        assert backend.instance_type == "g-4-standard"
        assert backend.image_id == "ubuntu-22.04"
        assert backend.network_id == "net-test-789"
        assert backend.security_group_ids == ["sg-default", "sg-ssh"]
        mock_client_class.assert_called_once_with(
            api_url="https://compute.nks.example.com",
            organization_id="org-test-123",
            project_id="proj-test-456",
            service_token="test-token-abc",
            identity_api_url="https://identity.nks.example.com",
        )

    def test_initialization_missing_setting(self, nscale_components):
        settings = {"api_url": "https://compute.nks.example.com"}
        with pytest.raises(ValueError, match="Missing required setting"):
            NscaleBackend(settings, nscale_components)

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_initialization_defaults(self, mock_client_class, nscale_components):
        minimal_settings = {
            "api_url": "https://compute.nks.example.com",
            "organization_id": "org-1",
            "project_id": "proj-1",
            "service_token": "token-1",
        }
        backend = NscaleBackend(minimal_settings, nscale_components)

        assert backend.resource_prefix == "waldur_"
        assert backend.instance_type == "standard"
        assert backend.image_id == ""
        assert backend.network_id == ""
        assert backend.security_group_ids == []
        assert backend.resource_type == "instance"

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_supports_decreasing_usage(self, mock_client_class, nscale_settings, nscale_components):
        backend = NscaleBackend(nscale_settings, nscale_components)
        assert backend.supports_decreasing_usage is True

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_resource_type_cluster(self, mock_client_class, nscale_components):
        settings = {
            "api_url": "https://compute.nks.example.com",
            "organization_id": "org-1",
            "project_id": "proj-1",
            "service_token": "token-1",
            "resource_type": "cluster",
        }
        backend = NscaleBackend(settings, nscale_components)
        assert backend.resource_type == "cluster"


class TestNscaleBackendPing:
    """Test cases for ping and diagnostics."""

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_ping_success(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client.get_networks.return_value = [{"id": "net-1"}]
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        assert backend.ping() is True
        mock_client.get_networks.assert_called_once()

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_ping_failure(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client.get_networks.side_effect = NscaleAPIError("Connection refused")
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        assert backend.ping() is False

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_ping_raise_exception(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client.get_networks.side_effect = NscaleAPIError("Connection refused")
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        with pytest.raises(BackendError, match="Nscale backend not available"):
            backend.ping(raise_exception=True)

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_diagnostics_success(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client.get_networks.return_value = [{"id": "net-1"}]
        mock_client.get_compute_instances.return_value = [SAMPLE_INSTANCE]
        mock_client.get_compute_clusters.return_value = []
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        assert backend.diagnostics() is True

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_diagnostics_failure(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client.get_networks.side_effect = Exception("API error")
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        assert backend.diagnostics() is False


class TestNscaleBackendLifecycle:
    """Test cases for resource lifecycle operations."""

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_pause_resource(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        result = backend.pause_resource("inst-001")

        assert result is True
        mock_client.stop_instance.assert_called_once_with("inst-001")

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_pause_resource_failure(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client.stop_instance.side_effect = NscaleAPIError("Instance not found")
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        result = backend.pause_resource("inst-missing")

        assert result is False

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_downscale_resource(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        result = backend.downscale_resource("inst-001")

        assert result is True
        mock_client.stop_instance.assert_called_once_with("inst-001")

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_restore_resource(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        result = backend.restore_resource("inst-001")

        assert result is True
        mock_client.start_instance.assert_called_once_with("inst-001")

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_restore_resource_failure(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client.start_instance.side_effect = NscaleAPIError("Instance not found")
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        result = backend.restore_resource("inst-missing")

        assert result is False


class TestNscaleBackendUsage:
    """Test cases for usage reporting."""

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_get_usage_report(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client.get_compute_instance.return_value = SAMPLE_INSTANCE
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        report = backend._get_usage_report(["inst-001"])

        assert "inst-001" in report
        usage = report["inst-001"]["TOTAL_ACCOUNT_USAGE"]
        assert usage["cpu"] == 4
        assert usage["memory"] == 8
        assert usage["storage"] == 100
        assert usage["gpu"] == 0

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_get_usage_report_with_unit_factor(
        self, mock_client_class, nscale_settings, nscale_components
    ):
        nscale_components["memory"]["unit_factor"] = 1024
        mock_client = MagicMock()
        instance_with_backend_values = {
            "metadata": {"id": "inst-001"},
            "spec": {"cpu": 4, "memory": 8192, "storage": 100},
        }
        mock_client.get_compute_instance.return_value = instance_with_backend_values
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        report = backend._get_usage_report(["inst-001"])

        usage = report["inst-001"]["TOTAL_ACCOUNT_USAGE"]
        assert usage["cpu"] == 4
        assert usage["memory"] == 8  # 8192 // 1024 = 8
        assert usage["storage"] == 100

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_get_usage_report_failure(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client.get_compute_instance.side_effect = NscaleAPIError("Not found")
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        report = backend._get_usage_report(["inst-missing"])

        assert "inst-missing" in report
        usage = report["inst-missing"]["TOTAL_ACCOUNT_USAGE"]
        assert all(v == 0 for v in usage.values())


class TestNscaleBackendMetadata:
    """Test cases for resource metadata."""

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_get_resource_metadata(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client.get_compute_instance.return_value = SAMPLE_INSTANCE
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        metadata = backend.get_resource_metadata("inst-001")

        assert metadata["instance_id"] == "inst-001"
        assert metadata["instance_name"] == "test-instance"
        assert metadata["flavor_id"] == "g-4-standard"
        assert metadata["power_state"] == "running"
        assert metadata["provisioning_status"] == "provisioned"
        assert metadata["cpu"] == 4
        assert metadata["memory"] == 8
        assert metadata["storage"] == 100

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_get_resource_metadata_failure(
        self, mock_client_class, nscale_settings, nscale_components
    ):
        mock_client = MagicMock()
        mock_client.get_compute_instance.side_effect = NscaleAPIError("Not found")
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        metadata = backend.get_resource_metadata("inst-missing")

        assert metadata == {}


class TestNscaleBackendCreateResource:
    """Test cases for resource creation."""

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_create_backend_resource(self, mock_client_class, nscale_settings, nscale_components):
        mock_client = MagicMock()
        mock_client.get_resource.return_value = None
        mock_client.create_compute_instance.return_value = SAMPLE_INSTANCE
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        result = backend._create_backend_resource("inst-new", "New Resource", "org-1")

        assert result is True
        mock_client.create_compute_instance.assert_called_once()
        call_data = mock_client.create_compute_instance.call_args[0][0]
        assert call_data["metadata"]["name"] == "inst-new"
        assert call_data["spec"]["flavorId"] == "g-4-standard"
        assert call_data["spec"]["imageId"] == "ubuntu-22.04"
        assert call_data["spec"]["networking"]["networkId"] == "net-test-789"

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_create_backend_resource_already_exists(
        self, mock_client_class, nscale_settings, nscale_components
    ):
        mock_client = MagicMock()
        mock_client.get_resource.return_value = MagicMock()
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        result = backend._create_backend_resource("inst-existing", "Existing", "org-1")

        assert result is True
        mock_client.create_compute_instance.assert_not_called()

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_create_backend_resource_api_error(
        self, mock_client_class, nscale_settings, nscale_components
    ):
        mock_client = MagicMock()
        mock_client.get_resource.return_value = None
        mock_client.create_compute_instance.side_effect = NscaleAPIError("Quota exceeded")
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(nscale_settings, nscale_components)
        with pytest.raises(BackendError, match="Failed to create compute instance"):
            backend._create_backend_resource("inst-fail", "Fail Resource", "org-1")

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_create_cluster_resource(self, mock_client_class, nscale_components):
        settings = {
            "api_url": "https://compute.nks.example.com",
            "organization_id": "org-1",
            "project_id": "proj-1",
            "service_token": "token-1",
            "resource_type": "cluster",
        }
        mock_client = MagicMock()
        mock_client.get_resource.return_value = None
        mock_client.create_compute_cluster.return_value = SAMPLE_CLUSTER
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(settings, nscale_components)
        result = backend._create_backend_resource("cluster-new", "New Cluster", "org-1")

        assert result is True
        mock_client.create_compute_cluster.assert_called_once()
        mock_client.create_compute_instance.assert_not_called()

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_create_cluster_resource_api_error(self, mock_client_class, nscale_components):
        settings = {
            "api_url": "https://compute.nks.example.com",
            "organization_id": "org-1",
            "project_id": "proj-1",
            "service_token": "token-1",
            "resource_type": "cluster",
        }
        mock_client = MagicMock()
        mock_client.get_resource.return_value = None
        mock_client.create_compute_cluster.side_effect = NscaleAPIError("Quota exceeded")
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(settings, nscale_components)
        with pytest.raises(BackendError, match="Failed to create cluster"):
            backend._create_backend_resource("cluster-fail", "Fail Cluster", "org-1")


class TestNscaleBackendDeleteResource:
    """Test cases for resource deletion."""

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_delete_cluster_resource(self, mock_client_class, nscale_components):
        settings = {
            "api_url": "https://compute.nks.example.com",
            "organization_id": "org-1",
            "project_id": "proj-1",
            "service_token": "token-1",
            "resource_type": "cluster",
        }
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(settings, nscale_components)
        waldur_res = MagicMock()
        waldur_res.backend_id = "cluster-001"

        backend.delete_resource(waldur_res)

        mock_client.delete_compute_cluster.assert_called_once_with("cluster-001")

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_delete_cluster_resource_empty_backend_id(self, mock_client_class, nscale_components):
        settings = {
            "api_url": "https://compute.nks.example.com",
            "organization_id": "org-1",
            "project_id": "proj-1",
            "service_token": "token-1",
            "resource_type": "cluster",
        }
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        backend = NscaleBackend(settings, nscale_components)
        waldur_res = MagicMock()
        waldur_res.backend_id = "  "

        backend.delete_resource(waldur_res)

        mock_client.delete_compute_cluster.assert_not_called()


class TestNscaleBackendLimits:
    """Test cases for resource limits."""

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_collect_resource_limits(
        self, mock_client_class, nscale_settings, nscale_components, waldur_resource
    ):
        mock_client_class.return_value = MagicMock()
        backend = NscaleBackend(nscale_settings, nscale_components)

        nscale_limits, waldur_limits = backend._collect_resource_limits(waldur_resource)

        assert nscale_limits["cpu"] == 4
        assert nscale_limits["memory"] == 8
        assert nscale_limits["storage"] == 100
        assert nscale_limits["gpu"] == 1
        assert waldur_limits["cpu"] == 4
        assert waldur_limits["memory"] == 8

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_collect_resource_limits_with_unit_factor(
        self, mock_client_class, nscale_components, waldur_resource
    ):
        nscale_components["memory"]["unit_factor"] = 1024
        settings = {
            "api_url": "https://compute.nks.example.com",
            "organization_id": "org-1",
            "project_id": "proj-1",
            "service_token": "token-1",
        }
        mock_client_class.return_value = MagicMock()
        backend = NscaleBackend(settings, nscale_components)

        nscale_limits, waldur_limits = backend._collect_resource_limits(waldur_resource)

        assert nscale_limits["memory"] == 8 * 1024
        assert waldur_limits["memory"] == 8

    @patch("waldur_site_agent_nscale.backend.NscaleClient")
    def test_list_components(self, mock_client_class, nscale_settings, nscale_components):
        mock_client_class.return_value = MagicMock()
        backend = NscaleBackend(nscale_settings, nscale_components)

        components = backend.list_components()

        assert set(components) == {"cpu", "memory", "storage", "gpu"}
