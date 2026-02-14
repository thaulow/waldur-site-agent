"""Tests for NScale client implementation."""

import pytest
from unittest.mock import MagicMock, patch

from waldur_site_agent.backend.structures import Association, ClientResource
from waldur_site_agent_nscale.client import NscaleClient
from waldur_site_agent_nscale.exceptions import NscaleAPIError

from .conftest import SAMPLE_CLUSTER, SAMPLE_GROUP, SAMPLE_INSTANCE, SAMPLE_NSCALE_USER


class TestNscaleClientInit:
    """Test cases for client initialization."""

    @patch("waldur_site_agent_nscale.client.requests.Session")
    def test_initialization(self, mock_session_class):
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        client = NscaleClient(
            api_url="https://compute.nks.example.com/",
            organization_id="org-1",
            project_id="proj-1",
            service_token="token-abc",
            identity_api_url="https://identity.nks.example.com/",
        )

        assert client.api_url == "https://compute.nks.example.com"
        assert client.organization_id == "org-1"
        assert client.project_id == "proj-1"
        assert client.identity_api_url == "https://identity.nks.example.com"
        mock_session.headers.update.assert_called_once()
        headers = mock_session.headers.update.call_args[0][0]
        assert headers["Authorization"] == "Bearer token-abc"

    @patch("waldur_site_agent_nscale.client.requests.Session")
    def test_initialization_without_identity(self, mock_session_class):
        mock_session_class.return_value = MagicMock()

        client = NscaleClient(
            api_url="https://compute.nks.example.com",
            organization_id="org-1",
            project_id="proj-1",
            service_token="token-abc",
        )

        assert client.identity_api_url is None


