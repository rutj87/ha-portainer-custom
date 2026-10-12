"""Test unique ID scoping and automatic legacy entity cleanup."""

from unittest.mock import MagicMock

import pytest

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.portainer import async_cleanup_excluded_entities
from custom_components.portainer.const import DOMAIN


@pytest.mark.asyncio
async def test_legacy_entity_cleanup_and_name_restoration(hass):
    """Test that legacy un-scoped entities are removed and _2 suffixes restored."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="test-instance-12345",
        data={},
        options={},
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.data = {7: MagicMock()}
    entry.runtime_data = coordinator

    entity_registry = er.async_get(hass)

    # 1. Register a legacy un-scoped entity (v1.0.0 format)
    legacy_entity = entity_registry.async_get_or_create(
        domain="binary_sensor",
        platform=DOMAIN,
        unique_id=f"{entry.entry_id}_omada-controller_status",
        suggested_object_id="omada_controller_running",
        config_entry=entry,
    )
    assert legacy_entity.entity_id == "binary_sensor.omada_controller_running"

    # 2. Register a new scoped entity (v1.0.1 format), which took _2 suffix
    new_entity = entity_registry.async_get_or_create(
        domain="binary_sensor",
        platform=DOMAIN,
        unique_id=f"{entry.entry_id}_7_omada-controller_status",
        suggested_object_id="omada_controller_running",
        config_entry=entry,
    )
    assert new_entity.entity_id == "binary_sensor.omada_controller_running_2"

    # Run cleanup
    async_cleanup_excluded_entities(hass, entry)

    # Verify legacy un-scoped entity was purged from the registry
    assert (
        entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_omada-controller_status"
        )
        is None
    )

    # Verify new entity reclaimed the clean original entity_id
    restored = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_7_omada-controller_status"
    )
    assert restored == "binary_sensor.omada_controller_running"
