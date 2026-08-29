import os
import time
import hmac
import hashlib
import requests

BASE_URL = "https://api.india.delta.exchange"


def test_delta():

    api_key = os.getenv("DELTA_API_KEY")
    api_secret = os.getenv("DELTA_API_SECRET")

    if not api_key:
        return {
            "success": False,
            "stage": "credentials",
            "error": "DELTA_API_KEY missing"
        }

    if not api_secret:
        return {
            "success": False,
            "stage": "credentials",
            "error": "DELTA_API_SECRET missing"
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
            timeout=20
        )

        try:
            data = response.json()
        except Exception:
            data = {
                "raw_response": response.text
            }

        if response.status_code == 200:

            return {
                "success": True,
                "stage": "authentication",
                "http_status": 200,
                "message": "Delta authentication OK"
            }

        return {
            "success": False,
            "stage": "delta_api",
            "http_status": response.status_code,
            "error": data
        }

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "stage": "network",
            "error": "Delta request timeout"
        }

    except requests.exceptions.RequestException as e:

        return {
            "success": False,
            "stage": "network",
            "error": str(e)
        }

    except Exception as e:

        return {
            "success": False,
            "stage": "unknown",
            "error": str(e)
        }
