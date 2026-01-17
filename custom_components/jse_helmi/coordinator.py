from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import JSEApi
from .const import CONF_CUSTOMER_ID, CONF_EMAIL, CONF_METERING_POINT_ID, CONF_PASSWORD, DOMAIN


@dataclass
class ConsumptionPoint:
    timestamp: str
    value: float


@dataclass
class ConsumptionData:
    customer_id: str
    metering_point_id: str
    unit: str
    series: List[ConsumptionPoint]


class JSECoordinator(DataUpdateCoordinator[ConsumptionData]):
    def __init__(
        self,
        hass: HomeAssistant,
        config: Dict[str, Any],
        update_interval: timedelta,
    ) -> None:
        self.hass = hass
        self._email = config[CONF_EMAIL]
        self._password = config[CONF_PASSWORD]
        self._customer_id = config[CONF_CUSTOMER_ID]
        self._metering_point_id = config[CONF_METERING_POINT_ID]
        self._client = JSEApi(email=self._email, password=self._password)
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=f"{DOMAIN}_{self._metering_point_id}",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> ConsumptionData:
        try:
            return await self.hass.async_add_executor_job(self._fetch_consumption)
        except Exception as exc:  # noqa: BLE001 - coordinator wraps errors
            raise UpdateFailed(str(exc)) from exc

    def _fetch_consumption(self) -> ConsumptionData:
        end = dt_util.as_local(dt_util.now()).replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(days=2)
        raw = self._client.get_consumption(
            customer_id=self._customer_id,
            metering_point_id=self._metering_point_id,
            start=start.isoformat(),
            end=end.isoformat(),
            resolution="hour",
        )
        data = raw.get("data", {})
        series_list = data.get("productSeries") or []
        points: List[ConsumptionPoint] = []
        unit = ""
        if series_list:
            for point in series_list[0].get("data") or []:
                ts = point.get("startTime")
                parsed = dt_util.parse_datetime(ts) if ts else None
                local_dt = dt_util.as_local(parsed) if parsed else None
                if local_dt and local_dt >= end:
                    continue
                local_ts = local_dt.isoformat() if local_dt else ""
                if not unit:
                    unit = point.get("type", "")
                points.append(ConsumptionPoint(timestamp=local_ts, value=point.get("value")))
        return ConsumptionData(
            customer_id=self._customer_id,
            metering_point_id=self._metering_point_id,
            unit=unit or "kWh",
            series=points,
        )
