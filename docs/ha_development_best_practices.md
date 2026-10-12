# Home Assistant Integration Development: Architectural Best Practices

This guide outlines core architectural principles, best practices, and integration quality scale requirements for developing Home Assistant integrations—highlighting the trade-offs between **Upstream Core Contributions (`home-assistant/core`)** and **Power-User Custom Component Forks (HACS)**.

---

## 1. Config Flow vs. Options Flow Architecture

### Core Design Philosophy
Home Assistant strictly separates **onboarding** from **configuration tuning**:
* **Config Flow (`ConfigFlow`)**: Dedicated exclusively to authentication, discovery, and establishing a valid connection. It should only ask for the **minimum viable information** needed to connect.
* **Options Flow (`OptionsFlow`)**: Dedicated to user preferences, polling adjustments, device filtering, and feature tuning *after* the initial connection is established.

### Best Practice Implementation (HA 2024.12+ / 2026.x)
In modern Home Assistant Core, `OptionsFlow.config_entry` is a framework-managed read-only property. 

#### Recommended Pattern:
```python
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback

class MyConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return options flow handler instance without arguments."""
        return MyOptionsFlowHandler()


class MyOptionsFlowHandler(OptionsFlow):
    """Handle options flow."""

    # DO NOT define __init__(self, config_entry) or attempt self.config_entry = config_entry.
    # self.config_entry is dynamically provided by the base OptionsFlow class.

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Access current entry options safely
        current_options = self.config_entry.options
        ...
```

### Auto-Reload on Option Change
When options are modified, the integration must reload to apply changes:
* **Option A (`OptionsFlowWithReload`)**: Subclass `OptionsFlowWithReload` instead of `OptionsFlow` (built-in automatic reload).
* **Option B (Update Listener)**: In `__init__.py`, register an update listener during entry setup:
  ```python
  entry.async_on_unload(entry.add_update_listener(async_reload_entry))
  ```

---

## 2. Entity Management & The Integration Quality Scale

### The Core Architectural Rule: Entity Registry vs. Options Toggles
One of the most frequent review rejections in `home-assistant/core` is adding boolean switches in `OptionsFlow` to enable/disable entire entity domains (e.g., `enable_sensors`, `enable_switches`, `enable_buttons`).

* **Upstream Guideline**: Home Assistant already provides native entity-level and category-level disabling in **Settings > Devices & Services > Entities**. Core policy states: *"Integrations must not replicate core entity registry controls in options flows."*
* **Custom Fork Approach**: For personal custom components, options toggles (e.g., completely skipping switch or sensor platforms) provide significant convenience and prevent hundreds of unwanted entities from ever polluting the database.

### Handling High-Cardinality & "Noisy" Entities
For integrations with high entity counts (such as Portainer reporting 700+ Docker anonymous volume hashes):

#### The Upstream Standard (`entity_registry_enabled_default = False`):
```python
class PortainerVolumeSizeSensor(PortainerVolumeEntity, SensorEntity):
    """Volume size sensor."""

    # Disabled by default so it does not clutter the state machine or recorder
    _attr_entity_registry_enabled_default = False
```
* **Why**: The entities are registered in Home Assistant, but their states are not tracked, polled, or saved to the recorder database unless the user manually enables them in the UI.

#### When an Options Toggle IS Justified Upstream:
An options toggle is permitted upstream if disabling the feature **prevents heavy background network calls or expensive API polling** (e.g., skipping `docker system df` polling entirely if volume monitoring is disabled).

---

## 3. Unique ID Scoping & Non-Breaking Migrations

### The Golden Rule of Unique IDs
> **Every entity and device unique ID must remain globally unique and permanently immutable across its entire lifecycle.**

### Multi-Host & Multi-Environment Scoping
If an integration connects to a controller, hub, or management platform that monitors multiple sub-hosts or environments (like Portainer, Proxmox, or UniFi):
* **Anti-Pattern**: Using `{entry_id}_{container_name}_{key}`. If two separate servers run a container named `portainer_agent` or `nginx`, Home Assistant will log duplicate unique ID errors and discard one.
* **Best Practice**: Include the endpoint/host identifier:
  ```python
  self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.endpoint_id}_{self.device_name}_{entity_description.key}"
  ```

