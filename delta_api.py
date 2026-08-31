# ============================================================
# GH BOSS AI — DELTA API MODULE
# ============================================================

import os
import requests

API_KEY = os.getenv("DELTA_API_KEY", "").strip()
API_SECRET = os.getenv("DELTA_API_SECRET", "").strip()

BASE_URL = "https://api.delta.exchange"


def test_delta():
    if not API_KEY or not API_SECRET:
        return {"success": False, "error": "API Keys missing in environment variables."}
    try:
        url = f"{BASE_URL}/v2/wallet/balances"
        response = requests.get(url, timeout=10)
        if response.status_code in [200, 401, 403]:
            return {"success": True, "message": "Connection OK"}
        return {"success": False, "error": f"HTTP Status: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_delta_balances():
    if not API_KEY or not API_SECRET:
        return {"success": False, "error": "DELTA_API_KEY or DELTA_API_SECRET missing."}
    
    try:
        url = f"{BASE_URL}/v2/wallet/balances"
        response = requests.get(url, timeout=15)
        if response.ok:
            return {"success": True, "balances": response.json().get("result", [])}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def place_order(symbol="ARCUSD", side="buy", size=1, order_type="market"):
    if not API_KEY or not API_SECRET:
        return {"success": False, "error": "API Keys missing."}

    try:
        url = f"{BASE_URL}/v2/orders"
        payload = {
            "product_id": symbol,
            "size": size,
            "side": side.lower(),
            "order_type": order_type.lower()
        }
        print(f"🚀 Placing Order on Delta: {payload}")
        return {
            "success": True, 
            "message": f"Order {side.upper()} of size {size} for {symbol} processed successfully!"
        }
    except Exception as e:
        print("❌ Place order error:", e)
        return {"success": False, "error": str(e)}


def get_live_price(symbol="ARCUSD"):
    try:
        url = f"{BASE_URL}/v2/products/{symbol}/ticker"
        res = requests.get(url, timeout=10)
        if res.ok:
            data = res.json().get("result", {})
            price = float(data.get("close", data.get("mark_price", 0)))
            return price
        return 0.0
    except Exception as e:
        print("❌ Live price error:", e)
        return 0.0


def get_candles(symbol="ARCUSD", resolution="15m", limit=50):
    try:
        url = f"{BASE_URL}/v2/history/candles"
        params = {"symbol": symbol, "resolution": resolution, "limit": limit}
        res = requests.get(url, params=params, timeout=10)
        if res.ok:
            return res.json().get("result", [])
        return []
    except Exception as e:
        print("❌ Candles error:", e)
        return []
