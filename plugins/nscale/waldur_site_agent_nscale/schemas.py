"""Nscale plugin-specific Pydantic schemas for configuration validation.

This module defines validation schemas for Nscale-specific configuration fields.
"""

from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict, Field, field_validator

from waldur_site_agent.common.plugin_schemas import (
    PluginBackendSettingsSchema,
    PluginComponentSchema,
)


class NscaleComponentSchema(PluginComponentSchema):
    """Nscale-specific component field validation.

    Validates component-level configuration for Nscale resources.
    """

    model_config = ConfigDict(extra="allow")  # Allow core fields to pass through


class NscaleBackendSettingsSchema(PluginBackendSettingsSchema):
    """Nscale-specific backend settings validation.

    Validates Nscale backend configuration settings.
    """

    model_config = ConfigDict(extra="allow")  # Allow additional settings

    # Required settings
    api_url: str = Field(..., description="Base URL for Nscale API")
    organization_id: str = Field(..., description="Nscale organization ID")
    project_id: str = Field(..., description="Nscale project ID")
    service_token: str = Field(..., description="Service token for API authentication")

    # Optional settings
    resource_prefix: Optional[str] = Field(
        default="waldur_", description="Prefix for resource names"
    )
    default_instance_type: Optional[str] = Field(
        default="standard", description="Default instance type for compute resources"
    )
    default_image_id: Optional[str] = Field(
        default=None, description="Default image ID for compute instances"
    )
    default_network_id: Optional[str] = Field(
        default=None, description="Default network ID to use for resources"
    )
    default_security_group_ids: Optional[list[str]] = Field(
        default=None, description="List of default security group IDs"
    )
    resource_type: Optional[str] = Field(
        default="instance",
        description="Resource type to manage: 'instance' (default) or 'cluster'",
    )
    identity_api_url: Optional[str] = Field(
        default=None,
        description="Base URL for NScale Identity API (for user management)",
    )

    @field_validator("api_url")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        """Validate that API URL is a valid HTTP/HTTPS URL."""
        if not v.startswith(("http://", "https://")):
            msg = "api_url must start with http:// or https://"
            raise ValueError(msg)
        return v.rstrip("/")