### Handling Unique ID Updates (Schema Migration)
If unique ID formatting must be changed to fix collisions, **you must never simply change the string** in an existing integration without a migration. Doing so orphans all existing user entities and creates duplicate `_2` entity IDs.

#### Mandatory Migration Pattern:
1. Increment `VERSION` on `ConfigFlow`:
   ```python
   class PortainerConfigFlow(ConfigFlow, domain=DOMAIN):
       VERSION = 6
   ```
2. Implement `async_migrate_entry` in `__init__.py`:
   ```python
   async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
       """Migrate config entry to newer version."""
       if entry.version < 6:
           entity_registry = er.async_get(hass)
           entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
           for entity in entries:
               # Rewrite old unique IDs to new format
               new_unique_id = migrate_id(entity.unique_id)
               entity_registry.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)
           hass.config_entries.async_update_entry(entry, version=6)
       return True
   ```

---

## 4. Device Topology & Clean Lifecycle Pruning

### Device Hierarchy (`via_device_id`)
Represent real-world hierarchy using `via_device_id`:
```
Portainer Instance (Config Entry)
   └── Endpoint (Host / Machine)
         └── Stack (Compose Group)
               └── Container (Service)
```
Entities should link to the most granular device, and each sub-device links upward via its parent's device ID.

### Clean Entity Registry Cleanup
When users deselect endpoints or disable features in `OptionsFlow`, clean up the registry so entities don't become permanently "stale" or "unavailable":
```python
@callback
def async_cleanup_excluded_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    
    # 1. Remove entities belonging to deselected endpoints
    for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if is_excluded(entity):
            entity_registry.async_remove(entity.entity_id)

    # 2. Remove orphaned devices belonging to deselected endpoints
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        if is_device_excluded(device):
            device_registry.async_remove_device(device.id)
```

---

## 5. UI Elements & `strings.json`

Every option and config step exposed to the user must be defined with translation strings in `strings.json`:
* Use **Selectors** (`SelectSelector`, `BooleanSelector`) rather than raw voluptuous primitives (`bool`, `vol.In`).
* Provide `data_description` for each field to give users context on the impact of changing the setting.

Example schema definition:
```json
{
  "options": {
    "step": {
      "init": {
        "title": "Portainer Options",
        "description": "Configure monitored endpoints and entity types.",
        "data": {
          "endpoints": "Endpoints to monitor",
          "enable_volumes": "Enable Docker volume entities"
        },
        "data_description": {
          "endpoints": "Deselecting an endpoint removes all its containers and devices.",
          "enable_volumes": "Warning: Can create hundreds of anonymous volume entities."
        }
      }
    }
  }
}
```

---

## 6. Decision Matrix: Custom Fork vs. Upstream Core PR

| Feature / Behavior | Custom Fork (`ha-portainer-custom`) | Upstream PR (`home-assistant/core`) |
| :--- | :--- | :--- |
| **Endpoint Selection** | Multi-select list in `OptionsFlow` | Multi-select list in `OptionsFlow` (Standard & Approved) |
| **Anonymous Volume Clutter** | Boolean toggle (`enable_volumes: false`) | `_attr_entity_registry_enabled_default = False` in `sensor.py` |
| **Entity Domain Toggles** | Boolean switches for sensors/buttons/switches | **Forbidden**; handled via native Home Assistant Entity Registry |
| **Setup Wizard Behavior** | Routes to `async_step_options` immediately | Single-step; settings tuned via **Configure** button post-setup |
| **Unique ID Migration** | Updated in-place with auto-cleanup | Requires formal `async_migrate_entry` to bump `VERSION` |
| **Maintenance & Currency** | Syncs from upstream `main` via automated CI/CD | Subject to Home Assistant Core merge approval & release cycle |