class TestNscaleClientComputeAPI:
    """Test cases for compute API methods."""

    def _make_client(self):
        with patch("waldur_site_agent_nscale.client.requests.Session"):
            client = NscaleClient(
                api_url="https://compute.nks.example.com",
                organization_id="org-1",
                project_id="proj-1",
                service_token="token-abc",
            )
        return client

    def test_get_compute_instances(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = [SAMPLE_INSTANCE]
        client.session.request.return_value = mock_response

        result = client.get_compute_instances()

        assert len(result) == 1
        client.session.request.assert_called_once_with(
            "GET", "https://compute.nks.example.com/api/v2/instances"
        )

    def test_get_compute_instance(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_INSTANCE
        client.session.request.return_value = mock_response

        result = client.get_compute_instance("inst-001")

        assert result["metadata"]["id"] == "inst-001"
        client.session.request.assert_called_once_with(
            "GET", "https://compute.nks.example.com/api/v2/instances/inst-001"
        )

    def test_create_compute_instance(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_INSTANCE
        client.session.request.return_value = mock_response

        instance_data = {"metadata": {"name": "new-inst"}, "spec": {"flavorId": "standard"}}
        result = client.create_compute_instance(instance_data)

        assert result["metadata"]["id"] == "inst-001"
        call_args = client.session.request.call_args
        assert call_args[0] == ("POST", "https://compute.nks.example.com/api/v2/instances")
        assert call_args[1]["json"] == instance_data

    def test_stop_instance(self):
        client = self._make_client()
        mock_response = MagicMock()
        client.session.request.return_value = mock_response

        client.stop_instance("inst-001")

        client.session.request.assert_called_once_with(
            "POST", "https://compute.nks.example.com/api/v2/instances/inst-001/stop"
        )

    def test_start_instance(self):
        client = self._make_client()
        mock_response = MagicMock()
        client.session.request.return_value = mock_response

        client.start_instance("inst-001")

        client.session.request.assert_called_once_with(
            "POST", "https://compute.nks.example.com/api/v2/instances/inst-001/start"
        )

    def test_delete_compute_instance(self):
        client = self._make_client()
        mock_response = MagicMock()
        client.session.request.return_value = mock_response

        client.delete_compute_instance("inst-001")

        client.session.request.assert_called_once_with(
            "DELETE", "https://compute.nks.example.com/api/v2/instances/inst-001"
        )

    def test_update_compute_instance(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_INSTANCE
        client.session.request.return_value = mock_response

        update_data = {"spec": {"cpu": 8}}
        client.update_compute_instance("inst-001", update_data)

        call_args = client.session.request.call_args
        assert call_args[0] == (
            "PUT",
            "https://compute.nks.example.com/api/v2/instances/inst-001",
        )
        assert call_args[1]["json"] == update_data

    def test_api_error_handling(self):
        client = self._make_client()
        import requests

        error_response = MagicMock()
        error_response.status_code = 404
        error_response.text = "Not Found"
        http_error = requests.exceptions.HTTPError(response=error_response)
        client.session.request.side_effect = http_error

        with pytest.raises(NscaleAPIError, match="API request failed"):
            client.get_compute_instance("inst-missing")


class TestNscaleClientBaseInterface:
    """Test cases for BaseClient interface methods."""

    def _make_client(self, with_identity=False):
        with patch("waldur_site_agent_nscale.client.requests.Session"):
            client = NscaleClient(
                api_url="https://compute.nks.example.com",
                organization_id="org-1",
                project_id="proj-1",
                service_token="token-abc",
                identity_api_url="https://identity.nks.example.com" if with_identity else None,
            )
        return client

    def test_list_resources(self):
        client = self._make_client()

        def mock_request(method, url, **kwargs):
            mock_resp = MagicMock()
            if "/instances" in url and "/instances/" not in url:
                mock_resp.json.return_value = [SAMPLE_INSTANCE]
            elif "/clusters" in url and "/clusters/" not in url:
                mock_resp.json.return_value = [SAMPLE_CLUSTER]
            else:
                mock_resp.json.return_value = []
            return mock_resp

        client.session.request.side_effect = mock_request
        resources = client.list_resources()

        assert len(resources) == 2
        assert isinstance(resources[0], ClientResource)
        assert resources[0].backend_id == "inst-001"
        assert resources[1].backend_id == "cluster-001"

    def test_get_resource_instance(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_INSTANCE
        client.session.request.return_value = mock_response

        result = client.get_resource("inst-001")

        assert result is not None
        assert result.backend_id == "inst-001"

    def test_get_resource_not_found(self):
        client = self._make_client()
        import requests

        error_response = MagicMock()
        error_response.status_code = 404
        error_response.text = "Not Found"
        http_error = requests.exceptions.HTTPError(response=error_response)
        client.session.request.side_effect = http_error

        result = client.get_resource("inst-missing")
        assert result is None

    def test_delete_resource_instance(self):
        client = self._make_client()
        mock_response = MagicMock()
        client.session.request.return_value = mock_response

        result = client.delete_resource("inst-001")

        assert result == "inst-001"

    def test_set_resource_limits(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_INSTANCE
        client.session.request.return_value = mock_response

        result = client.set_resource_limits("inst-001", {"cpu": 8, "memory": 16})

        assert result == "Limits set for inst-001"
        call_args = client.session.request.call_args
        assert call_args[0] == (
            "PUT",
            "https://compute.nks.example.com/api/v2/instances/inst-001",
        )
        assert call_args[1]["json"]["spec"]["cpu"] == 8
        assert call_args[1]["json"]["spec"]["memory"] == 16

    def test_get_resource_limits(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_INSTANCE
        client.session.request.return_value = mock_response

        limits = client.get_resource_limits("inst-001")

        assert limits["cpu"] == 4
        assert limits["memory"] == 8
        assert limits["storage"] == 100

    def test_get_usage_report(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_INSTANCE
        client.session.request.return_value = mock_response

        report = client.get_usage_report(["inst-001"])

        assert len(report) == 1
        assert report[0]["resource_id"] == "inst-001"
        assert report[0]["cpu"] == 4
        assert report[0]["memory"] == 8
        assert report[0]["storage"] == 100

    def test_extract_instance_specs(self):
        specs = NscaleClient._extract_instance_specs(SAMPLE_INSTANCE)
        assert specs["cpu"] == 4
        assert specs["memory"] == 8
        assert specs["storage"] == 100

    def test_extract_instance_specs_flat(self):
        flat_instance = {"cpu": 2, "memory": 4, "storage": 50}
        specs = NscaleClient._extract_instance_specs(flat_instance)
        assert specs["cpu"] == 2
        assert specs["memory"] == 4
        assert specs["storage"] == 50


class TestNscaleClientIdentity:
    """Test cases for Identity API user management."""

    def _make_client(self):
        with patch("waldur_site_agent_nscale.client.requests.Session"):
            client = NscaleClient(
                api_url="https://compute.nks.example.com",
                organization_id="org-1",
                project_id="proj-1",
                service_token="token-abc",
                identity_api_url="https://identity.nks.example.com",
            )
        return client

    def test_identity_request_without_url(self):
        with patch("waldur_site_agent_nscale.client.requests.Session"):
            client = NscaleClient(
                api_url="https://compute.nks.example.com",
                organization_id="org-1",
                project_id="proj-1",
                service_token="token-abc",
            )

        with pytest.raises(NscaleAPIError, match="Identity API URL not configured"):
            client._identity_request("GET", "/api/v1/organizations/org-1/users")

    def test_get_association_found(self):
        client = self._make_client()

        def mock_request(method, url, **kwargs):
            mock_resp = MagicMock()
            if "/users" in url and "/users/" not in url:
                mock_resp.json.return_value = [SAMPLE_NSCALE_USER]
            elif "/groups" in url and "/groups/" not in url:
                mock_resp.json.return_value = [SAMPLE_GROUP]
            return mock_resp

        client.session.request.side_effect = mock_request

        result = client.get_association("testuser", "inst-001")

        assert result is not None
        assert isinstance(result, Association)
        assert result.user == "testuser"
        assert result.account == "inst-001"

    def test_get_association_user_not_found(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = []
        client.session.request.return_value = mock_response

        result = client.get_association("unknown-user", "inst-001")
        assert result is None

    def test_get_association_no_identity_url(self):
        with patch("waldur_site_agent_nscale.client.requests.Session"):
            client = NscaleClient(
                api_url="https://compute.nks.example.com",
                organization_id="org-1",
                project_id="proj-1",
                service_token="token-abc",
            )

        result = client.get_association("testuser", "inst-001")
        assert result is None

    def test_create_association_new_user(self):
        client = self._make_client()
        call_count = {"n": 0}

        def mock_request(method, url, **kwargs):
            mock_resp = MagicMock()
            call_count["n"] += 1
            if method == "GET" and "/users" in url and "/users/" not in url:
                mock_resp.json.return_value = []  # User not found
            elif method == "POST" and "/users" in url:
                mock_resp.json.return_value = SAMPLE_NSCALE_USER
            elif method == "GET" and "/groups" in url and "/groups/" not in url:
                mock_resp.json.return_value = []  # Group not found
            elif method == "POST" and "/groups" in url:
                mock_resp.json.return_value = SAMPLE_GROUP
            return mock_resp

        client.session.request.side_effect = mock_request

        result = client.create_association("testuser", "inst-001")
        assert result == "testuser"

    def test_delete_association(self):
        client = self._make_client()

        def mock_request(method, url, **kwargs):
            mock_resp = MagicMock()
            if method == "GET" and "/users" in url and "/users/" not in url:
                mock_resp.json.return_value = [SAMPLE_NSCALE_USER]
            elif method == "GET" and "/groups" in url and "/groups/" not in url:
                mock_resp.json.return_value = [SAMPLE_GROUP]
            elif method == "PUT" and "/groups/" in url:
                mock_resp.json.return_value = SAMPLE_GROUP
            return mock_resp

        client.session.request.side_effect = mock_request

        result = client.delete_association("testuser", "inst-001")
        assert result == "testuser"

    @patch.object(NscaleClient, "get_user")
    @patch.object(NscaleClient, "_find_project_group")
    def test_list_resource_users(self, mock_find_group, mock_get_user):
        client = self._make_client()
        mock_find_group.return_value = {
            "metadata": {"id": "grp-1", "name": "inst-001"},
            "spec": {"userIds": ["uid-1"]},
        }
        mock_get_user.return_value = {
            "metadata": {"id": "uid-1"},
            "spec": {"subject": "testuser", "state": "active"},
        }

        users = client.list_resource_users("inst-001")

        assert users == ["testuser"]
        mock_find_group.assert_called_once_with("inst-001")
        mock_get_user.assert_called_once_with("uid-1")

    def test_list_resource_users_no_identity(self):
        with patch("waldur_site_agent_nscale.client.requests.Session"):
            client = NscaleClient(
                api_url="https://compute.nks.example.com",
                organization_id="org-1",
                project_id="proj-1",
                service_token="token-abc",
            )

        users = client.list_resource_users("inst-001")
        assert users == []

    def test_create_linux_user_homedir(self):
        client = self._make_client()
        result = client.create_linux_user_homedir("testuser")
        assert result == ""
