import os
import time
import hmac
import hashlib
import requests


BASE_URL = "https://api.india.delta.exchange"


def test_delta():

    api_key = os.getenv("DELTA_API_KEY")
    api_secret = os.getenv("DELTA_API_SECRET")

    if not api_key or not api_secret:
        return {
            "success": False,
            "message": "Delta credentials missing"
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
        "User-Agent": "python-rest-client",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:

        response = requests.get(
            BASE_URL + path,
            headers=headers,
            timeout=20
        )

        data = response.json()

        if response.status_code == 200:

            return {
                "success": True,
                "message": "Delta authentication OK"
            }

        return {
            "success": False,
            "http_status": response.status_code,
            "message": data
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }
