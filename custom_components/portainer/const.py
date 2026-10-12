"""Constants for the Portainer integration."""

DOMAIN = "portainer"
DEFAULT_NAME = "Portainer"

API_MAX_RETRIES = 3

CONTAINER_STATE_ACTIONS = {
    "start",
    "stop",
    "die",
    "kill",
    "pause",
    "unpause",
    "restart",
    "oom",
    "update",
}

HEALTH_STATUS_VALUES = ("healthy", "unhealthy", "starting")

CONTAINER_STATE_EVENT_TYPES: tuple[str, ...] = tuple(
    sorted(CONTAINER_STATE_ACTIONS)
) + tuple(f"health_status_{value}" for value in HEALTH_STATUS_VALUES)

CONF_ENDPOINTS = "endpoints"
CONF_ENABLE_VOLUMES = "enable_volumes"
CONF_ENABLE_UPDATES = "enable_updates"
CONF_ENABLE_CONTAINER_SENSORS = "enable_container_sensors"
CONF_ENABLE_BUTTONS = "enable_buttons"
CONF_ENABLE_SWITCHES = "enable_switches"
