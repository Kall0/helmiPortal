# Helmi Portal Client (JSE)

Reverse-engineered JSE Helmi portal API with a minimal Python client and a Home Assistant (HACS) integration. The HA integration exposes hourly kWh consumption and is designed to feed the Energy dashboard via a utility meter.

## Python CLI

Install dependencies:
```bash
python3 -m pip install requests
```

Login test:
```bash
JSE_EMAIL="you@example.com" JSE_PASSWORD="your-password" python3 -m client.cli login-test
```

List customers and metering points:
```bash
JSE_EMAIL="you@example.com" JSE_PASSWORD="your-password" python3 -m client.cli customers
```

Fetch consumption (daily):
```bash
JSE_EMAIL="you@example.com" JSE_PASSWORD="your-password" python3 -m client.cli consumption --start 2026-01-01 --end 2026-01-17 --granularity day
```

For hourly data, use `--granularity hour` and a shorter range if needed.

## Home Assistant (HACS)

This repo includes a custom integration under `custom_components/jse_helmi`.

Install via HACS:
1. HACS -> Integrations -> Custom repositories -> add this repo URL (Integration).
2. Install `JSE Helmi`.
3. Restart Home Assistant.
4. Settings -> Devices & Services -> Add Integration -> `JSE Helmi`.
5. Enter email/password and select customer + metering point.

Energy dashboard setup:
- Create a utility meter that rolls up the hourly sensor into a total.
- Example:
  ```yaml
  utility_meter:
    jse_energy_daily:
      source: sensor.jse_helmi_consumption_hourly
      cycle: daily
  ```
- Use `sensor.jse_energy_daily` in the Energy dashboard.

## Notes
- Times are reported in local timezone (Home Assistant locale).
- Pricing endpoints are discovered but not exposed yet.
