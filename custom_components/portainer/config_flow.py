"""Config flow for the portainer integration."""

from collections.abc import Mapping
import logging
from typing import Any, override

import probatio
from pyportainer import (
    Portainer,
    PortainerAuthenticationError,
    PortainerConnectionError,
    PortainerTimeoutError,
)
from pyportainer.models.portainer import PortainerSystemStatus

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_TOKEN, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_ENDPOINTS,
    CONF_ENABLE_BUTTONS,
    CONF_ENABLE_CONTAINER_SENSORS,
    CONF_ENABLE_SWITCHES,
    CONF_ENABLE_UPDATES,
    CONF_ENABLE_VOLUMES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
STEP_USER_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
        probatio.Required(probatio.Secret(CONF_API_TOKEN)): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        probatio.Optional(CONF_VERIFY_SSL, default=True): BooleanSelector(),
    }
)


async def _validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> PortainerSystemStatus:
    """Validate the user input allows us to connect."""

    client = Portainer(
        api_url=data[CONF_URL],
        api_key=data[CONF_API_TOKEN],
        session=async_get_clientsession(hass=hass, verify_ssl=data[CONF_VERIFY_SSL]),
    )
    try:
        system_status = await client.portainer_system_status()
    except PortainerAuthenticationError:
        raise InvalidAuth from None
    except PortainerConnectionError as err:
        raise CannotConnect from err
    except PortainerTimeoutError as err:
        raise PortainerTimeout from err

    _LOGGER.debug("Connected to Portainer API: %s", data[CONF_URL])
    return system_status


class PortainerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Portainer."""

    VERSION = 5

    def __init__(self) -> None:
        """Initialize config flow."""
        self._init_data: dict[str, Any] = {}

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                system_status = await _validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except PortainerTimeout:
                errors["base"] = "timeout_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(system_status.instance_id)
                self._abort_if_unique_id_configured()
                self._init_data = user_input
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Prompt for options during initial setup."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._init_data[CONF_URL],
                data=self._init_data,
                options=user_input,
            )

        client = Portainer(
            api_url=self._init_data[CONF_URL],
            api_key=self._init_data[CONF_API_TOKEN],
            session=async_get_clientsession(
                hass=self.hass, verify_ssl=self._init_data[CONF_VERIFY_SSL]
            ),
        )
        endpoint_options: list[SelectOptionDict] = []
        try:
            endpoints = await client.get_endpoints()
            for ep in endpoints:
                endpoint_options.append(
                    SelectOptionDict(
                        value=str(ep.id),
                        label=f"{ep.name} (ID: {ep.id})",
                    )
                )
        except Exception as err:
            _LOGGER.warning("Could not fetch endpoints during setup: %s", err)

        all_endpoint_ids = [opt["value"] for opt in endpoint_options]
        schema_dict: dict[Any, Any] = {}
        if endpoint_options:
            schema_dict[
                probatio.Optional(
                    CONF_ENDPOINTS,
                    default=all_endpoint_ids,
                )
            ] = SelectSelector(
                SelectSelectorConfig(
                    options=endpoint_options,
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            )

        schema_dict.update(
            {
                probatio.Optional(CONF_ENABLE_VOLUMES, default=False): BooleanSelector(),
                probatio.Optional(CONF_ENABLE_UPDATES, default=False): BooleanSelector(),
                probatio.Optional(
                    CONF_ENABLE_CONTAINER_SENSORS, default=True
                ): BooleanSelector(),
                probatio.Optional(CONF_ENABLE_BUTTONS, default=True): BooleanSelector(),
                probatio.Optional(CONF_ENABLE_SWITCHES, default=True): BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="options",
            data_schema=probatio.Schema(schema_dict),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth when Portainer API authentication fails."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth: ask for new API token and validate."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            try:
                await _validate_input(
                    self.hass,
                    data={
                        **reauth_entry.data,
                        CONF_API_TOKEN: user_input[CONF_API_TOKEN],
                    },
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except PortainerTimeout:
                errors["base"] = "timeout_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_API_TOKEN: user_input[CONF_API_TOKEN]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=probatio.Schema(
                {
                    probatio.Required(probatio.Secret(CONF_API_TOKEN)): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        errors: dict[str, str] = {}
        reconf_entry = self._get_reconfigure_entry()
        suggested_values = {
            CONF_URL: reconf_entry.data[CONF_URL],
            CONF_API_TOKEN: reconf_entry.data[CONF_API_TOKEN],
            CONF_VERIFY_SSL: reconf_entry.data[CONF_VERIFY_SSL],
        }

        if user_input:
            try:
                system_status = await _validate_input(
                    self.hass,
                    data={
                        **reconf_entry.data,
                        **user_input,
                    },
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except PortainerTimeout:
                errors["base"] = "timeout_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(system_status.instance_id)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    reconf_entry,
                    data_updates={
                        CONF_URL: user_input[CONF_URL],
                        CONF_API_TOKEN: user_input[CONF_API_TOKEN],
                        CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                data_schema=STEP_USER_DATA_SCHEMA,
                suggested_values=user_input or suggested_values,
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return PortainerOptionsFlowHandler()


class PortainerOptionsFlowHandler(OptionsFlow):
    """Handle options flow for Portainer."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        endpoint_options: list[SelectOptionDict] = []
        coordinator = getattr(self.config_entry, "runtime_data", None)
        if coordinator and hasattr(coordinator, "portainer"):
            try:
                endpoints = await coordinator.portainer.get_endpoints()
                for ep in endpoints:
                    endpoint_options.append(
                        SelectOptionDict(
                            value=str(ep.id),
                            label=f"{ep.name} (ID: {ep.id})",
                        )
                    )
            except Exception as err:
                _LOGGER.warning(
                    "Could not fetch Portainer endpoints for options flow: %s", err
                )

        # Fallback if endpoints couldn't be fetched live via coordinator
        if not endpoint_options and self.config_entry:
            try:
                client = Portainer(
                    api_url=self.config_entry.data[CONF_URL],
                    api_key=self.config_entry.data[CONF_API_TOKEN],
                    session=async_get_clientsession(
                        hass=self.hass,
                        verify_ssl=self.config_entry.data.get(CONF_VERIFY_SSL, True),
                    ),
                )
                endpoints = await client.get_endpoints()
                for ep in endpoints:
                    endpoint_options.append(
                        SelectOptionDict(
                            value=str(ep.id),
                            label=f"{ep.name} (ID: {ep.id})",
                        )
                    )
            except Exception as err:
                _LOGGER.warning(
                    "Could not fetch Portainer endpoints via fallback client: %s", err
                )

        if not endpoint_options and coordinator and getattr(coordinator, "data", None):
            for ep_id, ep_data in coordinator.data.items():
                name = ep_data.name or f"Endpoint {ep_id}"
                endpoint_options.append(
                    SelectOptionDict(value=str(ep_id), label=f"{name} (ID: {ep_id})")
                )

        all_endpoint_ids = [opt["value"] for opt in endpoint_options]
        raw_saved_endpoints = self.config_entry.options.get(CONF_ENDPOINTS)
        if raw_saved_endpoints is not None:
            current_endpoints = [
                str(ep) for ep in raw_saved_endpoints if str(ep) in all_endpoint_ids
            ]
        else:
            current_endpoints = all_endpoint_ids

        schema_dict: dict[Any, Any] = {}
        if endpoint_options:
            schema_dict[
                probatio.Optional(
                    CONF_ENDPOINTS,
                    default=current_endpoints,
                )
            ] = SelectSelector(
                SelectSelectorConfig(
                    options=endpoint_options,
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            )

        schema_dict.update(
            {
                probatio.Optional(
                    CONF_ENABLE_VOLUMES,
                    default=self.config_entry.options.get(CONF_ENABLE_VOLUMES, False),
                ): BooleanSelector(),
                probatio.Optional(
                    CONF_ENABLE_UPDATES,
                    default=self.config_entry.options.get(CONF_ENABLE_UPDATES, False),
                ): BooleanSelector(),
                probatio.Optional(
                    CONF_ENABLE_CONTAINER_SENSORS,
                    default=self.config_entry.options.get(
                        CONF_ENABLE_CONTAINER_SENSORS, True
                    ),
                ): BooleanSelector(),
                probatio.Optional(
                    CONF_ENABLE_BUTTONS,
                    default=self.config_entry.options.get(CONF_ENABLE_BUTTONS, True),
                ): BooleanSelector(),
                probatio.Optional(
                    CONF_ENABLE_SWITCHES,
                    default=self.config_entry.options.get(CONF_ENABLE_SWITCHES, True),
                ): BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=probatio.Schema(schema_dict),
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class PortainerTimeout(Exception):
    """Error to indicate a timeout occurred."""
