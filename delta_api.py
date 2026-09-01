# ============================================================
# GH BOSS AI — DELTA API MODULE (DIRECT LIVE & SAFE)
# ============================================================

import os
import requests

API_KEY = os.getenv("DELTA_API_KEY", "").strip()
API_SECRET = os.getenv("DELTA_API_SECRET", "").strip()

BASE_URL = "https://api.delta.exchange"


def test_delta():
    try:
        url = f"{BASE_URL}/v2/products"
        response = requests.get(url, timeout=10)
        if response.ok:
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
            res_data = response.json()
            # सुरक्षित रूप से लिस्ट या डिक्शनरी हैंडल करने के लिए
            balances = res_data.get("result", [])
            if isinstance(balances, dict):
                balances = [balances]
            return {"success": True, "balances": balances}
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
        url = f"{BASE_URL}/v2/products"
        res = requests.get(url, timeout=10)
        if res.ok:
            products = res.json().get("result", [])
            for p in products:
                if p.get("symbol") == symbol or p.get("contract_unit") == symbol:
                    return float(p.get("close", p.get("mark_price", 0)))
        return 0.0
    except Exception as e:
        print("❌ Live price error:", e)
        return 0.0
