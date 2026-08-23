# ============================================================
# GH V12 POLLING ENGINE + FULL TELEGRAM CONTROL (/start, /stop, /status)
# DELTA EXCHANGE INDIA V2 | ARCUSD
# ============================================================

import os
import requests
import json
import time
import hmac
import hashlib
import threading

BASE_URL = "https://api.india.delta.exchange"
SYMBOL = "ARCUSD"
TIMEFRAME = "1m"
LOT_SIZE = 1

ER_LENGTH = 14
MIN_ER = 0.05

SL_PCT = 0.004
TP_PCT = SL_PCT * (0.70 / 0.30)

COOLDOWN_SECONDS = 5
MOMENTUM_LOOKBACK = 2

API_KEY = os.getenv("API_KEY", "UvOmLQABY3ppqe83KcPCWvfTxLkD8c")
API_SECRET = os.getenv("API_SECRET", "05YCaLlNEM1C7qTxBGLYSICFsiP0viEv6g3zQILtLYguaPIgYF4DSJSJBpFP")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# Bot Control State
bot_active = True  # डिफ़ॉल्ट रूप से चालू रहेगा
product_id = None
tick_size = None
candles = []
last_trade_time = 0
order_lock = threading.Lock()
order_in_progress = False

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=3, pool_connections=10, pool_maxsize=10)
session.mount("https://", adapter)
session.headers.update({"User-Agent": "GH-V12-Bot/8.0", "Accept": "application/json"})

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        session.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=3)
    except Exception as e:
        print(f"⚠️ Telegram Alert Error: {e}", flush=True)

def public_get(endpoint, params=None):
    try:
        url = BASE_URL + endpoint
        res = session.get(url, params=params, timeout=5)
        return res.json()
    except Exception as e:
        print(f"\n❌ Public API Error: {e}", flush=True)
        return None

