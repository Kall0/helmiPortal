from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional

import requests
from zoneinfo import ZoneInfo


COGNITO_ENDPOINT = "https://cognito-idp.eu-west-1.amazonaws.com/"
COGNITO_CLIENT_ID = "eem5mn6iqfgf225ebg82v1k8l"
API_BASE = "https://api.asiakas.jes-extranet.com"


@dataclass
class AuthTokens:
    access_token: str
    id_token: str
    refresh_token: Optional[str]
    expires_in: int


class JSEClient:
    def __init__(
        self,
        email: str,
        password: str,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.email = email
        self.password = password
        self.session = session or requests.Session()
        self.tokens: Optional[AuthTokens] = None

    def login(self) -> AuthTokens:
        payload = {
            "AuthFlow": "USER_PASSWORD_AUTH",
            "ClientId": COGNITO_CLIENT_ID,
            "AuthParameters": {"USERNAME": self.email, "PASSWORD": self.password},
        }
        data = self._cognito_request("InitiateAuth", payload)
        result = data.get("AuthenticationResult") or {}
        tokens = AuthTokens(
            access_token=result.get("AccessToken", ""),
            id_token=result.get("IdToken", ""),
            refresh_token=result.get("RefreshToken"),
            expires_in=int(result.get("ExpiresIn", 0)),
        )
        if not tokens.access_token:
            raise RuntimeError("Cognito auth did not return AccessToken")
        self.tokens = tokens
        return tokens

    def get_user_sub(self) -> str:
        data = self._cognito_request(
            "GetUser", {"AccessToken": self._access_token()}
        )
        for attr in data.get("UserAttributes", []):
            if attr.get("Name") == "sub":
                return attr.get("Value", "")
        raise RuntimeError("Cognito GetUser response missing sub")

    def get_customer_ids(self, sub: str) -> List[str]:
        data = self._api_get("/idm/customerMetadata", params={"sub": sub})
        customer_ids = data.get("data", {}).get("customer_ids") or []
        return list(customer_ids)

    def get_customer_profile(self, customer_id: str) -> Dict[str, Any]:
        data = self._api_get(
            "/customer/customers", params={"customerId[]": customer_id}
        )
        items = data.get("data") or []
        if not items:
            raise RuntimeError("No customer profile returned")
        return items[0]

    def get_metering_point_ids(self, customer_id: str) -> List[str]:
        profile = self.get_customer_profile(customer_id)
        metering_points: List[str] = []
        for contract in profile.get("contracts", []) or []:
            mp = contract.get("meteringPoint") or {}
            mp_id = mp.get("meteringPointId")
            if mp_id:
                metering_points.append(mp_id)
        return metering_points

    def get_consumption(
        self,
        customer_id: str,
        metering_point_id: str,
        start: str,
        end: str,
        resolution: str,
    ) -> Dict[str, Any]:
        params = {
            "customerId": customer_id,
            "start": _normalize_datetime(start),
            "end": _normalize_datetime(end),
            "resolution": resolution,
        }
        path = f"/consumption/consumption/energy/{metering_point_id}"
        return self._api_get(path, params=params)

    def _access_token(self) -> str:
        if not self.tokens:
            self.login()
        assert self.tokens
        return self.tokens.access_token

    def _cognito_request(self, target: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": f"AWSCognitoIdentityProviderService.{target}",
        }
        response = self.session.post(
            COGNITO_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=30
        )
        response.raise_for_status()
        return response.json()

    def _api_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{API_BASE}{path}"
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self._access_token()}"}
        try:
            return _request_with_retry(self.session, "GET", url, headers=headers, params=params)
        except PermissionError:
            # Re-login once and retry with a fresh access token.
            self.login()
            headers["Authorization"] = f"Bearer {self._access_token()}"
            return _request_with_retry(self.session, "GET", url, headers=headers, params=params)


def _normalize_datetime(value: str) -> str:
    dt = _parse_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("Europe/Helsinki"))
    return dt.isoformat()


def _parse_datetime(value: str) -> datetime:
    text = value.strip()
    if "T" not in text:
        return datetime.combine(date.fromisoformat(text), time.min).replace(
            tzinfo=ZoneInfo("Europe/Helsinki")
        )
    if text[-5:-4] in {"+", "-"} and text[-2:].isdigit() and text[-5:-2].isdigit():
        # Convert +HHMM to +HH:MM for Python's fromisoformat.
        text = f"{text[:-2]}:{text[-2:]}"
    if text.endswith("Z"):
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    return datetime.fromisoformat(text)


def _request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    headers: Dict[str, str],
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            response = session.request(
                method, url, headers=headers, params=params, timeout=30
            )
            if response.status_code == 401 and attempt == 0:
                # The caller will re-login by re-invoking the request after login.
                raise PermissionError("Unauthorized (401)")
            if response.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"Retryable status {response.status_code}")
            response.raise_for_status()
            return response.json()
        except PermissionError:
            raise
        except Exception as exc:  # noqa: BLE001 - keep simple retry loop
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(0.5 * (2**attempt))
                continue
            raise RuntimeError(f"Request failed after {max_retries} attempts") from last_exc
    raise RuntimeError("Unreachable retry loop")


def normalize_consumption_response(
    response: Dict[str, Any],
    granularity: str,
) -> Dict[str, Any]:
    data = response.get("data", {})
    series_list = data.get("productSeries") or []
    series = []
    unit = ""
    if series_list:
        data_points = series_list[0].get("data") or []
        for point in data_points:
            if not unit:
                unit = point.get("type", "")
            series.append(
                {
                    "ts": _to_helsinki_iso(point.get("startTime")),
                    "value": point.get("value"),
                    "status": point.get("status"),
                }
            )
    return {"granularity": granularity, "unit": unit, "series": series}


def _to_helsinki_iso(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    dt = _parse_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo("Europe/Helsinki")).isoformat()
