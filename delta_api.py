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
            "stage": "credentials",
            "error": "credentials_missing"
        }

    method = "GET"
    path = "/v2/wallet/balances"
    query_string = ""
    payload = ""

    timestamp = str(int(time.time()))

    signature_payload = (
        method
        + timestamp
        + path
        + query_string
        + payload
    )

    signature = hmac.new(
        api_secret.encode("utf-8"),
        signature_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "api-key": api_key,
        "timestamp": timestamp,
        "signature": signature,
        "User-Agent": "GH-Delta-Bot",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:

        response = requests.get(
            BASE_URL + path,
            headers=headers,
            timeout=30
        )

        try:
            data = response.json()
        except Exception:
            data = {
                "raw_response": response.text[:500]
            }

        return {
            "success": response.status_code == 200,
            "stage": "authenticated_request",
            "http_status": response.status_code,
            "delta_response": data
        }

    except Exception as e:

        return {
            "success": False,
            "stage": "network",
            "error": str(e)
        }
