# Repository Guidelines

## Overview
This repository is currently empty (no tracked source files or configuration). The guidance below describes the expected structure and practices to follow as the project is initialized. Update this document as soon as concrete tooling and directories are introduced.

## Project Structure & Module Organization
- `src/`: main application or library code (create when starting implementation).
- `tests/`: unit/integration tests (mirror `src/` layout).
- `assets/` or `public/`: static files such as images or fonts.
- `scripts/`: automation helpers (build, lint, release).

Example structure:
```
.
├── src/
├── tests/
├── assets/
└── scripts/
```

## Build, Test, and Development Commands
No build system is configured yet. Once chosen, add scripts at the project root (for example, `package.json`, `Makefile`, or `pyproject.toml`) and document commands here, such as:
- `npm run dev`: start local development server.
- `npm test`: run test suite.
- `npm run build`: generate production build.

## Coding Style & Naming Conventions
- Indentation: 2 or 4 spaces depending on the chosen language/tooling; keep it consistent.
- Names: use `kebab-case` for filenames, `camelCase` for variables/functions, and `PascalCase` for types/classes unless the language community strongly prefers otherwise.
- Add a formatter or linter (for example, `prettier`, `eslint`, `black`, or `ruff`) and document the command (e.g., `npm run lint`).

## Testing Guidelines
- Place tests in `tests/` and mirror source module names (e.g., `user-service.test.js` for `user-service.js`).
- Use a single test runner and document it once selected (for example, `jest`, `vitest`, or `pytest`).
- Prefer fast unit tests; add integration tests under `tests/integration/` if needed.

## Commit & Pull Request Guidelines
No Git history is available yet. When initializing VCS:
- Use clear, imperative commit messages (e.g., `Add user authentication flow`).
- Keep commits focused; avoid bundling unrelated changes.
- For PRs, include a short summary, testing notes, and screenshots for UI changes.

## Configuration & Secrets
- Store secrets in environment variables or a local `.env` file.
- Never commit credentials; add `.env` and similar files to `.gitignore` once Git is initialized.

## agents.md — JSE Helmi reverse-engineering (endpoints + auth) + Python client

### Goal
Reverse-engineer the Helmi/Jarvi-Suomen Energia portal API enough to:
1) authenticate with email+password (AWS Cognito),
2) discover the customer id(s),
3) fetch consumption data (hourly/daily/monthly),
4) provide a standalone Python CLI that prints structured JSON.

Home Assistant integration is explicitly out-of-scope for now.

### Known facts (from current HAR)
- Auth uses AWS Cognito (cognito-idp.eu-west-1.amazonaws.com)
- `InitiateAuth` with `USER_PASSWORD_AUTH`
- Cognito region: `eu-west-1`
- Cognito app client id: `eem5mn6iqfgf225ebg82v1k8l`
- Backend base: `https://api.asiakas.jes-extranet.com`
- Known endpoint:
  - `GET /idm/customerMetadata?sub=<uuid>`
  - returns `customer_ids` like `jes_1227886`

Assume most backend calls require `Authorization: Bearer <AccessToken>` even if the HAR export hid/redacted it.

### Deliverables
- `notes/endpoints.md`
  - list of endpoints (method, path, params/body, required headers)
  - example response schemas (redact personal data)
- `client/jse_client.py`
  - a minimal Python client that:
    - logs in (Cognito)
    - gets `sub`
    - gets `customer_id`
    - fetches consumption for a date range
- `client/cli.py`
  - CLI wrapper:
    - `python -m client.cli login-test`
    - `python -m client.cli customers`
    - `python -m client.cli consumption --start YYYY-MM-DD --end YYYY-MM-DD --granularity hour|day|month`
  - outputs JSON to stdout

### TODO (blocking): capture HAR that includes consumption endpoints
The existing HAR covers login + customerMetadata only. We need the API calls that return consumption.

#### How to capture the HAR (Chrome)
1. Open DevTools -> Network.
2. Enable:
   - Preserve log
   - Disable cache
3. Clear requests.
4. Log in.
5. Navigate to the consumption/usage graph view.
6. Change date range (7d -> 30d), switch hour/day if possible.
7. Filter to Fetch/XHR.
8. Export: "Save all as HAR with content".
9. Do NOT sanitize if possible. If you must sanitize, keep response bodies for JSON calls.

### Tasks for the agent (in order)

#### 1) Parse HARs and map the API
Input:
- the existing HAR file already provided
- the new HAR with consumption calls (TODO above)

Output:
- Identify all requests to:
  - `cognito-idp.eu-west-1.amazonaws.com`
  - `api.asiakas.jes-extranet.com`
- Group by endpoint and infer:
  - auth type (bearer/cookie)
  - required headers
  - required query params/body keys
- For each candidate consumption endpoint:
  - record URL path, method
  - find which parameters control date range/granularity
  - capture a small redacted example response schema
- Write results to `notes/endpoints.md`

#### 2) Implement Cognito auth (prove it works)
Implement auth without a browser.
Preferred approach: raw HTTPS to Cognito (no boto3 dependency).

Cognito request shape:
- POST `https://cognito-idp.eu-west-1.amazonaws.com/`
- headers:
  - `Content-Type: application/x-amz-json-1.1`
  - `X-Amz-Target: AWSCognitoIdentityProviderService.InitiateAuth`
- body:
  - `{"AuthFlow":"USER_PASSWORD_AUTH","ClientId":"...","AuthParameters":{"USERNAME":"...","PASSWORD":"..."}}`

Expected response includes `AuthenticationResult`:
- `AccessToken`, `IdToken`, `RefreshToken`, `ExpiresIn`

Also implement `GetUser`:
- headers:
  - `X-Amz-Target: AWSCognitoIdentityProviderService.GetUser`
- body:
  - `{"AccessToken":"..."}`

From `GetUser` or decoded `IdToken`, obtain `sub`.

#### 3) Implement backend calls (customer metadata)
Call:
- `GET https://api.asiakas.jes-extranet.com/idm/customerMetadata?sub=<sub>`
Send:
- `Authorization: Bearer <AccessToken>`
- `Accept: application/json`

Parse:
- first `customer_id` from `customer_ids[]`

#### 4) Implement consumption calls (after endpoint discovery)
Once the consumption endpoint(s) are identified:
- implement `get_consumption(customer_id, start, end, granularity)`
- normalize output into a stable schema:
  - `{"granularity":"hour","unit":"kWh","series":[{"ts":"...","value":...}, ...]}`
- the CLI should print this JSON.

#### 5) Resilience + hygiene
- If any backend request returns 401:
  - re-login (simple) OR implement refresh token flow if discoverable.
- Add basic retries for 429/5xx with short exponential backoff.
- Never print tokens/passwords in logs.
- Use env vars for secrets:
  - `JSE_EMAIL`, `JSE_PASSWORD`

### Coding conventions
- Keep it simple and readable (no premature abstractions).
- Use `requests` initially (sync) to move fast.
- Add type hints, but don't over-engineer.
- Minimal dependencies.

### CLI examples
- `JSE_EMAIL=... JSE_PASSWORD=... python -m client.cli login-test`
- `JSE_EMAIL=... JSE_PASSWORD=... python -m client.cli customers`
- `JSE_EMAIL=... JSE_PASSWORD=... python -m client.cli consumption --start 2026-01-01 --end 2026-01-17 --granularity day`

### Completion definition
Done when:
- endpoints.md lists all required endpoints and their parameters
- CLI can fetch consumption for a date range using only email+password
- output is stable JSON suitable for later HA integration
