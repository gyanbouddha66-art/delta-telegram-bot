import os
import time
import json
import hmac
import hashlib
import requests
import threading
from flask import Flask

# ============================================================
# 1. API & BOT CONFIGURATION (DIRECT KEYS FIXED)
# ============================================================
API_KEY = os.environ.get("DELTA_API_KEY", "nHv2Al08t6Bd8O1KSGBXCHP2ZbpmP3")
API_SECRET = os.environ.get("DELTA_API_SECRET", "tCTPHxKcZxZ2wvk9oMyFrgDRkTK37ryjRNDM6Lhkt6neE2MfIkv9lL5vW8se")

# TELEGRAM DIRECT KEYS (FOR GUARANTEED ALERTS)
TELEGRAM_BOT_TOKEN = "8919168139:AAFo7kWLd49psCb3f6H-LQaMMSDOg4T8ZvE"
TELEGRAM_CHAT_ID = "965643127"

BASE_URL = "https://api.india.delta.exchange"
SYMBOL = "ARCUSD"
TIMEFRAME = "1m"

# TRADING PARAMETERS
QTY = 1               # Contract Quantity per trade
SL_PCT = 0.008        # 0.8% Stop Loss
TP_PCT = 0.012        # 1.2% Take Profit
MIN_ER = 0.20         # Trend Efficiency Ratio Filter
MIN_MOMENTUM = 0.0004 # Fast Price Spike Trigger (0.04%)

session = requests.Session()
in_position = False

# ============================================================
# 2. RENDER HEALTH CHECK SERVER
# ============================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Fast Scalper Engine Active & Scanning!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ============================================================
# 3. TELEGRAM ALERT SYSTEM
# ============================================================
def send_telegram(msg):
    print(msg)
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=3)
    except Exception as e:
        print(f"Telegram Error: {e}")

# ============================================================
# 4. DELTA PRIVATE API & DATA HELPERS
# ============================================================
def private_request(method, endpoint, payload=None):
    try:
        method = method.upper()
        timestamp = str(int(time.time()))
        path = endpoint
        payload_str = json.dumps(payload, separators=(',', ':')) if payload else ""
        
        signature = hmac.new(
            API_SECRET.encode('utf-8'),
            (method + timestamp + path + "" + payload_str).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "api-key": API_KEY,
            "signature": signature,
            "timestamp": timestamp,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        url = BASE_URL + path
        if method == "GET":
            return session.get(url, headers=headers, timeout=4).json()
        return session.post(url, data=payload_str, headers=headers, timeout=4).json()
    except Exception as e:
        return {"error": str(e)}

def get_product_id():
    try:
        res = session.get(f"{BASE_URL}/v2/products/{SYMBOL}", timeout=4).json()
        if res and res.get("success"):
            return int(res["result"]["id"])
    except Exception:
        pass
    return None

def get_live_price():
    try:
        res = session.get(f"{BASE_URL}/v2/tickers/{SYMBOL}", timeout=4).json()
        if res and res.get("success"):
            return float(res["result"]["close"])
    except Exception:
        pass
    return None

def fetch_candles():
    try:
        now = int(time.time())
        res = session.get(f"{BASE_URL}/v2/history/candles", params={"symbol": SYMBOL, "resolution": TIMEFRAME, "start": now - 1800, "end": now}, timeout=4).json()
        if res and res.get("result"):
            return [float(c["close"]) if isinstance(c, dict) else float(c[4]) for c in reversed(res["result"])]
    except Exception:
        pass
    return []

def calculate_er(prices):
    if len(prices) < 10:
        return 0.0
    change = abs(prices[-1] - prices[-10])
    volatility = sum(abs(prices[i] - prices[i-1]) for i in range(len(prices)-9, len(prices)))
    return change / volatility if volatility > 0 else 0.0

# ============================================================
# 5. FAST ORDER EXECUTION
# ============================================================
def place_fast_trade(side, price, product_id):
    global in_position
    
    if side == "buy":
        sl_price = round(price * (1 - SL_PCT), 5)
        tp_price = round(price * (1 + TP_PCT), 5)
    else:
        sl_price = round(price * (1 + SL_PCT), 5)
        tp_price = round(price * (1 - TP_PCT), 5)

    payload = {
        "product_id": product_id,
        "size": QTY,
        "side": side,
        "order_type": "market_order",
        "stop_loss_order": {"order_type": "market_order", "stop_price": str(sl_price)},
        "take_profit_order": {"order_type": "market_order", "stop_price": str(tp_price)}
    }

    send_telegram(f"⚡ *FAST SIGNAL TRIGGERED!*\nSending `{side.upper()}` Order at `{price}`...")
    res = private_request("POST", "/v2/orders", payload)

    if res and res.get("success"):
        in_position = True
        send_telegram(f"🚀 *ORDER EXECUTED!*\nSide: `{side.upper()}`\nEntry: `{price}`\nSL: `{sl_price}` | TP: `{tp_price}`")
    else:
        send_telegram(f"❌ *ORDER FAILED:* `{res}`")

# ============================================================
# 6. FAST TRADING SCANNER LOOP
# ============================================================
def fast_trader_loop():
    global in_position
    time.sleep(2)
    product_id = get_product_id()
    if not product_id:
        send_telegram("❌ Product ID fetch failed. Check Internet/Symbol.")
        return

    # STARTUP TELEGRAM NOTIFICATION
    send_telegram(f"⚡ *FAST TRADER LIVE ON RENDER!*\nPair: `{SYMBOL}`\nScanning every 1 second...")
    
    last_price = get_live_price()

    while True:
        try:
            time.sleep(1)
            price = get_live_price()
            if not price or not last_price:
                last_price = price
                continue

            if in_position:
                time.sleep(60)
                in_position = False
                continue

            price_change = (price - last_price) / last_price

            if abs(price_change) >= MIN_MOMENTUM:
                candles = fetch_candles()
                er = calculate_er(candles)

                if er >= MIN_ER:
                    if price_change > 0:
                        place_fast_trade("buy", price, product_id)
                    else:
                        place_fast_trade("sell", price, product_id)

            last_price = price
        except Exception as e:
            time.sleep(1)

# ============================================================
# MAIN THREADS
# ============================================================
if __name__ == "__main__":
    t_web = threading.Thread(target=run_flask)
    t_bot = threading.Thread(target=fast_trader_loop)
    
    t_web.start()
    t_bot.start()
