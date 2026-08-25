import os, requests, json, time, hmac, hashlib, threading
from flask import Flask

BASE_URL = "https://api.india.delta.exchange"
SYMBOL = "ARCUSD"
LOT_SIZE = 3

API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

bot_active = True
product_id = None
last_direction = None
order_lock = threading.Lock()

last_hh = None
last_ll = None

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=2, pool_connections=50, pool_maxsize=50)
session.mount("https://", adapter)

app = Flask('')

@app.route('/')
def home():
    return "⚡ Market Structure Speed Engine Bot Active 24/7!"

def send_telegram(msg):
    print(f"[TELEGRAM] {msg}", flush=True)
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            session.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                         json={"chat_id": CHAT_ID, "text": msg}, timeout=2)
        except Exception as e:
            print(f"Telegram Error: {e}", flush=True)

def private_request(method, endpoint, params=None, body=None):
    try:
        method = method.upper()
        query = "?" + "&".join([f"{k}={v}" for k, v in params.items()]) if params else ""
        payload = json.dumps(body, separators=(",", ":")) if body else ""
        timestamp = str(int(time.time()))
        msg = method + timestamp + endpoint + query + payload
        sig = hmac.new(API_SECRET.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
        
        headers = {
            "api-key": API_KEY, 
            "signature": sig, 
            "timestamp": timestamp, 
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        url = BASE_URL + endpoint
        res = session.request(method, url, params=params, data=payload, headers=headers, timeout=2.5)
        return res.json() if res and res.status_code == 200 else None
    except Exception as e:
        print(f"API Request Error: {e}", flush=True)
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
        print(f"⚡ EXECUTION TRIGGERED: {direction} | Current Pos: {size}", flush=True)
        
        target_size = LOT_SIZE if direction == "BUY" else -LOT_SIZE
        order_size = abs(target_size - size)

        if order_size > 0:
            side = "buy" if direction == "BUY" else "sell"
            payload = {
                "product_symbol": SYMBOL,
                "size": order_size,
                "side": side,
                "order_type": "market_order"
            }
            res = private_request("POST", "/v2/orders", body=payload)
            if res and res.get("success"):
                send_telegram(f"🚀 SMC EXECUTED: {direction} {order_size} LOTS @ {SYMBOL}")
                last_direction = direction
            else:
                send_telegram(f"❌ ORDER FAILED: {res}")

def process_structure_pivots(c_data):
    global last_hh, last_ll
    if len(c_data) < 3: return
    
    # Pivot (1, 1) Window
    c1 = c_data[-3]
    c2 = c_data[-2]
    c3 = c_data[-1]

    # Check Swing High (Pivot High)
    if c2['high'] > c1['high'] and c2['high'] > c3['high']:
        ph = c2['high']
        if last_hh is None or ph > last_hh:
            execute_direction_trade("BUY")
        else:
            execute_direction_trade("SELL")
        last_hh = ph  # Continuous state update

    # Check Swing Low (Pivot Low)
    if c2['low'] < c1['low'] and c2['low'] < c3['low']:
        pl = c2['low']
        if last_ll is None or pl < last_ll:
            execute_direction_trade("SELL")
        else:
            execute_direction_trade("BUY")
        last_ll = pl  # Continuous state update

def fetch_candles_and_detect():
    try:
        now = int(time.time())
        start_time = now - 1800  # 30 candles (1800 sec)
        
        # Delta Official REST Candles Endpoint
        url = f"{BASE_URL}/v2/history/candles"
        params = {
            "symbol": SYMBOL,
            "resolution": "1m",
            "start": str(start_time),
            "end": str(now)
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        res = session.get(url, params=params, headers=headers, timeout=4.0)
        
        if res.status_code == 200:
            data = res.json()
            raw_candles = data.get("result", [])
            if raw_candles:
                c_list = [{"high": float(c["high"]), "low": float(c["low"]), "close": float(c["close"])} for c in raw_candles]
                c_list = c_list[-30:]
                process_structure_pivots(c_list)
        else:
            print(f"API HTTP Status Error: {res.status_code} | Body: {res.text}", flush=True)

    except Exception as e:
        print(f"Fetch Error: {e}", flush=True)

def start_engine():
    global product_id
    try:
        res = session.get(f"{BASE_URL}/v2/products/{SYMBOL}", headers={"User-Agent": "Mozilla/5.0"}, timeout=5.0).json()
        if res and res.get("result"):
            product_id = int(res["result"]["id"])
            send_telegram(f"⚡ MARKET STRUCTURE ENGINE ACTIVE (30 CANDLES / LOT: {LOT_SIZE})!")
    except Exception as e:
        print(f"Product Fetch Error: {e}", flush=True)

    while True:
        if bot_active:
            fetch_candles_and_detect()
        time.sleep(2)

threading.Thread(target=start_engine, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
