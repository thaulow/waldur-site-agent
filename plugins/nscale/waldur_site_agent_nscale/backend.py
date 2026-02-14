"""Nscale Backend for waldur site agent.

This module provides integration between Waldur Mastermind and Nscale.
It implements the backend interface for managing compute instances, clusters,
networks, and security groups.

Mapping:
- Waldur Project -> Nscale Project
- Waldur Resource -> Nscale Compute Instance/Cluster
- Waldur User -> Nscale User (via Identity Service)
"""

import logging
from typing import Optional

from waldur_api_client.models.resource import Resource as WaldurResource

from waldur_site_agent.backend import backends
from waldur_site_agent.backend.exceptions import BackendError
from waldur_site_agent.backend.structures import BackendResourceInfo
from waldur_site_agent_nscale.client import NscaleClient
from waldur_site_agent_nscale.exceptions import NscaleAPIError

logger = logging.getLogger(__name__)


class NscaleBackend(backends.BaseBackend):
    """Nscale backend implementation for Waldur Site Agent.

    This backend manages the lifecycle of compute resources in Nscale based on
    Waldur marketplace orders and handles resource management.

    Supports two resource types via ``resource_type`` setting:
    - ``instance`` (default): Compute instances.
    - ``cluster``: Kubernetes clusters.
    """

    # Usage reflects currently allocated specs, not accumulated historical usage.
    supports_decreasing_usage: bool = True
    client: NscaleClient

    def __init__(self, nscale_settings: dict, nscale_components: dict[str, dict]) -> None:
        """Init backend info and creates a corresponding client."""
        super().__init__(nscale_settings, nscale_components)
        self.backend_type = "nscale"

        required_settings = ["api_url", "organization_id", "project_id", "service_token"]
        for setting in required_settings:
            if setting not in nscale_settings:
                raise ValueError(f"Missing required setting: {setting}")

        self.resource_type = nscale_settings.get("resource_type", "instance")

        self.client = NscaleClient(
            api_url=nscale_settings["api_url"],
            organization_id=nscale_settings["organization_id"],
            project_id=nscale_settings["project_id"],
            service_token=nscale_settings["service_token"],
            identity_api_url=nscale_settings.get("identity_api_url"),
        )

        self.resource_prefix = nscale_settings.get("resource_prefix", "waldur_")
        self.instance_type = nscale_settings.get("default_instance_type", "standard")
        self.image_id = nscale_settings.get("default_image_id", "")
        self.network_id = nscale_settings.get("default_network_id", "")
        self.security_group_ids = nscale_settings.get("default_security_group_ids", [])

    def ping(self, raise_exception: bool = False) -> bool:
        """Check if Nscale backend is available and accessible."""
        try:
            self.client.get_networks()
        except Exception as e:
            if raise_exception:
                raise BackendError(f"Nscale backend not available: {e}") from e
            logger.exception("Nscale backend not available")
            return False
        else:
            return True

    def diagnostics(self) -> bool:
        """Logs info about the Nscale backend."""
        try:
            networks = self.client.get_networks()
            instances = self.client.get_compute_instances()
            clusters = self.client.get_compute_clusters()
            logger.info(
                "Nscale backend diagnostics: %d networks, %d instances, %d clusters",
                len(networks),
                len(instances),
                len(clusters),
            )
            return True
        except Exception as e:
            logger.exception("Nscale diagnostics failed: %s", e)
            return False

    def list_components(self) -> list[str]:
        """Return a list of components supported by Nscale backend."""
        return list(self.backend_components.keys())

    def _pre_create_resource(
        self, waldur_resource: WaldurResource, user_context: Optional[dict] = None
    ) -> None:
        """Perform actions prior to resource creation."""
        if self.network_id:
            try:
                self.client.get_network(self.network_id)
            except Exception:
                logger.warning("Default network %s not found", self.network_id)
        del user_context

    def _collect_resource_limits(
        self, waldur_resource: WaldurResource
    ) -> tuple[dict[str, int], dict[str, int]]:
        """Convert Waldur resource limits to backend limits.

        Multiplies each component value by its unit_factor.
        Handles both dict and object forms of limits.
        """
        nscale_limits: dict[str, int] = {}
        waldur_limits: dict[str, int] = {}

        raw_limits = waldur_resource.limits
        resource_limits: dict = (
            raw_limits.to_dict() if hasattr(raw_limits, "to_dict") else raw_limits or {}
        )

        for component_key, component_config in self.backend_components.items():
            waldur_value = resource_limits.get(component_key)
            if waldur_value is not None:
                unit_factor = component_config.get("unit_factor", 1)
                nscale_limits[component_key] = int(waldur_value) * unit_factor
                waldur_limits[component_key] = int(waldur_value)

        return nscale_limits, waldur_limits

    def _get_usage_report(
        self, resource_backend_ids: list[str]
    ) -> dict[str, dict[str, dict[str, int]]]:
        """Collect usage report by reporting allocated specs for each resource.

        Values are converted to Waldur units by dividing by unit_factor.
        """
        report: dict[str, dict[str, dict[str, int]]] = {}

        for resource_id in resource_backend_ids:
            try:
                instance = self.client.get_compute_instance(resource_id)
                spec = instance.get("spec", {})

                usage: dict[str, int] = {}
                for component_key, component_config in self.backend_components.items():
                    backend_value = spec.get(
                        component_key, instance.get(component_key, 0)
                    )
                    unit_factor = component_config.get("unit_factor", 1)
                    usage[component_key] = backend_value // max(unit_factor, 1)

                report[resource_id] = {"TOTAL_ACCOUNT_USAGE": usage}

            except Exception:
                logger.exception("Failed to get usage for resource %s", resource_id)
                empty_usage = dict.fromkeys(self.backend_components, 0)
                report[resource_id] = {"TOTAL_ACCOUNT_USAGE": empty_usage}

        return report

    def downscale_resource(self, resource_backend_id: str) -> bool:
        """Downscale the resource by stopping the instance."""
        try:
            self.client.stop_instance(resource_backend_id)
            logger.info("Downscaled (stopped) resource %s", resource_backend_id)
            return True
        except Exception as e:
            logger.exception("Failed to downscale resource %s: %s", resource_backend_id, e)
            return False

    def pause_resource(self, resource_backend_id: str) -> bool:
        """Pause the resource by stopping the instance."""
        try:
            self.client.stop_instance(resource_backend_id)
            logger.info("Paused (stopped) resource %s", resource_backend_id)
            return True
        except Exception as e:
            logger.exception("Failed to pause resource %s: %s", resource_backend_id, e)
            return False

    def restore_resource(self, resource_backend_id: str) -> bool:
        """Restore the resource by starting the instance."""
        try:
            self.client.start_instance(resource_backend_id)
            logger.info("Restored (started) resource %s", resource_backend_id)
            return True
        except Exception as e:
            logger.exception("Failed to restore resource %s: %s", resource_backend_id, e)
            return False

    def get_resource_metadata(self, resource_backend_id: str) -> dict:
        """Get backend-specific resource metadata."""
        try:
            instance = self.client.get_compute_instance(resource_backend_id)
            metadata = instance.get("metadata", {})
            spec = instance.get("spec", {})
            status = instance.get("status", {})
            return {
                "instance_id": metadata.get("id", instance.get("id")),
                "instance_name": metadata.get("name", instance.get("name")),
                "flavor_id": spec.get("flavorId", ""),
                "image_id": spec.get("imageId", ""),
                "power_state": status.get("powerState", ""),
                "provisioning_status": status.get("provisioningStatus", ""),
                "cpu": spec.get("cpu", instance.get("cpu", 0)),
                "memory": spec.get("memory", instance.get("memory", 0)),
                "storage": spec.get("storage", instance.get("storage", 0)),
            }
        except Exception:
            logger.exception("Failed to get resource metadata for %s", resource_backend_id)
            return {}

    def _create_backend_resource(
        self,
        resource_backend_id: str,
        resource_name: str,
        resource_organization: str,
        resource_parent_name: Optional[str] = None,
    ) -> bool:
        """Create instance or cluster depending on resource_type."""
        logger.info(
            "Creating %s resource %s in %s backend (backend ID = %s)",
            self.resource_type,
            resource_name,
            self.backend_type,
            resource_backend_id,
        )

        if self.client.get_resource(resource_backend_id) is not None:
            logger.info("The resource with ID %s already exists in Nscale", resource_backend_id)
            return True

        if self.resource_type == "cluster":
            return self._create_cluster_resource(resource_backend_id, resource_name)

        return self._create_instance_resource(resource_backend_id)

    def _create_instance_resource(self, resource_backend_id: str) -> bool:
        """Create a compute instance in Nscale."""
        instance_data = {
            "metadata": {"name": resource_backend_id},
            "spec": {
                "flavorId": self.instance_type,
            },
        }

        if self.image_id:
            instance_data["spec"]["imageId"] = self.image_id
        if self.network_id:
            instance_data["spec"]["networking"] = {"networkId": self.network_id}
        if self.security_group_ids:
            instance_data["spec"].setdefault("networking", {})["securityGroups"] = (
                self.security_group_ids
            )

        try:
            self.client.create_compute_instance(instance_data)
            logger.info("Created Nscale compute instance %s", resource_backend_id)
            return True
        except NscaleAPIError as e:
            logger.exception("Failed to create compute instance: %s", e)
            raise BackendError(f"Failed to create compute instance: {e}") from e

    def _create_cluster_resource(
        self, resource_backend_id: str, resource_name: str
    ) -> bool:
        """Create a Kubernetes cluster in Nscale."""
        cluster_data = {
            "metadata": {"name": resource_backend_id},
            "spec": {
                "workloadPools": [
                    {
                        "name": "default",
                        "replicas": 1,
                        "flavorId": self.instance_type,
                    }
                ],
            },
        }

        try:
            self.client.create_compute_cluster(cluster_data)
            logger.info("Created Nscale cluster %s", resource_backend_id)
            return True
        except NscaleAPIError as e:
            logger.exception("Failed to create cluster: %s", e)
            raise BackendError(f"Failed to create cluster: {e}") from e

    def delete_resource(self, waldur_resource: WaldurResource, **kwargs: str) -> None:
        """Delete resource from the backend.

        For clusters: directly deletes via cluster API.
        For instances: delegates to base class.
        """
        if self.resource_type == "cluster":
            resource_backend_id = waldur_resource.backend_id
            if not resource_backend_id or not resource_backend_id.strip():
                logger.warning("Empty backend_id for cluster resource, skipping deletion")
                return
            try:
                self.client.delete_compute_cluster(resource_backend_id)
            except NscaleAPIError as e:
                logger.exception("Failed to delete cluster %s: %s", resource_backend_id, e)
            return

        super().delete_resource(waldur_resource, **kwargs)

    def post_create_resource(
        self,
        backend_resource_info: BackendResourceInfo,
        waldur_resource: WaldurResource,
        user_context: Optional[dict] = None,
    ) -> None:
        """Update instance with proper specifications after creation."""
        del user_context
        resource_backend_id = backend_resource_info.backend_id

        nscale_limits, _ = self._collect_resource_limits(waldur_resource)
        if nscale_limits:
            logger.info("Updating instance %s with limits: %s", resource_backend_id, nscale_limits)
            self.client.set_resource_limits(resource_backend_id, nscale_limits)

    def _setup_resource_limits(
        self, resource_backend_id: str, waldur_resource: WaldurResource
    ) -> dict[str, int]:
        """Setup resource limits from Waldur resource."""
        nscale_limits, waldur_limits = self._collect_resource_limits(waldur_resource)

        if not nscale_limits:
            logger.info("Skipping setting of limits")
            return {}

        logger.info("Setting resource backend limits to: %s", nscale_limits)
        return waldur_limits
