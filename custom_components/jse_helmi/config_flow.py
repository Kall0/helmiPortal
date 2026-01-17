from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import JSEApi
from .const import (
    CONF_CUTOFF_HOUR,
    CONF_CUSTOMER_ID,
    CONF_EMAIL,
    CONF_METERING_POINT_ID,
    CONF_PASSWORD,
    CONF_STALE_HOURS,
    CONF_UPDATE_MINUTE,
    DEFAULT_CUTOFF_HOUR,
    DEFAULT_STALE_HOURS,
    DEFAULT_UPDATE_MINUTE,
    DOMAIN,
)


class JSEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None
        self._customer_ids: list[str] = []
        self._metering_point_ids: list[str] = []
        self._selected_customer_id: str | None = None

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            try:
                await self._async_discover()
            except Exception:
                errors["base"] = "auth_failed"
            else:
                if len(self._customer_ids) > 1:
                    return await self.async_step_customer()
                if len(self._customer_ids) == 1:
                    self._selected_customer_id = self._customer_ids[0]
                    await self._async_set_metering_points(self._selected_customer_id)
                    if len(self._metering_point_ids) > 1:
                        return await self.async_step_metering_point()
                    return self._create_entry(
                        self._selected_customer_id,
                        self._metering_point_ids[0] if self._metering_point_ids else "",
                    )
                errors["base"] = "no_customers"

        schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_customer(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            customer_id = user_input[CONF_CUSTOMER_ID]
            self._selected_customer_id = customer_id
            await self._async_set_metering_points(customer_id)
            if len(self._metering_point_ids) > 1:
                return await self.async_step_metering_point()
            return self._create_entry(
                customer_id, self._metering_point_ids[0] if self._metering_point_ids else ""
            )

        return self.async_show_form(
            step_id="customer",
            data_schema=vol.Schema(
                {vol.Required(CONF_CUSTOMER_ID): vol.In(self._customer_ids)}
            ),
        )

    async def async_step_metering_point(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self._create_entry(
                self._selected_customer_id or self._customer_ids[0],
                user_input[CONF_METERING_POINT_ID],
            )

        return self.async_show_form(
            step_id="metering_point",
            data_schema=vol.Schema(
                {vol.Required(CONF_METERING_POINT_ID): vol.In(self._metering_point_ids)}
            ),
        )

    def _create_entry(self, customer_id: str, metering_point_id: str) -> FlowResult:
        return self.async_create_entry(
            title=f"JSE Helmi {metering_point_id or customer_id}",
            data={
                CONF_EMAIL: self._email,
                CONF_PASSWORD: self._password,
                CONF_CUSTOMER_ID: customer_id,
                CONF_METERING_POINT_ID: metering_point_id,
            },
        )

    async def _async_discover(self) -> None:
        api = JSEApi(email=self._email or "", password=self._password or "")
        sub = await self.hass.async_add_executor_job(api.get_user_sub)
        self._customer_ids = await self.hass.async_add_executor_job(
            api.get_customer_ids, sub
        )

    async def _async_set_metering_points(self, customer_id: str) -> None:
        api = JSEApi(email=self._email or "", password=self._password or "")
        self._metering_point_ids = await self.hass.async_add_executor_job(
            api.get_metering_point_ids, customer_id
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return JSEOptionsFlow(config_entry)


class JSEOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CUSTOMER_ID, default=self._entry.data.get(CONF_CUSTOMER_ID)
                    ): str,
                    vol.Required(
                        CONF_METERING_POINT_ID,
                        default=self._entry.data.get(CONF_METERING_POINT_ID),
                    ): str,
                    vol.Required(
                        CONF_CUTOFF_HOUR,
                        default=self._entry.options.get(CONF_CUTOFF_HOUR, DEFAULT_CUTOFF_HOUR),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
                    vol.Required(
                        CONF_UPDATE_MINUTE,
                        default=self._entry.options.get(
                            CONF_UPDATE_MINUTE, DEFAULT_UPDATE_MINUTE
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
                    vol.Required(
                        CONF_STALE_HOURS,
                        default=self._entry.options.get(
                            CONF_STALE_HOURS, DEFAULT_STALE_HOURS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
                }
            ),
        )
