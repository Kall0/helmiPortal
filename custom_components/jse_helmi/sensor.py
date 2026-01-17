from __future__ import annotations

from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ConsumptionData, JSECoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: JSECoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([JSEConsumptionSensor(coordinator)])


class JSEConsumptionSensor(CoordinatorEntity[JSECoordinator], SensorEntity):
    _attr_name = "JSE Helmi Consumption (Hourly)"
    _attr_unit_of_measurement = "kWh"
    _attr_device_class = "energy"
    _attr_state_class = "measurement"

    def __init__(self, coordinator: JSECoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"jse_helmi_consumption_hourly_{coordinator.data.metering_point_id}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.data.metering_point_id)},
            name=f"JSE Helmi {coordinator.data.metering_point_id}",
            manufacturer="JSE",
        )

    @property
    def native_value(self) -> Optional[float]:
        data: ConsumptionData = self.coordinator.data
        if not data.series:
            return None
        return data.series[-1].value

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data: ConsumptionData = self.coordinator.data
        return {
            "customer_id": data.customer_id,
            "metering_point_id": data.metering_point_id,
            "unit": data.unit,
            "series": [
                {"ts": point.timestamp, "value": point.value}
                for point in data.series
            ],
        }