def make_signature(method, timestamp, endpoint, query="", payload=""):
    message = method.upper() + str(timestamp) + endpoint + query + payload
    return hmac.new(API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()

def private_request(method, endpoint, params=None, body=None):
    try:
        method = method.upper()
        query = ""
        if params:
            query = "?" + "&".join([f"{k}={v}" for k, v in params.items()])
            
        payload = json.dumps(body, separators=(",", ":")) if body is not None else ""
        timestamp = str(int(time.time()))
        
        signature = make_signature(method, timestamp, endpoint, query, payload)
        
        headers = {
            "api-key": API_KEY,
            "signature": signature,
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        url = BASE_URL + endpoint
        if method == "GET":
            res = session.get(url, params=params, headers=headers, timeout=5)
        elif method == "POST":
            res = session.post(url, data=payload, headers=headers, timeout=5)
        else:
            res = session.request(method, url, params=params, data=payload, headers=headers, timeout=5)
            
        return res.json()
    except Exception as e:
        print(f"\n❌ Private API Error: {e}", flush=True)
        return None

def load_product():
    global product_id, tick_size
    for attempt in range(5):
        data = public_get("/v2/products/" + SYMBOL)
        if data and data.get("result"):
            result = data["result"]
            try:
                product_id = int(result["id"])
                tick_size = float(result.get("tick_size", 0.00001))
                msg = f"✅ PRODUCT LOADED: {SYMBOL} | ID: {product_id} | TICK: {tick_size}"
                print(msg, flush=True)
                send_telegram("🤖 GH-V12 Bot Online!\n" + msg)
                return True
            except Exception:
                pass
        print(f"⚠️ Fetching product failed. Retrying... ({attempt+1}/5)", flush=True)
        time.sleep(1)
    return False

def fetch_history():
    now = int(time.time())
    data = public_get("/v2/history/candles", {"symbol": SYMBOL, "resolution": TIMEFRAME, "start": now - 7200, "end": now})
    if not data or not data.get("result"):
        return []
    output = []
    for c in data["result"]:
        try:
            output.append({"time": int(c["time"]), "open": float(c["open"]), "high": float(c["high"]), "low": float(c["low"]), "close": float(c["close"])})
        except Exception:
            continue
    output.sort(key=lambda x: x["time"])
    return output

def get_live_price():
    data = public_get(f"/v2/tickers/{SYMBOL}")
    if data and isinstance(data, dict) and "result" in data:
        res = data["result"]
        for k in ("mark_price", "spot_price", "close"):
            val = res.get(k)
            if val is not None:
                return float(val)
    return None

def efficiency_ratio(data):
    if len(data) < ER_LENGTH + 1:
        return 0.0
    current = data[-1]["close"]
    old = data[-1 - ER_LENGTH]["close"]
    direction = abs(current - old)
    volatility = sum(abs(data[i]["close"] - data[i - 1]["close"]) for i in range(len(data) - ER_LENGTH, len(data)))
    if volatility <= 0:
        return 0.0
    return direction / volatility

def momentum_signal(price):
    if len(candles) < (MOMENTUM_LOOKBACK + 1):
        return "buy"
    reference = candles[-1 - MOMENTUM_LOOKBACK]["close"]
    if reference <= 0:
        return "buy"
    momentum = (price - reference) / reference
    return "buy" if momentum >= 0 else "sell"

def get_signal(price):
    if len(candles) < (ER_LENGTH + 2):
        return "buy", 1.0
    er = efficiency_ratio(candles)
    if er < MIN_ER:
        return "buy", er
    return momentum_signal(price), er

def get_position():
    if not product_id:
        return None
    data = private_request("GET", "/v2/positions", params={"product_id": str(product_id)})
    if not data or not isinstance(data.get("result"), dict):
        return None
    res = data["result"]
    try:
        size = int(float(res.get("size", 0)))
        entry = float(res.get("entry_price", 0))
    except Exception:
        size, entry = 0, 0.0
    return {"size": size, "entry_price": entry}

def has_position():
    pos = get_position()
    return pos and abs(pos["size"]) > 0

def place_market_order(side):
    body = {
        "product_symbol": SYMBOL, 
        "size": LOT_SIZE, 
        "side": side, 
        "order_type": "market_order", 
        "client_order_id": "GHV12_" + str(int(time.time()))
    }
    print(f"\n🚀 MARKET {side.upper()}", flush=True)
    return private_request("POST", "/v2/orders", body=body)

def wait_for_fill():
    for _ in range(10):
        pos = get_position()
        if pos and abs(pos["size"]) > 0 and pos["entry_price"] > 0:
            return pos
        time.sleep(0.3)
    return None

def round_price(price):
    if tick_size and tick_size > 0:
        return round(round(price / tick_size) * tick_size, 8)
    return round(price, 8)

def place_bracket(entry_price, side):
    if side == "buy":
        sl, tp = entry_price * (1 - SL_PCT), entry_price * (1 + TP_PCT)
    else:
        sl, tp = entry_price * (1 + SL_PCT), entry_price * (1 - TP_PCT)
    sl, tp = round_price(sl), round_price(tp)
    
    body = {
        "product_id": product_id,
        "product_symbol": SYMBOL,
        "stop_loss_order": {"order_type": "market_order", "stop_price": float(sl)},
        "take_profit_order": {"order_type": "market_order", "stop_price": float(tp)},
        "bracket_stop_trigger_method": "last_traded_price"
    }
    return private_request("POST", "/v2/orders/bracket", body=body)

def execute_trade(side, price, er):
    global last_trade_time, order_in_progress
    with order_lock:
        if order_in_progress:
            return
        order_in_progress = True

    try:
        if has_position():
            print("⚠️ Active Position Exists. Waiting...", flush=True)
            return
            
        print(f"\n⚡ EXEC_SIGNAL: {side.upper()} | PRICE: {price:.8f} | ER: {er:.4f}", flush=True)
        res = place_market_order(side)
        
        if not res or res.get("success") is False:
            err_msg = f"❌ Order Failed: {res}"
            print(err_msg, flush=True)
            send_telegram(err_msg)
            return
        
        pos = wait_for_fill()
        if not pos:
            print("🚨 Position verification pending...", flush=True)
            return
        
        entry = pos["entry_price"]
        bracket = place_bracket(entry, side)
        if not bracket or bracket.get("success") is False:
            err_msg = f"🚨 BRACKET FAILED! Response: {bracket}"
            print(err_msg, flush=True)
            send_telegram(err_msg)
            return
        
        success_msg = f"🚀 LIVE TRADE EXECUTED!\nSymbol: {SYMBOL}\nSide: {side.upper()}\nEntry: {entry:.8f}\nER: {er:.4f}\n✅ Bracket SL/TP Placed!"
        print("✅ ORDER & BRACKET SUCCESSFUL!", flush=True)
        send_telegram(success_msg)
        
        last_trade_time = time.time()
    finally:
        with order_lock:
            order_in_progress = False

# Background Thread for Telegram Commands (/start, /stop, /status)
def telegram_command_listener():
    global bot_active
    if not TELEGRAM_TOKEN:
        return
    
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    
    while True:
        try:
            res = session.get(url, params={"offset": last_update_id + 1, "timeout": 5}, timeout=10)
            data = res.json()
            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    text = msg.get("text", "").strip().lower()
                    sender_id = str(msg.get("chat", {}).get("id", ""))
                    
                    if CHAT_ID and sender_id != CHAT_ID:
                        continue
                        
                    if text == "/stop":
                        bot_active = False
                        send_telegram("🔴 TRADING ENGINE STOPPED! New trades will not be placed.")
                        print("🔴 BOT STOPPED VIA TELEGRAM", flush=True)
                    elif text == "/start":
                        bot_active = True
                        send_telegram("🟢 TRADING ENGINE RESUMED! Monitoring signals...")
                        print("🟢 BOT STARTED VIA TELEGRAM", flush=True)
                    elif text == "/status":
                        st = "🟢 RUNNING" if bot_active else "🔴 STOPPED"
                        p = get_live_price()
                        pos = get_position()
                        pos_info = f"Size: {pos['size']} | Entry: {pos['entry_price']}" if pos else "None"
                        send_telegram(f"🤖 Bot Status: {st}\nSymbol: {SYMBOL}\nPrice: {p}\nPosition: {pos_info}")
        except Exception:
            pass
        time.sleep(1)

# Start Command Listener Thread
threading.Thread(target=telegram_command_listener, daemon=True).start()

print("STARTING INSTANT POLLING ENGINE WITH COMMAND LISTENER...", flush=True)
if not load_product():
    print("❌ Failed to load product. Check connection.", flush=True)
    send_telegram("❌ Failed to load product. Check connection.")
    raise SystemExit

candles = fetch_history()
print(f"Loaded {len(candles)} candles. Starting loop...", flush=True)

last_candle_fetch = time.time()

while True:
    try:
        price = get_live_price()
        if price is None:
            time.sleep(0.3)
            continue
        
        if time.time() - last_candle_fetch > 10 or not candles:
            candles = fetch_history()
            last_candle_fetch = time.time()

        signal, er = get_signal(price)
        
        # केवल तभी ट्रेड करेगा जब bot_active True होगा
        if bot_active:
            print(f"PRICE: {price:.8f} | ER: {er:.4f} | EXEC_SIGNAL: {signal.upper()}", flush=True)
            if time.time() - last_trade_time > COOLDOWN_SECONDS:
                execute_trade(signal, price, er)
        else:
            print(f"PAUSED ⏸️ | PRICE: {price:.8f}", flush=True)
            
        time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nBot stopped.", flush=True)
        send_telegram("🛑 Bot Stopped Manually.")
        break
    except Exception as e:
        time.sleep(0.3)
