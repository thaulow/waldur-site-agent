"""Shared test fixtures for NScale plugin tests."""

import pytest
from uuid import uuid4

from waldur_api_client.models.offering_user import OfferingUser
from waldur_api_client.models.resource import Resource as WaldurResource


@pytest.fixture
def nscale_settings():
    """Basic NScale settings for testing."""
    return {
        "api_url": "https://compute.nks.example.com",
        "organization_id": "org-test-123",
        "project_id": "proj-test-456",
        "service_token": "test-token-abc",  # noqa: S106
        "identity_api_url": "https://identity.nks.example.com",
        "resource_prefix": "waldur_",
        "default_instance_type": "g-4-standard",
        "default_image_id": "ubuntu-22.04",
        "default_network_id": "net-test-789",
        "default_security_group_ids": ["sg-default", "sg-ssh"],
    }


@pytest.fixture
def nscale_settings_no_identity():
    """NScale settings without Identity API."""
    return {
        "api_url": "https://compute.nks.example.com",
        "organization_id": "org-test-123",
        "project_id": "proj-test-456",
        "service_token": "test-token-abc",  # noqa: S106
    }


@pytest.fixture
def nscale_components():
    """Component definitions for testing."""
    return {
        "cpu": {
            "measured_unit": "core-hours",
            "unit_factor": 1,
            "accounting_type": "limit",
            "label": "CPU Cores",
        },
        "memory": {
            "measured_unit": "GB-hours",
            "unit_factor": 1,
            "accounting_type": "limit",
            "label": "Memory",
        },
        "storage": {
            "measured_unit": "GB",
            "unit_factor": 1,
            "accounting_type": "limit",
            "label": "Storage",
        },
        "gpu": {
            "measured_unit": "gpu-hours",
            "unit_factor": 1,
            "accounting_type": "limit",
            "label": "GPU Hours",
        },
    }


class MockResourceLimits:
    """Mock ResourceLimits for testing."""

    def __init__(self):
        self.cpu = 4
        self.memory = 8
        self.storage = 100
        self.gpu = 1

    def to_dict(self):
        return {
            "cpu": self.cpu,
            "memory": self.memory,
            "storage": self.storage,
            "gpu": self.gpu,
        }

    def __contains__(self, key):
        return key in self.to_dict()

    def __getitem__(self, key):
        return self.to_dict()[key]


@pytest.fixture
def waldur_resource():
    """Sample Waldur resource for testing."""
    return WaldurResource(
        uuid=uuid4(),
        name="Test NScale Resource",
        slug="test-nscale-resource",
        customer_slug="test-customer",
        project_slug="test-project",
        backend_id="",
        limits=MockResourceLimits(),
    )


@pytest.fixture
def offering_user():
    """Sample offering user for testing."""
    return OfferingUser(
        username="testuser",
        user_full_name="Test User",
        user_email="test@example.com",
    )


SAMPLE_INSTANCE = {
    "metadata": {"id": "inst-001", "name": "test-instance"},
    "spec": {
        "flavorId": "g-4-standard",
        "imageId": "ubuntu-22.04",
        "cpu": 4,
        "memory": 8,
        "storage": 100,
    },
    "status": {
        "powerState": "running",
        "provisioningStatus": "provisioned",
    },
}

SAMPLE_CLUSTER = {
    "metadata": {"id": "cluster-001", "name": "test-cluster"},
    "spec": {
        "workloadPools": [
            {"name": "pool-1", "replicas": 3, "flavorId": "g-4-standard"}
        ]
    },
    "status": {"provisioningStatus": "provisioned"},
}

SAMPLE_NSCALE_USER = {
    "metadata": {"id": "user-001", "name": "testuser"},
    "spec": {"subject": "testuser", "state": "active"},
}

SAMPLE_GROUP = {
    "metadata": {"id": "group-001", "name": "inst-001"},
    "spec": {"userIds": ["user-001"]},
}
