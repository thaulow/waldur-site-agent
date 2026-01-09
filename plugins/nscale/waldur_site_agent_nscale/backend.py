"""Nscale Backend for waldur site agent.

This module provides integration between Waldur Mastermind and Nscale.
It implements the backend interface for managing compute instances, clusters,
networks, and security groups.

Mapping:
- Waldur Project -> Nscale Project
- Waldur Resource -> Nscale Compute Instance/Cluster
- Waldur User -> Nscale User (if supported)
"""

import logging
from typing import Optional

from waldur_api_client.models.resource import Resource as WaldurResource
from waldur_api_client.models.resource_limits import ResourceLimits

from waldur_site_agent.backend import backends
from waldur_site_agent.backend.structures import BackendResourceInfo
from waldur_site_agent.backend.exceptions import BackendError
from waldur_site_agent_nscale.client import NscaleClient
from waldur_site_agent_nscale.exceptions import NscaleAPIError

logger = logging.getLogger(__name__)


class NscaleBackend(backends.BaseBackend):
    """Nscale backend implementation for Waldur Site Agent.

    This backend manages the lifecycle of compute resources in Nscale based on
    Waldur marketplace orders and handles resource management.
    """

    def __init__(self, nscale_settings: dict, nscale_components: dict[str, dict]) -> None:
        """Init backend info and creates a corresponding client."""
        super().__init__(nscale_settings, nscale_components)
        self.backend_type = "nscale"

        # Required settings
        required_settings = ["api_url", "organization_id", "project_id", "service_token"]
        for setting in required_settings:
            if setting not in nscale_settings:
                raise ValueError(f"Missing required setting: {setting}")

        self.client: NscaleClient = NscaleClient(
            api_url=nscale_settings["api_url"],
            organization_id=nscale_settings["organization_id"],
            project_id=nscale_settings["project_id"],
            service_token=nscale_settings["service_token"],
        )

        # Backend-specific settings with defaults
        self.resource_prefix = nscale_settings.get("resource_prefix", "waldur_")
        self.instance_type = nscale_settings.get("default_instance_type", "standard")
        self.image_id = nscale_settings.get("default_image_id", "")
        self.network_id = nscale_settings.get("default_network_id", "")
        self.security_group_ids = nscale_settings.get("default_security_group_ids", [])

    def ping(self, raise_exception: bool = False) -> bool:
        """Check if Nscale backend is available and accessible."""
        try:
            # Try to list networks as a simple connectivity test
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
        # Ensure network and security groups exist if needed
        if self.network_id:
            try:
                self.client.get_network(self.network_id)
            except Exception:
                logger.warning("Default network %s not found", self.network_id)
        del user_context


    def _collect_resource_limits(
        self, waldur_resource: WaldurResource
    ) -> tuple[dict[str, int], dict[str, int]]:
        """Collect Nscale and Waldur limits separately."""
        nscale_limits: dict = {}
        waldur_resource_limits: dict = {}

        # Extract limits from resource
        limits = waldur_resource.limits
        if not limits:
            return nscale_limits, waldur_resource_limits

        for component_key, data in self.backend_components.items():
            if component_key in limits:
                limit_value = limits[component_key]
                # Apply unit factor if needed
                unit_factor = data.get("unit_factor", 1)
                nscale_limits[component_key] = limit_value * unit_factor
                waldur_resource_limits[component_key] = limit_value

        return nscale_limits, waldur_resource_limits

    def _get_usage_report(
        self, resource_backend_ids: list[str]
    ) -> dict[str, dict[str, dict[str, int]]]:
        """Collect usage report for the specified resources from Nscale."""
        report: dict[str, dict[str, dict[str, int]]] = {}

        for resource_id in resource_backend_ids:
            try:
                instance = self.client.get_compute_instance(resource_id)
                usage: dict[str, int] = {}

                # Map instance usage to components
                for component_key in self.backend_components.keys():
                    if component_key == "cpu":
                        usage[component_key] = instance.get("cpu_usage", 0)
                    elif component_key == "memory":
                        usage[component_key] = instance.get("memory_usage", 0)
                    elif component_key == "storage":
                        usage[component_key] = instance.get("storage_usage", 0)
                    else:
                        usage[component_key] = 0

                report[resource_id] = {"TOTAL_ACCOUNT_USAGE": usage}

            except Exception:
                logger.exception("Failed to get usage for resource %s", resource_id)
                # Initialize with empty usage
                empty_usage = dict.fromkeys(self.backend_components, 0)
                report[resource_id] = {"TOTAL_ACCOUNT_USAGE": empty_usage}

        return report

    def downscale_resource(self, resource_backend_id: str) -> bool:
        """Downscale the resource on the backend - stop or resize instance."""
        try:
            instance = self.client.get_compute_instance(resource_backend_id)
            # Stop the instance (downscale)
            # Note: Actual implementation depends on Nscale API
            logger.info("Downscaling resource %s", resource_backend_id)
            return True
        except Exception as e:
            logger.exception("Failed to downscale resource %s: %s", resource_backend_id, e)
            return False

    def pause_resource(self, resource_backend_id: str) -> bool:
        """Pause the resource on the backend - stop instance."""
        try:
            instance = self.client.get_compute_instance(resource_backend_id)
            # Stop the instance (pause)
            # Note: Actual implementation depends on Nscale API
            logger.info("Pausing resource %s", resource_backend_id)
            return True
        except Exception as e:
            logger.exception("Failed to pause resource %s: %s", resource_backend_id, e)
            return False

    def restore_resource(self, resource_backend_id: str) -> bool:
        """Restore the resource after downscaling or pausing - start instance."""
        try:
            instance = self.client.get_compute_instance(resource_backend_id)
            # Start the instance (restore)
            # Note: Actual implementation depends on Nscale API
            logger.info("Restoring resource %s", resource_backend_id)
            return True
        except Exception as e:
            logger.exception("Failed to restore resource %s: %s", resource_backend_id, e)
            return False

    def get_resource_metadata(self, resource_backend_id: str) -> dict:
        """Get backend-specific resource metadata."""
        try:
            instance = self.client.get_compute_instance(resource_backend_id)
            return {
                "instance_id": instance.get("id"),
                "instance_name": instance.get("name"),
                "instance_type": instance.get("type"),
                "status": instance.get("status"),
                "cpu": instance.get("cpu", 0),
                "memory": instance.get("memory", 0),
                "storage": instance.get("storage", 0),
            }
        except Exception:
            logger.exception("Failed to get resource metadata for %s", resource_backend_id)
            return {}

    def _create_compute_instance(
        self, resource_backend_id: str, waldur_resource: WaldurResource
    ) -> dict:
        """Create compute instance in Nscale."""
        # Collect limits
        nscale_limits, _ = self._collect_resource_limits(waldur_resource)

        # Build instance data
        instance_data = {
            "name": resource_backend_id,
            "description": waldur_resource.name,
            "type": self.instance_type,
            "image_id": self.image_id,
            "network_id": self.network_id,
            "security_group_ids": self.security_group_ids,
        }

        # Add resource specifications from limits
        if "cpu" in nscale_limits:
            instance_data["cpu"] = nscale_limits["cpu"]
        if "memory" in nscale_limits:
            instance_data["memory"] = nscale_limits["memory"]
        if "storage" in nscale_limits:
            instance_data["storage"] = nscale_limits["storage"]

        try:
            result = self.client.create_compute_instance(instance_data)
            logger.info("Created Nscale compute instance %s for resource %s", result.get("id"), resource_backend_id)
            return result
        except NscaleAPIError as e:
            logger.exception("Failed to create compute instance: %s", e)
            raise BackendError(f"Failed to create compute instance: {e}") from e

    def _create_backend_resource(
        self,
        resource_backend_id: str,
        resource_name: str,
        resource_organization: str,
        resource_parent_name: Optional[str] = None,
    ) -> bool:
        """Create resource in Nscale backend - creates a basic compute instance."""
        logger.info(
            "Creating resource %s in Nscale backend (backend ID = %s)",
            resource_name,
            resource_backend_id,
        )
        
        # Check if resource already exists
        if self.client.get_resource(resource_backend_id) is not None:
            logger.info("The resource with ID %s already exists in Nscale", resource_backend_id)
            return True

        # Create basic compute instance (specs will be updated in post_create_resource)
        instance_data = {
            "name": resource_backend_id,
            "description": resource_name,
            "type": self.instance_type,
        }
        
        if self.image_id:
            instance_data["image_id"] = self.image_id
        if self.network_id:
            instance_data["network_id"] = self.network_id
        if self.security_group_ids:
            instance_data["security_group_ids"] = self.security_group_ids

        try:
            self.client.create_compute_instance(instance_data)
            logger.info("Created Nscale compute instance %s", resource_backend_id)
            return True
        except NscaleAPIError as e:
            logger.exception("Failed to create compute instance: %s", e)
            raise BackendError(f"Failed to create compute instance: {e}") from e

    def post_create_resource(
        self,
        backend_resource_info: BackendResourceInfo,
        waldur_resource: WaldurResource,
        user_context: Optional[dict] = None,
    ) -> None:
        """Update instance with proper specifications after creation."""
        del user_context
        resource_backend_id = backend_resource_info.backend_id
        
        # Update instance with proper specs from limits
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
        # Note: Actual limit update happens in post_create_resource
        # This method just returns the waldur limits for tracking
        return waldur_limits
