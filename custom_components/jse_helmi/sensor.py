from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import ConsumptionData, JSECoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: JSECoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            JSEConsumptionSensor(coordinator),
            JSEDailyTotalSensor(coordinator),
        ]
    )


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


class JSEDailyTotalSensor(CoordinatorEntity[JSECoordinator], SensorEntity):
    _attr_name = "JSE Helmi Consumption (Daily Total)"
    _attr_unit_of_measurement = "kWh"
    _attr_device_class = "energy"
    _attr_state_class = "total_increasing"

    def __init__(self, coordinator: JSECoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"jse_helmi_consumption_daily_{coordinator.data.metering_point_id}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.data.metering_point_id)},
            name=f"JSE Helmi {coordinator.data.metering_point_id}",
            manufacturer="JSE",
        )
        self._total = 0.0
        self._last_day: Optional[date] = None

    @property
    def native_value(self) -> Optional[float]:
        if self._last_day is None:
            return None
        return self._total

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "last_day": self._last_day.isoformat() if self._last_day else None,
        }

    def _handle_coordinator_update(self) -> None:
        data: ConsumptionData = self.coordinator.data
        now_local = dt_util.as_local(dt_util.now())
        cutoff = datetime.combine(now_local.date(), time(5, 0, 0, tzinfo=now_local.tzinfo))
        if now_local < cutoff:
            # Before cutoff, keep the previous total.
            self.async_write_ha_state()
            return

        target_day = (now_local - timedelta(days=1)).date()
        total = 0.0
        for point in data.series:
            parsed = dt_util.parse_datetime(point.timestamp) if point.timestamp else None
            if not parsed:
                continue
            local_dt = dt_util.as_local(parsed)
            if local_dt.date() == target_day:
                if point.value is not None:
                    total += float(point.value)

        if self._last_day != target_day:
            # New day, increment the running total.
            self._total += total
            self._last_day = target_day

        self.async_write_ha_state()
