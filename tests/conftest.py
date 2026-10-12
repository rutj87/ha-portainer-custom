"""Fixtures for Portainer tests."""

from unittest.mock import AsyncMock, patch

import pytest
from pyportainer.models.portainer import Endpoint, SystemStatus

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_portainer_client():
    """Mock the Portainer API client."""
    with patch("custom_components.portainer.config_flow.Portainer") as mock_client_cls, \
         patch("custom_components.portainer.Portainer") as mock_init_client_cls:
        client = AsyncMock()
        client.portainer_system_status.return_value = SystemStatus(
            instance_id="test-instance-12345",
            version="2.21.0",
        )
        endpoint_1 = Endpoint(
            id=7,
            name="Omada Pi",
            status=1,
            type=1,
            url="tcp://192.168.86.107:9001",
        )
        endpoint_2 = Endpoint(
            id=8,
            name="Ubuntu VM",
            status=1,
            type=1,
            url="tcp://192.168.86.108:9001",
        )
        client.get_endpoints.return_value = [endpoint_1, endpoint_2]
        mock_client_cls.return_value = client
        mock_init_client_cls.return_value = client
        yield client
