import os, requests, json, time, hmac, hashlib, threading
from flask import Flask

BASE_URL = "https://api.india.delta.exchange"
SYMBOL = "ARCUSD"

# RISK & TRADE SETTINGS
LOT_SIZE = 3           # Lot Size
SL_PERCENT = 0.008      # 0.8% Stop Loss
TP_PERCENT = 0.015      # 1.5% Take Profit

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
    return "⚡ Micro Structure Bot Fully Verified & Active 24/7!"

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

def cancel_open_orders():
    """नए ट्रेड से पहले पुराने ब्रैकेट ऑर्डर्स को कैंसिल करता है"""
    if not product_id: return
    try:
        private_request("DELETE", "/v2/orders/all", params={"product_id": str(product_id)})
    except Exception as e:
        print(f"Cancel Orders Error: {e}", flush=True)

def get_position():
    if not product_id: return 0, 0.0
    data = private_request("GET", "/v2/positions", params={"product_id": str(product_id)})
    if data and isinstance(data.get("result"), dict):
        res = data["result"]
        return int(float(res.get("size", 0))), float(res.get("entry_price", 0))
    return 0, 0.0

def place_bracket_orders(entry_price, direction, size):
    if entry_price <= 0: return
    
    if direction == "BUY":
        stop_loss_price = round(entry_price * (1 - SL_PERCENT), 4)
        take_profit_price = round(entry_price * (1 + TP_PERCENT), 4)
        close_side = "sell"
    else:
        stop_loss_price = round(entry_price * (1 + SL_PERCENT), 4)
        take_profit_price = round(entry_price * (1 - TP_PERCENT), 4)
        close_side = "buy"

    # Stop Loss Order
    sl_payload = {
        "product_symbol": SYMBOL,
        "size": size,
        "side": close_side,
        "order_type": "stop_market_order",
        "stop_price": str(stop_loss_price)
    }
    private_request("POST", "/v2/orders", body=sl_payload)

    # Take Profit Order
    tp_payload = {
        "product_symbol": SYMBOL,
        "size": size,
        "side": close_side,
        "order_type": "limit_order",
        "limit_price": str(take_profit_price)
    }
    private_request("POST", "/v2/orders", body=tp_payload)

    send_telegram(f"🛡️ SL/TP SET: SL @ {stop_loss_price} | TP @ {take_profit_price}")

def execute_direction_trade(direction, structure_type):
    global last_direction
    if direction == last_direction:
        return False
        
    with order_lock:
        size, entry_price = get_position()
        print(f"⚡ EXECUTION TRIGGERED [{structure_type}]: {direction} | Pos: {size}", flush=True)
        
        target_size = LOT_SIZE if direction == "BUY" else -LOT_SIZE
        order_size = abs(target_size - size)

        if order_size > 0:
            # पुराने पेंडिंग ऑर्डर्स साफ़ करें
            cancel_open_orders()
            
            side = "buy" if direction == "BUY" else "sell"
            payload = {
                "product_symbol": SYMBOL,
                "size": order_size,
                "side": side,
                "order_type": "market_order"
            }
            res = private_request("POST", "/v2/orders", body=payload)
            if res and res.get("success"):
                send_telegram(f"🚀 [{structure_type}] EXECUTED: {direction} {order_size} LOTS @ {SYMBOL}")
                last_direction = direction
                
                # Dynamic Sync to get correct entry price
                current_entry = 0.0
                for _ in range(5):
                    time.sleep(0.5)
                    _, current_entry = get_position()
                    if current_entry > 0:
                        break
                
                if current_entry > 0:
                    place_bracket_orders(current_entry, direction, order_size)
                return True
            else:
                send_telegram(f"❌ ORDER FAILED: {res}")
                return False
    return False

def process_3_segment_structure(c_data):
    global last_hh, last_ll
    if len(c_data) < 3: return
    
    prev_candle = c_data[-2]
    curr_candle = c_data[-1]

    curr_high = curr_candle['high']
    curr_low = curr_candle['low']
    curr_close = curr_candle['close']

    if last_hh is None: last_hh = prev_candle['high']
    if last_ll is None: last_ll = prev_candle['low']

    # 3-Segment Candle Math
    rng = curr_high - curr_low
    if rng > 0:
        one_third = rng / 3.0
        upper_segment = curr_high - one_third
        lower_segment = curr_low + one_third
        
        in_upper_segment = curr_close >= upper_segment
        in_lower_segment = curr_close <= lower_segment
    else:
        in_upper_segment = True
        in_lower_segment = True

    # Structure Trigger Logic
    if curr_high > last_hh and in_upper_segment:
        if execute_direction_trade("BUY", "HH - BULLISH"):
            last_hh = curr_high

    elif curr_low < last_ll and in_lower_segment:
        if execute_direction_trade("SELL", "LL - BEARISH"):
            last_ll = curr_low

    elif curr_high <= last_hh and curr_low > last_ll:
        if in_upper_segment:
            execute_direction_trade("BUY", "HL - REVERSAL")
        elif in_lower_segment:
            execute_direction_trade("SELL", "LH - REVERSAL")

def fetch_candles_and_detect():
    try:
        now = int(time.time())
        start_time = now - 600
        
        url = f"{BASE_URL}/v2/history/candles"
        params = {
            "symbol": SYMBOL,
            "resolution": "1m",
            "start": str(start_time),
            "end": str(now)
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        res = session.get(url, params=params, headers=headers, timeout=3.0)
        
        if res.status_code == 200:
            data = res.json()
            raw_candles = data.get("result", [])
            if raw_candles:
                c_list = []
                for c in raw_candles:
                    h = float(c["high"]) if c.get("high") is not None else 0.0
                    l = float(c["low"]) if c.get("low") is not None else 0.0
                    cl = float(c["close"]) if c.get("close") is not None else 0.0
                    c_list.append({"high": h, "low": l, "close": cl})
                
                process_3_segment_structure(c_list)

    except Exception as e:
        print(f"Fetch Error: {e}", flush=True)

def start_engine():
    global product_id
    try:
        res = session.get(f"{BASE_URL}/v2/products/{SYMBOL}", headers={"User-Agent": "Mozilla/5.0"}, timeout=5.0).json()
        if res and res.get("result"):
            product_id = int(res["result"]["id"])
            send_telegram(f"⚡ FAST HH/LL BOT WITH SAFE SL/TP (LOT: {LOT_SIZE}) ACTIVE!")
    except Exception as e:
        print(f"Product Fetch Error: {e}", flush=True)

    while True:
        if bot_active:
            fetch_candles_and_detect()
        time.sleep(1.5)

threading.Thread(target=start_engine, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
