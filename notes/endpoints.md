# JSE Helmi API endpoints (from HAR)

Base API: `https://api.asiakas.jes-extranet.com`

Auth is AWS Cognito (`cognito-idp.eu-west-1.amazonaws.com`); backend calls appear to require `Authorization: Bearer <AccessToken>` plus `Accept: application/json`.

## Auth (AWS Cognito)

### InitiateAuth
- `POST https://cognito-idp.eu-west-1.amazonaws.com/`
- Headers:
  - `Content-Type: application/x-amz-json-1.1`
  - `X-Amz-Target: AWSCognitoIdentityProviderService.InitiateAuth`
- Body:
  - `{"AuthFlow":"USER_PASSWORD_AUTH","ClientId":"eem5mn6iqfgf225ebg82v1k8l","AuthParameters":{"USERNAME":"<email>","PASSWORD":"<password>"}}`
- Response (shape):
  ```json
  {
    "AuthenticationResult": {
      "AccessToken": "...",
      "IdToken": "...",
      "RefreshToken": "...",
      "ExpiresIn": 3600,
      "TokenType": "Bearer"
    }
  }
  ```

### GetUser
- `POST https://cognito-idp.eu-west-1.amazonaws.com/`
- Headers:
  - `Content-Type: application/x-amz-json-1.1`
  - `X-Amz-Target: AWSCognitoIdentityProviderService.GetUser`
- Body:
  - `{"AccessToken":"<access_token>"}`
- Response includes `Username` and `UserAttributes` (use `sub` attribute).

## Backend

### Customer metadata (maps Cognito `sub` -> customer ids)
- `GET /idm/customerMetadata?sub=<sub>`
- Headers:
  - `Authorization: Bearer <AccessToken>`
  - `Accept: application/json`
- Response (redacted):
  ```json
  {
    "data": {
      "sub": "<uuid>",
      "customer_ids": ["jes_1234567"],
      "business_ids": [],
      "ignored_customer_ids": [],
      "account_setup_completed": true
    }
  }
  ```

### Customer profile (optional; includes contact data)
- `GET /customer/customers?customerId[]=<customer_id>`
- Headers:
  - `Authorization: Bearer <AccessToken>`
  - `Accept: application/json`
- Response (redacted):
  ```json
  {
    "data": [
      {
        "id": "jes_1234567",
        "customerId": "1234567",
        "customerType": "<code>",
        "currentContacts": [],
        "currentAddresses": [],
        "contracts": [
          {
            "meteringPoint": {
              "id": "jes_FI_JSE000_XXXXXX",
              "meteringPointId": "FI_JSE000_XXXXXX"
            }
          }
        ]
      }
    ]
  }
  ```

### Account info (optional)
- `GET /customer/account/<email>`
- Headers:
  - `Authorization: Bearer <AccessToken>`
  - `Accept: application/json`
- Response (redacted):
  ```json
  {
    "data": {
      "uid": "<email>",
      "preferences": {},
      "dashboardConfig": []
    }
  }
  ```

### Metering point config (requires meteringPointId)
- `GET /customer/meteringPoints/<metering_point_id>/config?customerId=<customer_id>`
- Headers:
  - `Authorization: Bearer <AccessToken>`
  - `Accept: application/json`
- Response (redacted):
  ```json
  {
    "data": {
      "fuseType": "Under63A",
      "productProfile": {"usage": "Energia"}
    }
  }
  ```

### Consumption (energy)
- `GET /consumption/consumption/energy/<metering_point_id>`
- Query params:
  - `customerId=<customer_id>`
  - `start=<ISO8601 datetime>`
  - `end=<ISO8601 datetime>`
  - `resolution=hour|day|month`
- Headers:
  - `Authorization: Bearer <AccessToken>`
  - `Accept: application/json`
- Response (redacted):
  ```json
  {
    "data": {
      "customerId": "jes_1234567",
      "meteringPointId": "FI_JSE000_XXXXXX",
      "productSeries": [
        {
          "typeId": "KWH Usage",
          "data": [
            {
              "startTime": "2025-06-30T21:00:00.000Z",
              "endTime": "2025-07-31T21:00:00.000Z",
              "value": 603.261,
              "type": "kWh",
              "status": 150
            }
          ]
        }
      ],
      "sumSeries": []
    }
  }
  ```

### Consumption pricing (energy)
- `GET /consumption/pricing/energy/<metering_point_id>`
- Query params:
  - `customerId=<customer_id>`
  - `start=<ISO8601 datetime>`
  - `end=<ISO8601 datetime>`
  - `resolution=hour|day|month`
- Headers:
  - `Authorization: Bearer <AccessToken>`
  - `Accept: application/json`
- Response (redacted):
  ```json
  {
    "data": {
      "productSeries": [
        {
          "typeId": "KWH Price",
          "data": [
            {
              "startTime": "...",
              "endTime": "...",
              "value": 0.1234,
              "type": "EUR"
            }
          ]
        }
      ]
    }
  }
  ```

### Temperature (not required for current scope)
- `GET /temperature/temperature/<postal_code>`
- Query params: `start`, `end`, `resolution`
- Headers:
  - `Authorization: Bearer <AccessToken>`
  - `Accept: application/json`

## Notes
- The HAR responses use 304 with content populated; treat as normal JSON responses.
- Metering point id (`FI_JSE000_...`) is available via `GET /customer/customers` at `data[0].contracts[*].meteringPoint.meteringPointId`.
- Once the consumption HAR is fully captured, verify where the metering point id is sourced.
