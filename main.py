# ============================================================
# PINE SCRIPT MARKET STRUCTURE SPEED ENGINE BOT (DELTA EXCHANGE)
# LOT: 3 | PIVOT (1,1) REVERSE EXIT SYSTEM (NO FIXED SL/TP)
# ============================================================

import os, requests, json, time, hmac, hashlib, threading
from flask import Flask

BASE_URL = "https://api.india.delta.exchange"
SYMBOL = "ARCUSD"
LOT_SIZE = 3                      # Updated Lot Size: 3 Lots

API_KEY = os.getenv("API_KEY", "UvOmLQABY3ppqe83KcPCWvfTxLkD8c")
API_SECRET = os.getenv("API_SECRET", "05YCaLlNEM1C7qTxBGLYSICFsiP0viEv6g3zQILtLYguaPIgYF4DSJSJBpFP")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

bot_active = True
product_id = None
last_direction = None
order_lock = threading.Lock()

candles = []
last_hh = None
last_ll = None

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=1, pool_connections=50, pool_maxsize=50)
session.mount("https://", adapter)

app = Flask('')

@app.route('/')
def home():
    return "⚡ Market Structure Speed Engine Bot (Lot: 3) Active 24/7!"

def send_telegram(msg):
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            session.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=2)
        except: pass

def private_request(method, endpoint, params=None, body=None):
    try:
        method = method.upper()
        query = "?" + "&".join([f"{k}={v}" for k, v in params.items()]) if params else ""
        payload = json.dumps(body, separators=(",", ":")) if body else ""
        timestamp = str(int(time.time()))
        msg = method + timestamp + endpoint + query + payload
        sig = hmac.new(API_SECRET.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
        
        headers = {"api-key": API_KEY, "signature": sig, "timestamp": timestamp, "Content-Type": "application/json"}
        url = BASE_URL + endpoint
        
        res = session.request(method, url, params=params, data=payload, headers=headers, timeout=1.5)
        return res.json() if res and res.status_code == 200 else None
    except:
        return None

def get_position():
    if not product_id: return 0, 0.0
    data = private_request("GET", "/v2/positions", params={"product_id": str(product_id)})
    if data and isinstance(data.get("result"), dict):
        res = data["result"]
        return int(float(res.get("size", 0))), float(res.get("entry_price", 0))
    return 0, 0.0

def execute_direction_trade(direction):
    global last_direction
    if direction == last_direction:
        return
        
    with order_lock:
        size, _ = get_position()
        
        # Reverse Signal Exit + Entry Logic
        if direction == "BUY" and size <= 0:
            if size < 0: # Close Sell Position
                private_request("POST", "/v2/orders", body={"product_symbol": SYMBOL, "size": abs(size), "side": "buy", "order_type": "market_order"})
            res = private_request("POST", "/v2/orders", body={"product_symbol": SYMBOL, "size": LOT_SIZE, "side": "buy", "order_type": "market_order"})
            if res and res.get("success"):
                send_telegram(f"🚀 PANEL DIRECTION: BULLISH MOVE (BUY 3 LOTS) @ {SYMBOL}")
                last_direction = "BUY"

        elif direction == "SELL" and size >= 0:
            if size > 0: # Close Buy Position
                private_request("POST", "/v2/orders", body={"product_symbol": SYMBOL, "size": abs(size), "side": "sell", "order_type": "market_order"})
            res = private_request("POST", "/v2/orders", body={"product_symbol": SYMBOL, "size": LOT_SIZE, "side": "sell", "order_type": "market_order"})
            if res and res.get("success"):
                send_telegram(f"🔻 PANEL DIRECTION: BEARISH PRESS (SELL 3 LOTS) @ {SYMBOL}")
                last_direction = "SELL"

def process_structure_pivots(c_data):
    global last_hh, last_ll
    if len(c_data) < 3: return
    
    prev = c_data[-3]
    curr = c_data[-2]
    nxt  = c_data[-1]
    
    # Pivot High check
    if curr['high'] > prev['high'] and curr['high'] > nxt['high']:
        ph = curr['high']
        p_type = "HH" if (last_hh is None or ph > last_hh) else "LH"
        last_hh = ph
        
        if p_type == "HH":
            execute_direction_trade("BUY")
        elif p_type == "LH":
            execute_direction_trade("SELL")

    # Pivot Low check
    if curr['low'] < prev['low'] and curr['low'] < nxt['low']:
        pl = curr['low']
        p_type = "LL" if (last_ll is None or pl < last_ll) else "HL"
        last_ll = pl
        
        if p_type == "HL":
            execute_direction_trade("BUY")
        elif p_type == "LL":
            execute_direction_trade("SELL")

def fetch_candles_and_detect():
    try:
        end = int(time.time())
        res = session.get(BASE_URL + "/v2/ohlc", params={"symbol": SYMBOL, "resolution": "1m", "start": str(end - 600), "end": str(end)}, timeout=1.5).json()
        if res and res.get("result"):
            c_list = [{"high": float(c["high"]), "low": float(c["low"]), "close": float(c["close"])} for c in res["result"]]
            process_structure_pivots(c_list)
    except: pass

def start_engine():
    global product_id
    res = session.get(BASE_URL + "/v2/products/" + SYMBOL).json()
    if res and res.get("result"):
        product_id = int(res["result"]["id"])
        send_telegram("⚡ MARKET STRUCTURE ENGINE ACTIVE (LOT SIZE: 3)!")

    while True:
        if bot_active:
            fetch_candles_and_detect()
        time.sleep(0.5)

threading.Thread(target=start_engine, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
