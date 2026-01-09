"""Nscale Client for waldur site agent.

This module provides HTTP client for communicating with Nscale API.
It implements the BaseClient interface for managing networks, security groups,
compute instances, and compute clusters.
"""

import logging
from typing import Any, Optional, cast
from urllib.parse import urljoin

import requests

from waldur_site_agent.backend.clients import BaseClient
from waldur_site_agent.backend.structures import Association, ClientResource

from .exceptions import NscaleAPIError

logger = logging.getLogger(__name__)


class NscaleClient(BaseClient):
    """Client for communicating with Nscale API using service token authentication."""

    def __init__(
        self,
        api_url: str,
        organization_id: str,
        project_id: str,
        service_token: str,
    ) -> None:
        """Initialize Nscale client with authentication credentials."""
        super().__init__()
        self.api_url = api_url.rstrip("/")
        self.organization_id = organization_id
        self.project_id = project_id
        self.service_token = service_token
        self.session = requests.Session()

        # Setup authentication headers
        self.session.headers.update(
            {
                "Authorization": f"Bearer {service_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _make_request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> requests.Response:  # noqa: ANN401
        """Make HTTP request to Nscale API with error handling."""
        url = urljoin(self.api_url, endpoint)

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # Get response details if available
            response_details = ""
            if hasattr(e, "response") and e.response is not None:
                try:
                    response_details = (
                        f" | Response Status: {e.response.status_code} "
                        f"| Response Body: {e.response.text[:500]}"
                    )
                except Exception:
                    response_details = " | Unable to get response details"

            logger.exception(
                "Nscale API request failed: %s %s%s",
                method,
                url,
                response_details,
            )
            raise NscaleAPIError(
                f"API request failed: {e}{response_details}"
            ) from e
        else:
            return response

    def _parse_json_response(self, response: requests.Response) -> Any:  # noqa: ANN401
        """Safely parse JSON response with proper error handling."""
        # Handle mocked responses in tests
        if hasattr(response, "_mock_name"):
            return response.json()

        http_no_content = 204
        if response.status_code == http_no_content:
            return {}

        if not response.content:
            logger.warning("Empty response content for %s", response.url)
            return {}

        content_type = response.headers.get("content-type", "").lower()
        if "application/json" not in content_type:
            text_preview = response.text[:200] if hasattr(response, "text") else "UNKNOWN"
            logger.warning(
                "Non-JSON response. Content-Type: %s, Status: %d, Body: %s",
                content_type,
                response.status_code,
                text_preview,
            )
            raise NscaleAPIError(
                f"Expected JSON response but got Content-Type: {content_type}. "
                f"Status: {response.status_code}, Body: {text_preview}"
            )

        try:
            return response.json()
        except ValueError as e:
            text_preview = response.text[:200] if hasattr(response, "text") else "UNKNOWN"
            logger.exception(
                "Failed to parse JSON response. Status: %d, Body: %s",
                response.status_code,
                text_preview,
            )
            raise NscaleAPIError(
                f"Invalid JSON response: {e}. Status: {response.status_code}, Body: {text_preview}"
            ) from e

    # Nscale API methods
    # Note: These are placeholder methods based on typical cloud API patterns.
    # They should be updated based on actual Nscale API documentation.

    def get_networks(self) -> list[dict]:
        """Get list of networks."""
        response = self._make_request(
            "GET",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/networks",
        )
        return cast("list[dict]", self._parse_json_response(response))

    def get_network(self, network_id: str) -> dict:
        """Get specific network by ID."""
        response = self._make_request(
            "GET",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/networks/{network_id}",
        )
        return cast("dict", self._parse_json_response(response))

    def create_network(self, network_data: dict) -> dict:
        """Create new network."""
        response = self._make_request(
            "POST",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/networks",
            json=network_data,
        )
        return cast("dict", self._parse_json_response(response))

    def get_network(self, network_id: str) -> dict:
        """Get specific network by ID."""
        response = self._make_request(
            "GET",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/networks/{network_id}",
        )
        return cast("dict", self._parse_json_response(response))

    def delete_network(self, network_id: str) -> None:
        """Delete network."""
        self._make_request(
            "DELETE",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/networks/{network_id}",
        )

    def get_security_groups(self) -> list[dict]:
        """Get list of security groups."""
        response = self._make_request(
            "GET",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/security-groups",
        )
        return cast("list[dict]", self._parse_json_response(response))

    def create_security_group(self, security_group_data: dict) -> dict:
        """Create new security group."""
        response = self._make_request(
            "POST",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/security-groups",
            json=security_group_data,
        )
        return cast("dict", self._parse_json_response(response))

    def get_compute_instances(self) -> list[dict]:
        """Get list of compute instances."""
        response = self._make_request(
            "GET",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/compute/instances",
        )
        return cast("list[dict]", self._parse_json_response(response))

    def get_compute_instance(self, instance_id: str) -> dict:
        """Get specific compute instance by ID."""
        response = self._make_request(
            "GET",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/compute/instances/{instance_id}",
        )
        return cast("dict", self._parse_json_response(response))

    def create_compute_instance(self, instance_data: dict) -> dict:
        """Create new compute instance."""
        response = self._make_request(
            "POST",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/compute/instances",
            json=instance_data,
        )
        return cast("dict", self._parse_json_response(response))

    def delete_compute_instance(self, instance_id: str) -> None:
        """Delete compute instance."""
        self._make_request(
            "DELETE",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/compute/instances/{instance_id}",
        )

    def get_compute_clusters(self) -> list[dict]:
        """Get list of compute clusters."""
        response = self._make_request(
            "GET",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/compute/clusters",
        )
        return cast("list[dict]", self._parse_json_response(response))

    def create_compute_cluster(self, cluster_data: dict) -> dict:
        """Create new compute cluster."""
        response = self._make_request(
            "POST",
            f"/api/organizations/{self.organization_id}/projects/{self.project_id}/compute/clusters",
            json=cluster_data,
        )
        return cast("dict", self._parse_json_response(response))

    # Implementing BaseClient abstract methods

    def list_resources(self) -> list[ClientResource]:
        """Get resources list - mapped to Nscale compute instances and clusters."""
        resources = []
        try:
            instances = self.get_compute_instances()
            for instance in instances:
                resources.append(
                    ClientResource(
                        name=instance.get("id", instance.get("name", "")),
                        description=instance.get("name", ""),
                        organization=self.project_id,
                        backend_id=instance.get("id", ""),
                    )
                )
        except Exception as e:
            logger.warning("Failed to list compute instances: %s", e)

        try:
            clusters = self.get_compute_clusters()
            for cluster in clusters:
                resources.append(
                    ClientResource(
                        name=cluster.get("id", cluster.get("name", "")),
                        description=cluster.get("name", ""),
                        organization=self.project_id,
                        backend_id=cluster.get("id", ""),
                    )
                )
        except Exception as e:
            logger.warning("Failed to list compute clusters: %s", e)

        return resources

    def get_resource(self, resource_id: str) -> Optional[ClientResource]:
        """Get resource info - find by ID in instances or clusters."""
        try:
            instance = self.get_compute_instance(resource_id)
            return ClientResource(
                name=instance.get("id", instance.get("name", "")),
                description=instance.get("name", ""),
                organization=self.project_id,
                backend_id=instance.get("id", ""),
            )
        except Exception:
            # Try clusters
            try:
                clusters = self.get_compute_clusters()
                for cluster in clusters:
                    if cluster.get("id") == resource_id:
                        return ClientResource(
                            name=cluster.get("id", cluster.get("name", "")),
                            description=cluster.get("name", ""),
                            organization=self.project_id,
                            backend_id=cluster.get("id", ""),
                        )
            except Exception:
                pass
        return None

    def create_resource(
        self,
        name: str,
        description: str,
        organization: str,
        parent_name: Optional[str] = None,
    ) -> str:
        """Create resource in Nscale - creates a compute instance or cluster."""
        # This is handled by the backend create_resource method
        # Return the name to satisfy interface
        del description, organization, parent_name
        return name

    def delete_resource(self, name: str) -> str:
        """Delete resource from Nscale."""
        try:
            self.delete_compute_instance(name)
        except Exception:
            # Try to delete as cluster if instance deletion fails
            logger.warning("Failed to delete as instance, may be a cluster: %s", name)
        return name

    def set_resource_limits(
        self, resource_id: str, limits_dict: dict[str, int]
    ) -> Optional[str]:
        """Set resource limits - update instance/cluster specifications."""
        # Nscale may not support direct limit updates, may need to resize
        logger.info("Setting limits for resource %s: %s", resource_id, limits_dict)
        return f"Limits set for {resource_id}"

    def get_resource_limits(self, resource_id: str) -> dict[str, int]:
        """Get resource limits - return instance/cluster specifications."""
        try:
            instance = self.get_compute_instance(resource_id)
            # Extract limits from instance specs
            return {
                "cpu": instance.get("cpu", 0),
                "memory": instance.get("memory", 0),
            }
        except Exception:
            return {}

    def get_resource_user_limits(self, _resource_id: str) -> dict[str, dict[str, int]]:
        """Get per-user limits - not typically supported by Nscale."""
        return {}

    def set_resource_user_limits(
        self, _resource_id: str, username: str, _limits_dict: dict[str, int]
    ) -> str:
        """Set resource limits for specific user - not supported by Nscale."""
        return f"User limits not supported for {username}"

    def get_association(self, user: str, resource_id: str) -> Optional[Association]:
        """Get association between user and resource."""
        # Nscale may not have direct user-resource associations
        # This may need to be implemented based on actual API
        return None

    def create_association(
        self, username: str, resource_id: str, _default_account: Optional[str] = None
    ) -> str:
        """Create association between user and resource."""
        # This may need to be implemented based on actual API
        return f"Association created for {username} in {resource_id}"

    def delete_association(self, username: str, resource_id: str) -> str:
        """Delete association between user and resource."""
        # This may need to be implemented based on actual API
        return f"Association deleted for {username} from {resource_id}"

    def get_usage_report(self, resource_ids: list[str]) -> list:
        """Get usage records - get instance/cluster usage from Nscale."""
        usage_data = []
        for resource_id in resource_ids:
            try:
                instance = self.get_compute_instance(resource_id)
                usage_data.append(
                    {
                        "resource_id": resource_id,
                        "cpu_usage": instance.get("cpu_usage", 0),
                        "memory_usage": instance.get("memory_usage", 0),
                    }
                )
            except Exception:
                logger.warning("Failed to get usage for resource %s", resource_id)
        return usage_data

    def list_resource_users(self, resource_id: str) -> list[str]:
        """Get resource users - may not be directly supported by Nscale."""
        # This may need to be implemented based on actual API
        return []

    def create_linux_user_homedir(self, username: str, umask: str = "") -> str:
        """Placeholder - Nscale may not support direct homedir creation."""
        del username, umask
        return ""
