# ============================================================
# GH BOSS AI — DELTA API MODULE (`delta_api.py`)
# ============================================================

import os
import requests
import time
import hmac
import hashlib
import json

API_KEY = os.getenv("DELTA_API_KEY", "").strip()
API_SECRET = os.getenv("DELTA_API_SECRET", "").strip()
BASE_URL = "https://api.delta.exchange"


def generate_signature(method, endpoint, payload_str=""):
    if not API_SECRET:
        return "", ""
    timestamp = str(int(time.time()))
    signature_data = method + timestamp + endpoint + payload_str
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        signature_data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return timestamp, signature


def get_live_price(symbol="BTCUSD"):
    try:
        url = f"{BASE_URL}/v2/products"
        res = requests.get(url, timeout=10)
        if res.ok:
            products = res.json().get("result", [])
            for p in products:
                if p.get("symbol") == symbol or p.get("contract_unit") == symbol:
                    return float(p.get("close", p.get("mark_price", 0)))
        return 0.0
    except Exception as e:
        print("Live price error:", e)
        return 0.0


def get_candles(symbol="BTCUSD", resolution="15m", limit=50):
    try:
        url = f"{BASE_URL}/v2/history/candles"
        params = {"symbol": symbol, "resolution": resolution, "limit": limit}
        res = requests.get(url, params=params, timeout=10)
        if res.ok:
            return res.json().get("result", [])
        return []
    except Exception as e:
        print("Candles error:", e)
        return []


def place_order(product_id=27, side="buy", size=1, order_type="market"):
    if not API_KEY or not API_SECRET:
        return {"success": False, "error": "API Keys missing."}
    try:
        endpoint = "/v2/orders"
        url = f"{BASE_URL}{endpoint}"
        payload = {
            "product_id": int(product_id),
            "size": int(size),
            "side": side.lower(),
            "order_type": order_type.lower()
        }
        payload_str = json.dumps(payload)
        timestamp, signature = generate_signature("POST", endpoint, payload_str)
        headers = {
            "api-key": API_KEY,
            "timestamp": timestamp,
            "signature": signature,
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, data=payload_str, timeout=15)
        if response.ok:
            res_data = response.json()
            return {"success": True, "result": res_data.get("result", res_data)}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}
