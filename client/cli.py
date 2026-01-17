from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

from .jse_client import JSEClient, normalize_consumption_response


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _build_client() -> JSEClient:
    email = _require_env("JSE_EMAIL")
    password = _require_env("JSE_PASSWORD")
    return JSEClient(email=email, password=password)


def _cmd_login_test(client: JSEClient) -> Dict[str, Any]:
    tokens = client.login()
    sub = client.get_user_sub()
    return {"ok": True, "sub": sub, "expires_in": tokens.expires_in}


def _cmd_customers(client: JSEClient) -> Dict[str, Any]:
    sub = client.get_user_sub()
    customer_ids = client.get_customer_ids(sub)
    customers: List[Dict[str, Any]] = []
    for customer_id in customer_ids:
        metering_points = client.get_metering_point_ids(customer_id)
        customers.append(
            {"customer_id": customer_id, "metering_point_ids": metering_points}
        )
    return {"customers": customers}


def _cmd_consumption(client: JSEClient, args: argparse.Namespace) -> Dict[str, Any]:
    sub = client.get_user_sub()
    customer_ids = client.get_customer_ids(sub)
    if not customer_ids:
        raise RuntimeError("No customer ids found")
    customer_id = args.customer_id or customer_ids[0]

    if args.metering_point_id:
        metering_point_id = args.metering_point_id
    else:
        metering_points = client.get_metering_point_ids(customer_id)
        if not metering_points:
            raise RuntimeError("No metering points found for customer")
        metering_point_id = metering_points[0]

    raw = client.get_consumption(
        customer_id=customer_id,
        metering_point_id=metering_point_id,
        start=args.start,
        end=args.end,
        resolution=args.granularity,
    )
    normalized = normalize_consumption_response(raw, args.granularity)
    return {
        "customer_id": customer_id,
        "metering_point_id": metering_point_id,
        **normalized,
    }


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="JSE Helmi CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("login-test", help="Authenticate and fetch Cognito sub")
    subparsers.add_parser("customers", help="List customer and metering point ids")

    consumption = subparsers.add_parser("consumption", help="Fetch consumption data")
    consumption.add_argument("--start", required=True, help="Start date or ISO8601 datetime")
    consumption.add_argument("--end", required=True, help="End date or ISO8601 datetime")
    consumption.add_argument(
        "--granularity",
        required=True,
        choices=["hour", "day", "month"],
        help="Aggregation resolution",
    )
    consumption.add_argument("--customer-id", help="Override customer id")
    consumption.add_argument("--metering-point-id", help="Override metering point id")

    args = parser.parse_args(argv)

    try:
        client = _build_client()
        if args.command == "login-test":
            result = _cmd_login_test(client)
        elif args.command == "customers":
            result = _cmd_customers(client)
        elif args.command == "consumption":
            result = _cmd_consumption(client, args)
        else:
            raise RuntimeError(f"Unknown command: {args.command}")
    except Exception as exc:  # noqa: BLE001 - simple CLI error handling
        print(f"error: {exc}", file=sys.stderr)
        return 1

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
