from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import ConsumptionData, JSECoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: JSECoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [
            JSEConsumptionSensor(coordinator),
            JSEHourlyTotalSensor(coordinator),
            JSEDailyTotalSensor(coordinator),
        ]
    )


class JSEConsumptionSensor(CoordinatorEntity[JSECoordinator], SensorEntity):
    _attr_name = "JSE Helmi Consumption (Hourly)"
    _attr_native_unit_of_measurement = "kWh"
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
    def available(self) -> bool:
        data: ConsumptionData = self.coordinator.data
        if not data.series:
            return False
        last_ts = data.series[-1].timestamp
        parsed = dt_util.parse_datetime(last_ts) if last_ts else None
        if not parsed:
            return False
        age = dt_util.as_local(dt_util.now()) - dt_util.as_local(parsed)
        return age <= timedelta(hours=self.coordinator.stale_hours)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data: ConsumptionData = self.coordinator.data
        last_ts = data.series[-1].timestamp if data.series else None
        last_dt = dt_util.parse_datetime(last_ts) if last_ts else None
        stale_minutes = None
        if last_dt:
            age = dt_util.as_local(dt_util.now()) - dt_util.as_local(last_dt)
            stale_minutes = int(age.total_seconds() // 60)
        return {
            "customer_id": data.customer_id,
            "metering_point_id": data.metering_point_id,
            "unit": data.unit,
            "last_timestamp": last_ts,
            "stale_minutes": stale_minutes,
            "series": [
                {
                    "ts": point.timestamp,
                    "value": point.value,
                    "status": getattr(point, "status", None),
                }
                for point in data.series
            ],
        }


class JSEDailyTotalSensor(CoordinatorEntity[JSECoordinator], RestoreEntity, SensorEntity):
    _attr_name = "JSE Helmi Consumption (Daily Total)"
    _attr_native_unit_of_measurement = "kWh"
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

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if not last_state or last_state.state in (None, "unknown", "unavailable"):
            return
        try:
            self._total = float(last_state.state)
        except (TypeError, ValueError):
            return
        last_day = last_state.attributes.get("last_day")
        if last_day:
            try:
                self._last_day = date.fromisoformat(last_day)
            except ValueError:
                self._last_day = None

    def _handle_coordinator_update(self) -> None:
        data: ConsumptionData = self.coordinator.data
        now_local = dt_util.as_local(dt_util.now())
        cutoff = datetime.combine(
            now_local.date(),
            time(self.coordinator.cutoff_hour, 0, 0, tzinfo=now_local.tzinfo),
        )
        if now_local < cutoff:
            # Before cutoff, keep the previous total.
            self.async_write_ha_state()
            return

        target_day = (now_local - timedelta(days=1)).date()
        total = None
        for point in data.daily_series:
            parsed = dt_util.parse_datetime(point.timestamp) if point.timestamp else None
            if not parsed:
                continue
            local_dt = dt_util.as_local(parsed)
            if local_dt.date() == target_day:
                total = float(point.value)
                break

        if self._last_day != target_day and total is not None:
            # New day, increment the running total.
            self._total += total
            self._last_day = target_day

        self.async_write_ha_state()


class JSEHourlyTotalSensor(CoordinatorEntity[JSECoordinator], RestoreEntity, SensorEntity):
    _attr_name = "JSE Helmi Consumption (Hourly Total)"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = "energy"
    _attr_state_class = "total_increasing"

    def __init__(self, coordinator: JSECoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"jse_helmi_consumption_hourly_total_{coordinator.data.metering_point_id}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.data.metering_point_id)},
            name=f"JSE Helmi {coordinator.data.metering_point_id}",
            manufacturer="JSE",
        )
        self._total = 0.0
        self._last_ts: Optional[str] = None
        self._seed_ts: Optional[str] = None

    @property
    def native_value(self) -> Optional[float]:
        return self._total

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {"last_timestamp": self._last_ts, "seeded_ts": self._seed_ts}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if not last_state or last_state.state in (None, "unknown", "unavailable"):
            return
        try:
            self._total = float(last_state.state)
        except (TypeError, ValueError):
            return
        self._last_ts = last_state.attributes.get("last_timestamp")
        self._seed_ts = last_state.attributes.get("seeded_ts")

    def _handle_coordinator_update(self) -> None:
        data: ConsumptionData = self.coordinator.data
        points = []
        for point in data.series:
            parsed = dt_util.parse_datetime(point.timestamp) if point.timestamp else None
            if parsed:
                points.append((parsed, point))

        points.sort(key=lambda item: item[0])

        last_dt = dt_util.parse_datetime(self._last_ts) if self._last_ts else None
        if points:
            latest_point = points[-1][1]
            if last_dt is None:
                # Initialize with the latest point (single hour) without backfilling history.
                if latest_point.value is not None:
                    self._total += float(latest_point.value)
                self._last_ts = latest_point.timestamp
                self._seed_ts = latest_point.timestamp
                self.async_write_ha_state()
                return
            if (
                self._total == 0.0
                and self._last_ts == latest_point.timestamp
                and self._seed_ts != latest_point.timestamp
            ):
                # Seed once if we restored a zero total with a known last timestamp.
                if latest_point.value is not None:
                    self._total += float(latest_point.value)
                self._seed_ts = latest_point.timestamp
                self.async_write_ha_state()
                return

        for parsed, point in points:
            if last_dt and parsed <= last_dt:
                continue
            if point.value is not None:
                self._total += float(point.value)
            self._last_ts = point.timestamp
            last_dt = parsed

        self.async_write_ha_state()
