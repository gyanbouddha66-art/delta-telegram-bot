# ============================================================
# DELTA API MODULE (`delta_api.py`)
# ============================================================

import os
import time
import hmac
import hashlib
import requests
from config import SYMBOL, PRODUCT_ID, DEFAULT_SIZE

# Render या एनवायरनमेंट से API Keys प्राप्त करना
API_KEY = os.getenv("DELTA_API_KEY", "").strip()
API_SECRET = os.getenv("DELTA_API_SECRET", "").strip()
BASE_URL = "https://api.india.delta.exchange" # लाइव एक्सचेंज यूआरएल

def get_signature(secret, method, path, query_string="", payload=""):
    """डेल्टा एक्सचेंज के ऑथेंटिकेशन के लिए HMAC SHA256 सिग्नेचर बनाना"""
    timestamp = str(int(time.time() * 1000))
    signature_payload = timestamp + method + path + query_string + payload
    signature = hmac.new(
        secret.encode('utf-8'),
        signature_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return timestamp, signature

def test_delta():
    """डेल्टा एपीआई कनेक्शन और ऑथेंटिकेशन टेस्ट करने के लिए"""
    if not API_KEY or not API_SECRET:
        return {"status": False, "message": "API Keys missing in environment"}
    try:
        path = "/v2/wallet/balances"
        timestamp, signature = get_signature(API_SECRET, "GET", path)
        headers = {
            "api-key": API_KEY,
            "signature": signature,
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        url = f"{BASE_URL}{path}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return {"status": True, "message": "Delta API Connected Successfully"}
        else:
            return {"status": False, "message": f"Auth Failed: {response.text}"}
    except Exception as e:
        return {"status": False, "message": f"Connection Error: {str(e)}"}

def get_live_price(symbol=SYMBOL):
    """डेल्टा एक्सचेंज से किसी भी सिंबल का लाइव प्राइस प्राप्त करना"""
    try:
        url = f"{BASE_URL}/v2/products"
        res = requests.get(url, timeout=10)
        if res.ok:
            products = res.json().get("result", [])
            for p in products:
                prod_symbol = p.get("symbol", "")
                if symbol.lower() in prod_symbol.lower():
                    price = p.get("mark_price", p.get("spot_price", p.get("close", 0)))
                    if price:
                        return float(price)
        return 0.0
    except Exception as e:
        print("Live price error:", e)
        return 0.0

def get_delta_balances():
    """वॉलेट का लाइव बैलेंस देखने के लिए"""
    if not API_KEY or not API_SECRET:
        return {"success": False, "error": "API keys not configured"}
    try:
        path = "/v2/wallet/balances"
        timestamp, signature = get_signature(API_SECRET, "GET", path)
        headers = {
            "api-key": API_KEY,
            "signature": signature,
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        url = f"{BASE_URL}{path}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "balances": data.get("result", [])}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}

def place_order(product_id=PRODUCT_ID, symbol=SYMBOL, side="buy", size=DEFAULT_SIZE):
    """डेल्टा एक्सचेंज पर आर्डर (Buy/Sell) प्लेस करने के लिए"""
    if not API_KEY or not API_SECRET:
        return {"success": False, "error": "invalidapikey"}
    
    path = "/v2/orders"
    url = f"{BASE_URL}{path}"
    
    payload_dict = {
        "product_id": int(product_id),
        "size": int(size),
        "side": side.lower(),
        "order_type": "market"
    }
    
    import json
    payload_str = json.dumps(payload_dict)
    timestamp, signature = get_signature(API_SECRET, "POST", path, "", payload_str)
    
    headers = {
        "api-key": API_KEY,
        "signature": signature,
        "timestamp": timestamp,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, data=payload_str, headers=headers, timeout=10)
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get("success"):
                return {"success": True, "result": res_data.get("result")}
            else:
                return {"success": False, "error": res_data.get("error", "Unknown error")}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}
