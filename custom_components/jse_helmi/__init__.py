from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL_MINUTES, CONF_UPDATE_MINUTE, DEFAULT_UPDATE_MINUTE
from .coordinator import JSECoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = {**entry.data, **entry.options}
    coordinator = JSECoordinator(
        hass,
        config,
        update_interval=timedelta(minutes=DEFAULT_UPDATE_INTERVAL_MINUTES),
    )
    await coordinator.async_config_entry_first_refresh()
    update_minute = int(config.get(CONF_UPDATE_MINUTE, DEFAULT_UPDATE_MINUTE))

    async def _schedule_refresh(*_args) -> None:
        await coordinator.async_request_refresh()

    unsub = async_track_time_change(hass, _schedule_refresh, minute=update_minute, second=0)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "unsub": unsub,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if data and data.get("unsub"):
            data["unsub"]()
    return unload_ok
