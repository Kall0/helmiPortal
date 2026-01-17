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
- HA integration in `custom_components/jse_helmi` exposing hourly kWh; use utility meter for Energy.

## Change Handling (when API changes)
1. Capture a new HAR (auth + consumption view).
2. Update `notes/endpoints.md` first.
3. Adjust `client/jse_client.py` and `custom_components/jse_helmi/api.py`.
4. Run unit + live tests.
5. Bump version in `custom_components/jse_helmi/manifest.json` and push.
