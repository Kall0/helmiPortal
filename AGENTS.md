# Repository Guidelines

## Project Structure
- `client/`: standalone Python client + CLI.
- `custom_components/jse_helmi/`: Home Assistant (HACS) integration.
- `notes/`: endpoint map and reverse-engineering notes.
- `tests/`: unit + live integration tests.

## Commands
- Unit tests: `python3 -m unittest discover -s tests`
- Live integration: `JSE_EMAIL=... JSE_PASSWORD=... python3 -m unittest tests.test_integration_live`
- CLI smoke test: `JSE_EMAIL=... JSE_PASSWORD=... python3 -m client.cli login-test`
 - CLI full-hour filter: `python3 -m client.cli consumption --granularity hour --last-hours 1 --full-only`

## Secrets
- Use env vars only: `JSE_EMAIL`, `JSE_PASSWORD`.
- Never commit HAR files or credentials. HARs stay local; endpoints go in `notes/endpoints.md`.

## JSE Helmi API Facts
- Cognito region: `eu-west-1`
- App client id: `eem5mn6iqfgf225ebg82v1k8l`
- Cognito endpoint: `https://cognito-idp.eu-west-1.amazonaws.com/`
- Backend base: `https://api.asiakas.jes-extranet.com`
- Customer IDs from: `GET /idm/customerMetadata?sub=<uuid>`
- Metering point IDs from: `GET /customer/customers?customerId[]=...` -> `contracts[*].meteringPoint.meteringPointId`
- Consumption endpoint: `GET /consumption/consumption/energy/<metering_point_id>`
  - params: `customerId`, `start`, `end`, `resolution=hour|day|month`
  - requires `Authorization: Bearer <AccessToken>`

## Deliverables
- `notes/endpoints.md` kept current (method, path, params, headers, redacted schemas).
- `client/jse_client.py` + `client/cli.py` for auth, customer lookup, consumption.
- HA integration in `custom_components/jse_helmi` exposing:
  - Hourly sensor (`measurement`, no device_class)
  - Hourly total sensor (`total_increasing` for Energy)
  - Daily total sensor (`total_increasing`, uses `resolution=day`)

## Change Handling (when API changes)
1. Capture a new HAR (auth + consumption view).
2. Update `notes/endpoints.md` first.
3. Adjust `client/jse_client.py` and `custom_components/jse_helmi/api.py`.
4. Run unit + live tests.
5. Bump version in `custom_components/jse_helmi/manifest.json` and push.

## HA Integration Notes
- Options: cutoff hour, update minute, stale hours (set in integration options UI).
- Filters: only accept points with `status == 150` (full hours/days).
- Device is keyed to config entry id; all sensors attach to one device.
- Integration uses sync `requests` (non-official style); async refactor was rolled back.
- Do not change entity `unique_id` or device identifiers; doing so will reset HA history.
