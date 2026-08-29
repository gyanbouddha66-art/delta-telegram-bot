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
            "error": "Delta credentials missing"
        }

    # --------------------------------------------------------
    # PUBLIC CONNECTION TEST
    # --------------------------------------------------------

    try:

        response = requests.get(
            BASE_URL + "/v2/products",
            timeout=30
        )

        return {
            "success": response.status_code == 200,
            "stage": "public_connection",
            "http_status": response.status_code
        }

    except Exception as e:

        return {
            "success": False,
            "stage": "network",
            "error": str(e)
        }
