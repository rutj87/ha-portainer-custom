"""Test the Portainer config flow and options flow."""

from unittest.mock import patch
import pytest

from homeassistant import config_entries
from homeassistant.const import CONF_URL, CONF_VERIFY_SSL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.portainer.const import (
    CONF_API_TOKEN,
    CONF_ENABLE_BUTTONS,
    CONF_ENABLE_CONTAINER_SENSORS,
    CONF_ENABLE_SWITCHES,
    CONF_ENABLE_UPDATES,
    CONF_ENABLE_VOLUMES,
    CONF_ENDPOINTS,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_full_config_flow_with_options_step(hass, mock_portainer_client):
    """Test user step connects and routes directly to options step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    # Fill in connection details
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: "http://192.168.86.107:9001",
            CONF_API_TOKEN: "valid-token-secret",
            CONF_VERIFY_SSL: False,
        },
    )
    # Must immediately transition to options step
    assert result["type"] == "form"
    assert result["step_id"] == "options"

    # Submit options
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ENDPOINTS: ["7"],
            CONF_ENABLE_VOLUMES: False,
            CONF_ENABLE_UPDATES: False,
            CONF_ENABLE_CONTAINER_SENSORS: True,
            CONF_ENABLE_BUTTONS: True,
            CONF_ENABLE_SWITCHES: True,
        },
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "http://192.168.86.107:9001"
    assert result["data"] == {
        CONF_URL: "http://192.168.86.107:9001",
        CONF_API_TOKEN: "valid-token-secret",
        CONF_VERIFY_SSL: False,
    }
    assert result["options"] == {
        CONF_ENDPOINTS: ["7"],
        CONF_ENABLE_VOLUMES: False,
        CONF_ENABLE_UPDATES: False,
        CONF_ENABLE_CONTAINER_SENSORS: True,
        CONF_ENABLE_BUTTONS: True,
        CONF_ENABLE_SWITCHES: True,
    }


@pytest.mark.asyncio
async def test_options_flow_handler(hass, mock_portainer_client):
    """Test options flow opens without AttributeError and updates settings."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="test-instance-12345",
        data={
            CONF_URL: "http://192.168.86.107:9001",
            CONF_API_TOKEN: "valid-token-secret",
            CONF_VERIFY_SSL: False,
        },
        options={
            CONF_ENDPOINTS: ["7", "8"],
            CONF_ENABLE_VOLUMES: True,
            CONF_ENABLE_UPDATES: False,
        },
    )
    entry.add_to_hass(hass)

    # Initialize options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Save new options (e.g. disable volumes and select only endpoint 7)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_ENDPOINTS: ["7"],
            CONF_ENABLE_VOLUMES: False,
            CONF_ENABLE_UPDATES: False,
            CONF_ENABLE_CONTAINER_SENSORS: True,
            CONF_ENABLE_BUTTONS: True,
            CONF_ENABLE_SWITCHES: True,
        },
    )
    assert result["type"] == "create_entry"
    assert entry.options[CONF_ENDPOINTS] == ["7"]
    assert entry.options[CONF_ENABLE_VOLUMES] is False
