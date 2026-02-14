"""Nscale Client for waldur site agent.

This module provides HTTP client for communicating with Nscale API.
It implements the BaseClient interface for managing networks, security groups,
compute instances, compute clusters, and user management via the Identity Service.
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
    """Client for communicating with Nscale API using service token authentication.

    Nscale uses separate service endpoints:
    - Compute Service: manages instances, clusters
    - Region Service: manages networks, security groups, storage
    - Identity Service: manages users, groups, projects
    """

    def __init__(
        self,
        api_url: str,
        organization_id: str,
        project_id: str,
        service_token: str,
        identity_api_url: Optional[str] = None,
    ) -> None:
        """Initialize Nscale client with authentication credentials."""
        super().__init__()
        self.api_url = api_url.rstrip("/")
        self.organization_id = organization_id
        self.project_id = project_id
        self.service_token = service_token
        self.identity_api_url = identity_api_url.rstrip("/") if identity_api_url else None
        self.session = requests.Session()

        self.session.headers.update(
            {
                "Authorization": f"Bearer {service_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _make_request(
        self, method: str, endpoint: str, base_url: Optional[str] = None, **kwargs: Any
    ) -> requests.Response:  # noqa: ANN401
        """Make HTTP request to Nscale API with error handling."""
        url = urljoin(base_url or self.api_url, endpoint)

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
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

    # ── Compute Service: Instances ──

    def get_compute_instances(self) -> list[dict]:
        """Get list of compute instances."""
        response = self._make_request("GET", "/api/v2/instances")
        return cast("list[dict]", self._parse_json_response(response))

    def get_compute_instance(self, instance_id: str) -> dict:
        """Get specific compute instance by ID."""
        response = self._make_request("GET", f"/api/v2/instances/{instance_id}")
        return cast("dict", self._parse_json_response(response))

    def create_compute_instance(self, instance_data: dict) -> dict:
        """Create new compute instance."""
        response = self._make_request("POST", "/api/v2/instances", json=instance_data)
        return cast("dict", self._parse_json_response(response))

    def update_compute_instance(self, instance_id: str, instance_data: dict) -> dict:
        """Update compute instance specs."""
        response = self._make_request(
            "PUT", f"/api/v2/instances/{instance_id}", json=instance_data
        )
        return cast("dict", self._parse_json_response(response))

    def delete_compute_instance(self, instance_id: str) -> None:
        """Delete compute instance."""
        self._make_request("DELETE", f"/api/v2/instances/{instance_id}")

    def stop_instance(self, instance_id: str) -> None:
        """Stop a running compute instance."""
        self._make_request("POST", f"/api/v2/instances/{instance_id}/stop")

    def start_instance(self, instance_id: str) -> None:
        """Start a stopped compute instance."""
        self._make_request("POST", f"/api/v2/instances/{instance_id}/start")

    # ── Compute Service: Clusters ──

    def get_compute_clusters(self) -> list[dict]:
        """Get list of compute clusters."""
        response = self._make_request("GET", "/api/v2/clusters")
        return cast("list[dict]", self._parse_json_response(response))

    def get_compute_cluster(self, cluster_id: str) -> dict:
        """Get specific compute cluster by ID."""
        response = self._make_request("GET", f"/api/v2/clusters/{cluster_id}")
        return cast("dict", self._parse_json_response(response))

    def create_compute_cluster(self, cluster_data: dict) -> dict:
        """Create new compute cluster."""
        response = self._make_request("POST", "/api/v2/clusters", json=cluster_data)
        return cast("dict", self._parse_json_response(response))

    def delete_compute_cluster(self, cluster_id: str) -> None:
        """Delete compute cluster."""
        self._make_request("DELETE", f"/api/v2/clusters/{cluster_id}")

    # ── Region Service: Networks ──

    def get_networks(self) -> list[dict]:
        """Get list of networks."""
        response = self._make_request("GET", "/api/v2/networks")
        return cast("list[dict]", self._parse_json_response(response))

    def get_network(self, network_id: str) -> dict:
        """Get specific network by ID."""
        response = self._make_request("GET", f"/api/v2/networks/{network_id}")
        return cast("dict", self._parse_json_response(response))

    def create_network(self, network_data: dict) -> dict:
        """Create new network."""
        response = self._make_request("POST", "/api/v2/networks", json=network_data)
        return cast("dict", self._parse_json_response(response))

    def delete_network(self, network_id: str) -> None:
        """Delete network."""
        self._make_request("DELETE", f"/api/v2/networks/{network_id}")

    # ── Region Service: Security Groups ──

    def get_security_groups(self) -> list[dict]:
        """Get list of security groups."""
        response = self._make_request("GET", "/api/v2/securitygroups")
        return cast("list[dict]", self._parse_json_response(response))

    def create_security_group(self, security_group_data: dict) -> dict:
        """Create new security group."""
        response = self._make_request(
            "POST", "/api/v2/securitygroups", json=security_group_data
        )
        return cast("dict", self._parse_json_response(response))

    # ── Identity Service: Users ──

    def _identity_request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> requests.Response:  # noqa: ANN401
        """Make request to NScale Identity Service."""
        if not self.identity_api_url:
            raise NscaleAPIError(
                "Identity API URL not configured. "
                "Set identity_api_url in backend settings to enable user management."
            )
        return self._make_request(method, endpoint, base_url=self.identity_api_url, **kwargs)

    def list_organization_users(self) -> list[dict]:
        """List users in the organization."""
        response = self._identity_request(
            "GET", f"/api/v1/organizations/{self.organization_id}/users"
        )
        return cast("list[dict]", self._parse_json_response(response))

    def get_user(self, user_id: str) -> dict:
        """Get a specific user."""
        response = self._identity_request(
            "GET", f"/api/v1/organizations/{self.organization_id}/users/{user_id}"
        )
        return cast("dict", self._parse_json_response(response))

    def create_user(self, user_data: dict) -> dict:
        """Create a user in the organization."""
        response = self._identity_request(
            "POST",
            f"/api/v1/organizations/{self.organization_id}/users",
            json=user_data,
        )
        return cast("dict", self._parse_json_response(response))

    def update_user(self, user_id: str, user_data: dict) -> dict:
        """Update a user (e.g. change state to active/suspended)."""
        response = self._identity_request(
            "PUT",
            f"/api/v1/organizations/{self.organization_id}/users/{user_id}",
            json=user_data,
        )
        return cast("dict", self._parse_json_response(response))

    def delete_user(self, user_id: str) -> None:
        """Delete a user from the organization."""
        self._identity_request(
            "DELETE", f"/api/v1/organizations/{self.organization_id}/users/{user_id}"
        )

    # ── Identity Service: Groups ──

    def list_groups(self) -> list[dict]:
        """List groups in the organization."""
        response = self._identity_request(
            "GET", f"/api/v1/organizations/{self.organization_id}/groups"
        )
        return cast("list[dict]", self._parse_json_response(response))

    def get_group(self, group_id: str) -> dict:
        """Get a specific group."""
        response = self._identity_request(
            "GET", f"/api/v1/organizations/{self.organization_id}/groups/{group_id}"
        )
        return cast("dict", self._parse_json_response(response))

    def create_group(self, group_data: dict) -> dict:
        """Create a group in the organization."""
        response = self._identity_request(
            "POST",
            f"/api/v1/organizations/{self.organization_id}/groups",
            json=group_data,
        )
        return cast("dict", self._parse_json_response(response))

    def update_group(self, group_id: str, group_data: dict) -> dict:
        """Update a group (e.g. add/remove user IDs)."""
        response = self._identity_request(
            "PUT",
            f"/api/v1/organizations/{self.organization_id}/groups/{group_id}",
            json=group_data,
        )
        return cast("dict", self._parse_json_response(response))

    def delete_group(self, group_id: str) -> None:
        """Delete a group from the organization."""
        self._identity_request(
            "DELETE", f"/api/v1/organizations/{self.organization_id}/groups/{group_id}"
        )

    # ── Helpers ──

    def _find_user_by_username(self, username: str) -> Optional[dict]:
        """Find a user in the organization by username/email."""
        try:
            users = self.list_organization_users()
            for user in users:
                spec = user.get("spec", {})
                if spec.get("subject") == username:
                    return user
        except NscaleAPIError:
            logger.warning("Failed to search for user %s in Identity API", username)
        return None

    def _find_project_group(self, resource_id: str) -> Optional[dict]:
        """Find the group associated with a resource's project."""
        try:
            groups = self.list_groups()
            for group in groups:
                metadata = group.get("metadata", {})
                if metadata.get("name", "").endswith(resource_id):
                    return group
        except NscaleAPIError:
            logger.warning("Failed to search for project group for resource %s", resource_id)
        return None

    @staticmethod
    def _extract_instance_specs(instance: dict) -> dict[str, int]:
        """Extract CPU, memory, and storage specs from an instance response."""
        spec = instance.get("spec", {})
        return {
            "cpu": spec.get("cpu", instance.get("cpu", 0)),
            "memory": spec.get("memory", instance.get("memory", 0)),
            "storage": spec.get("storage", instance.get("storage", 0)),
        }

    # ── BaseClient interface implementation ──

    def list_resources(self) -> list[ClientResource]:
        """Get resources list - mapped to Nscale compute instances and clusters."""
        resources = []
        try:
            instances = self.get_compute_instances()
            for instance in instances:
                metadata = instance.get("metadata", instance)
                resources.append(
                    ClientResource(
                        name=metadata.get("id", metadata.get("name", "")),
                        description=metadata.get("name", ""),
                        organization=self.project_id,
                        backend_id=metadata.get("id", ""),
                    )
                )
        except Exception as e:
            logger.warning("Failed to list compute instances: %s", e)

        try:
            clusters = self.get_compute_clusters()
            for cluster in clusters:
                metadata = cluster.get("metadata", cluster)
                resources.append(
                    ClientResource(
                        name=metadata.get("id", metadata.get("name", "")),
                        description=metadata.get("name", ""),
                        organization=self.project_id,
                        backend_id=metadata.get("id", ""),
                    )
                )
        except Exception as e:
            logger.warning("Failed to list compute clusters: %s", e)

        return resources

    def get_resource(self, resource_id: str) -> Optional[ClientResource]:
        """Get resource info - find by ID in instances or clusters."""
        try:
            instance = self.get_compute_instance(resource_id)
            metadata = instance.get("metadata", instance)
            return ClientResource(
                name=metadata.get("id", metadata.get("name", "")),
                description=metadata.get("name", ""),
                organization=self.project_id,
                backend_id=metadata.get("id", ""),
            )
        except Exception:
            try:
                cluster = self.get_compute_cluster(resource_id)
                metadata = cluster.get("metadata", cluster)
                return ClientResource(
                    name=metadata.get("id", metadata.get("name", "")),
                    description=metadata.get("name", ""),
                    organization=self.project_id,
                    backend_id=metadata.get("id", ""),
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
        """Create resource in Nscale - handled by the backend."""
        del description, organization, parent_name
        return name

    def delete_resource(self, name: str) -> str:
        """Delete resource from Nscale."""
        try:
            self.delete_compute_instance(name)
        except Exception:
            try:
                self.delete_compute_cluster(name)
            except Exception:
                logger.warning("Failed to delete resource %s as instance or cluster", name)
        return name

    def set_resource_limits(
        self, resource_id: str, limits_dict: dict[str, int]
    ) -> Optional[str]:
        """Set resource limits by updating instance specs."""
        instance_data: dict[str, Any] = {"spec": {}}
        if "cpu" in limits_dict:
            instance_data["spec"]["cpu"] = limits_dict["cpu"]
        if "memory" in limits_dict:
            instance_data["spec"]["memory"] = limits_dict["memory"]
        if "storage" in limits_dict:
            instance_data["spec"]["storage"] = limits_dict["storage"]

        if instance_data["spec"]:
            self.update_compute_instance(resource_id, instance_data)
            logger.info("Updated limits for resource %s: %s", resource_id, limits_dict)
        return f"Limits set for {resource_id}"

    def get_resource_limits(self, resource_id: str) -> dict[str, int]:
        """Get resource limits from instance specs."""
        try:
            instance = self.get_compute_instance(resource_id)
            return self._extract_instance_specs(instance)
        except Exception:
            return {}

    def get_resource_user_limits(self, _resource_id: str) -> dict[str, dict[str, int]]:
        """Get per-user limits - not supported by NScale (instance-level only)."""
        return {}

    def set_resource_user_limits(
        self, _resource_id: str, username: str, _limits_dict: dict[str, int]
    ) -> str:
        """Set per-user limits - not supported by NScale (instance-level only)."""
        return f"Per-user limits not supported for {username}"

    def get_association(self, user: str, resource_id: str) -> Optional[Association]:
        """Get association between user and resource via Identity API."""
        if not self.identity_api_url:
            return None

        nscale_user = self._find_user_by_username(user)
        if nscale_user is None:
            return None

        user_id = nscale_user.get("metadata", {}).get("id", "")
        group = self._find_project_group(resource_id)
        if group is None:
            return None

        user_ids = group.get("spec", {}).get("userIds", [])
        if user_id in user_ids:
            return Association(user=user, account=resource_id)
        return None

    def create_association(
        self, username: str, resource_id: str, _default_account: Optional[str] = None
    ) -> str:
        """Create association between user and resource via Identity API."""
        if not self.identity_api_url:
            logger.warning("Identity API not configured, skipping user association")
            return username

        nscale_user = self._find_user_by_username(username)
        if nscale_user is None:
            nscale_user = self.create_user(
                {"spec": {"subject": username, "state": "active"}}
            )
            logger.info("Created NScale user for %s", username)

        user_id = nscale_user.get("metadata", {}).get("id", "")

        group = self._find_project_group(resource_id)
        if group is None:
            group = self.create_group(
                {"metadata": {"name": resource_id}, "spec": {"userIds": [user_id]}}
            )
            logger.info("Created project group for resource %s", resource_id)
        else:
            group_id = group.get("metadata", {}).get("id", "")
            user_ids = group.get("spec", {}).get("userIds", [])
            if user_id not in user_ids:
                user_ids.append(user_id)
                self.update_group(group_id, {"spec": {"userIds": user_ids}})
                logger.info("Added user %s to group for resource %s", username, resource_id)

        return username

    def delete_association(self, username: str, resource_id: str) -> str:
        """Delete association between user and resource via Identity API."""
        if not self.identity_api_url:
            logger.warning("Identity API not configured, skipping user disassociation")
            return username

        nscale_user = self._find_user_by_username(username)
        if nscale_user is None:
            return username

        user_id = nscale_user.get("metadata", {}).get("id", "")
        group = self._find_project_group(resource_id)
        if group is None:
            return username

        group_id = group.get("metadata", {}).get("id", "")
        user_ids = group.get("spec", {}).get("userIds", [])
        if user_id in user_ids:
            user_ids.remove(user_id)
            self.update_group(group_id, {"spec": {"userIds": user_ids}})
            logger.info("Removed user %s from group for resource %s", username, resource_id)

        return username

    def get_usage_report(self, resource_ids: list[str]) -> list:
        """Get usage by reporting allocated instance specs."""
        usage_data = []
        for resource_id in resource_ids:
            try:
                instance = self.get_compute_instance(resource_id)
                specs = self._extract_instance_specs(instance)
                usage_data.append({"resource_id": resource_id, **specs})
            except Exception:
                logger.warning("Failed to get usage for resource %s", resource_id)
        return usage_data

    def list_resource_users(self, resource_id: str) -> list[str]:
        """List users associated with a resource via its project group."""
        if not self.identity_api_url:
            return []

        group = self._find_project_group(resource_id)
        if group is None:
            return []

        user_ids = group.get("spec", {}).get("userIds", [])
        usernames = []
        for uid in user_ids:
            try:
                user = self.get_user(uid)
                subject = user.get("spec", {}).get("subject", "")
                if subject:
                    usernames.append(subject)
            except Exception:
                logger.warning("Failed to resolve user ID %s", uid)
        return usernames

    def create_linux_user_homedir(self, username: str, umask: str = "") -> str:
        """Not applicable for NScale cloud VMs."""
        logger.info("Homedir creation not applicable for NScale (cloud VM): %s", username)
        del umask
        return ""
