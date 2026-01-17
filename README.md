# Helmi Portal Client (JSE)

## Quickstart

```bash
python3 -m pip install requests
```

```bash
JSE_EMAIL="you@example.com" JSE_PASSWORD="your-password" python3 -m client.cli login-test
```

```bash
JSE_EMAIL="you@example.com" JSE_PASSWORD="your-password" python3 -m client.cli customers
```

```bash
JSE_EMAIL="you@example.com" JSE_PASSWORD="your-password" python3 -m client.cli consumption --start 2026-01-01 --end 2026-01-17 --granularity day
```

For hourly data, use `--granularity hour` (and a narrower date range if needed).

## Home Assistant (HACS)

This repo includes a custom integration under `custom_components/jse_helmi`.

Install via HACS (Custom repositories) and add the integration in HA UI:
1. HACS -> Integrations -> Custom repositories -> add this repo URL.
2. Install `JSE Helmi`.
3. Restart Home Assistant.
4. Settings -> Devices & Services -> Add Integration -> `JSE Helmi`.
5. Enter email/password, then select customer and metering point if prompted.

The integration provides a single hourly kWh sensor. For the Energy dashboard:
- Create a `utility_meter` that uses the hourly sensor to produce a `total_increasing` sensor.
- Use that utility meter sensor in the Energy dashboard configuration.
