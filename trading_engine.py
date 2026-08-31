import os
import time
import hmac
import hashlib
import json
import requests

BASE_URL = "https://api.india.delta.exchange"


def _headers(method, path, query_string="", payload=""):
    api_key = os.getenv("DELTA_API_KEY", "").strip()
    api_secret = os.getenv("DELTA_API_SECRET", "").strip()

    if not api_key or not api_secret:
        raise RuntimeError("DELTA_API_KEY / DELTA_API_SECRET missing")

    timestamp = str(int(time.time()))

    message = (
        method
        + timestamp
        + path
        + query_string
        + payload
    )

    signature = hmac.new(
        api_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return {
        "api-key": api_key,
        "timestamp": timestamp,
        "signature": signature,
        "User-Agent": "GH-Delta-Trading-Bot",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


# ============================================================
# LIVE TICKER
# ============================================================

def get_live_price(symbol="BTCUSD"):

    path = f"/v2/tickers/{symbol}"

    try:
        r = requests.get(
            BASE_URL + path,
            headers={"Accept": "application/json"},
            timeout=10
        )

        data = r.json()

        if r.status_code != 200:
            return {
                "success": False,
                "error": data
            }

        result = data.get("result", {})

        price = (
            result.get("close")
            or result.get("last_price")
            or result.get("mark_price")
        )

        return {
            "success": True,
            "symbol": symbol,
            "price": float(price) if price is not None else None,
            "raw": result
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# OHLCV
# ============================================================

def get_candles(
    symbol="BTCUSD",
    resolution="1m",
    candles=200
):

    end = int(time.time())

    seconds = {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600
    }.get(resolution, 60)

    start = end - (seconds * candles)

    path = "/v2/history/candles"

    try:

        r = requests.get(
            BASE_URL + path,
            params={
                "resolution": resolution,
                "symbol": symbol,
                "start": start,
                "end": end
            },
            headers={
                "Accept": "application/json"
            },
            timeout=15
        )

        data = r.json()

        if r.status_code != 200:

            return {
                "success": False,
                "error": data
            }

        rows = data.get("result", [])

        rows = sorted(
            rows,
            key=lambda x: x.get("time", 0)
        )

        return {
            "success": True,
            "symbol": symbol,
            "resolution": resolution,
            "candles": rows
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# BALANCE
# ============================================================

def get_delta_balances():

    method = "GET"
    path = "/v2/wallet/balances"

    try:

        headers = _headers(
            method,
            path
        )

        r = requests.get(
            BASE_URL + path,
            headers=headers,
            timeout=20
        )

        data = r.json()

        if r.status_code != 200:

            return {
                "success": False,
                "http_status": r.status_code,
                "error": data
            }

        return {
            "success": True,
            "http_status": 200,
            "balances": data.get("result", [])
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# TEST
# ============================================================

def test_delta():

    result = get_delta_balances()

    if result.get("success"):

        return {
            "success": True,
            "stage": "authenticated_request",
            "http_status": 200,
            "message": "Delta authentication OK"
        }

    return result
