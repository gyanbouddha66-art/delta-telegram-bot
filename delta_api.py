import os
import time
import hmac
import hashlib
import requests

BASE_URL = "https://api.india.delta.exchange"


def get_delta_balances():

    api_key = os.getenv("DELTA_API_KEY")
    api_secret = os.getenv("DELTA_API_SECRET")

    if not api_key or not api_secret:
        return {
            "success": False,
            "error": "Delta credentials missing"
        }

    method = "GET"
    path = "/v2/wallet/balances"
    query_string = ""
    payload = ""

    timestamp = str(int(time.time()))

    signature_data = (
        method
        + timestamp
        + path
        + query_string
        + payload
    )

    signature = hmac.new(
        api_secret.encode("utf-8"),
        signature_data.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "api-key": api_key,
        "timestamp": timestamp,
        "signature": signature,
        "User-Agent": "GH-Delta-Trading-Bot",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:

        response = requests.get(
            BASE_URL + path,
            headers=headers,
            timeout=30
        )

        data = response.json()

        if response.status_code != 200:

            return {
                "success": False,
                "http_status": response.status_code,
                "error": data
            }

        balances = data.get("result", [])

        usd = None
        inr = None
        eth = None
        btc = None

        for item in balances:

            symbol = item.get("asset_symbol")

            if symbol == "USD":
                usd = item

            elif symbol == "INR":
                inr = item

            elif symbol == "ETH":
                eth = item

            elif symbol == "BTC":
                btc = item

        return {
            "success": True,
            "http_status": 200,

            "usd": usd,
            "inr": inr,
            "eth": eth,
            "btc": btc
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


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
