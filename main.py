# ============================================================
# ULTRA-FAST SCALPER ENGINE (DELTA EXCHANGE INDIA V2)
# SYMBOL: ARCUSD | LOTS: 3 | WIDER STOP-LOSS (SL)
# ============================================================

import os
import requests
import json
import time
import hmac
import hashlib
import threading
from flask import Flask

BASE_URL = "https://api.india.delta.exchange"
SYMBOL = "ARCUSD"
LOT_SIZE = 3                      # Updated Lot Size: 3 Lots

COOLDOWN_SECONDS = 1              # Fast Scalp Cooldown
CANDLE_TIMEFRAME_SEC = 60         # Timeframe

# Fast Scalp RSI Parameters
RSI_FAST_PERIOD = 3               
RSI_SLOW_PERIOD = 8               

# Risk Management Parameters (Wider SL & TP)
ATR_PERIOD = 10
ATR_MULTIPLIER_SL = 1.5           # Increased Stop-Loss (1.5 x ATR)
ATR_MULTIPLIER_TP = 2.5           # Expanded Target Profit (2.5 x ATR)

# API Credentials
API_KEY = os.getenv("API_KEY", "UvOmLQABY3ppqe83KcPCWvfTxLkD8c")
API_SECRET = os.getenv("API_SECRET", "05YCaLlNEM1C7qTxBGLYSICFsiP0viEv6g3zQILtLYguaPIgYF4DSJSJBpFP")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

bot_active = True
product_id = None
tick_size = None
last_trade_time = 0
order_lock = threading.Lock()
stats_lock = threading.Lock()
order_in_progress = False

wins_count = 0
losses_count = 0
initial_wallet_balance = 0.0
last_valid_balance = 0.0

current_candle = None
closed_candles = []

latest_rsi_fast = 50.0
latest_rsi_slow = 50.0
latest_price = 0.0

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=1, pool_connections=50, pool_maxsize=50)
session.mount("https://", adapter)
session.headers.update({"User-Agent": "FastScalper-Engine/2.0", "Accept": "application/json"})

# ------------------------------------------------------------
# RENDER FREE TIER PORT BINDING (FLASK)
# ------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "⚡ High-Speed Scalper Engine (Lot: 3 | Wider SL) Active 24/7!"

# ------------------------------------------------------------
# HELPER & API FUNCTIONS
# ------------------------------------------------------------
def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        session.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=2)
    except Exception:
        pass

def public_get(endpoint, params=None):
    try:
        url = BASE_URL + endpoint
        res = session.get(url, params=params, timeout=1.5)
        if res and res.status_code == 200:
            return res.json()
        return None
    except Exception:
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
            res = session.get(url, params=params, headers=headers, timeout=1.5)
        elif method == "POST":
            res = session.post(url, data=payload, headers=headers, timeout=1.5)
        else:
            res = session.request(method, url, params=params, data=payload, headers=headers, timeout=1.5)
            
        if res and res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        print(f"❌ API Error: {e}", flush=True)
        return None

def get_wallet_balance():
    global last_valid_balance
    data = private_request("GET", "/v2/wallet/balances")
    if data and data.get("result"):
        for asset in data["result"]:
            if asset.get("asset_symbol") in ("USDT", "DETO", "USD"):
                bal = float(asset.get("balance", 0.0))
                if bal > 0:
                    last_valid_balance = bal
                    return bal
    return last_valid_balance

def fetch_historical_candles():
    global closed_candles
    end_time = int(time.time())
    start_time = end_time - (30 * 60)
    params = {"symbol": SYMBOL, "resolution": "1m", "start": str(start_time), "end": str(end_time)}
    data = public_get("/v2/ohlc", params=params)
    if data and data.get("result"):
        parsed = []
        for c in data["result"]:
            parsed.append({
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "start_time": float(c["time"])
            })
        closed_candles = parsed[-30:]
        print(f"⚡ Scalper Loaded {len(closed_candles)} Candles.", flush=True)

def load_product():
    global product_id, tick_size, initial_wallet_balance
    for _ in range(5):
        data = public_get("/v2/products/" + SYMBOL)
        if data and data.get("result"):
            result = data["result"]
            try:
                product_id = int(result["id"])
                tick_size = float(result.get("tick_size", 0.00001))
                initial_wallet_balance = get_wallet_balance()
                fetch_historical_candles()
                msg = f"🚀 HIGH-SPEED SCALPER ONLINE!\nSymbol: {SYMBOL}\nLot Size: {LOT_SIZE}\nBalance: ${initial_wallet_balance:.2f}"
                print(msg, flush=True)
                send_telegram(msg)
                return True
            except Exception as e:
                print(f"Init Error: {e}")
        time.sleep(1)
    return False

def get_live_ticker_data():
    data = public_get(f"/v2/tickers/{SYMBOL}")
    if data and isinstance(data, dict) and "result" in data:
        res = data["result"]
        for k in ("mark_price", "spot_price", "close"):
            if res.get(k) is not None:
                return float(res.get(k))
    return None

# ------------------------------------------------------------
# FAST SCALPER INDICATORS & LOGIC
# ------------------------------------------------------------
def calculate_rsi(candles, period):
    if len(candles) < period + 1:
        return 50.0
    gains, losses = 0.0, 0.0
    for i in range(len(candles) - period, len(candles)):
        change = candles[i]["close"] - candles[i-1]["close"]
        if change > 0:
            gains += change
        else:
            losses += abs(change)
    if losses == 0:
        return 100.0
    rs = (gains / period) / (losses / period)
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_atr(candles, period=10):
    if len(candles) < period + 1:
        return 0.0004
    tr_list = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i-1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        tr_list.append(tr)
    return sum(tr_list[-period:]) / period

def evaluate_scalp_signal(candles):
    global latest_rsi_fast, latest_rsi_slow
    if len(candles) < 10:
        return "none", 0.0004

    latest_rsi_fast = calculate_rsi(candles, RSI_FAST_PERIOD)
    latest_rsi_slow = calculate_rsi(candles, RSI_SLOW_PERIOD)
    
    prev_candles = candles[:-1]
    prev_fast = calculate_rsi(prev_candles, RSI_FAST_PERIOD)
    prev_slow = calculate_rsi(prev_candles, RSI_SLOW_PERIOD)
    
    atr = calculate_atr(candles, ATR_PERIOD)

    if prev_fast <= prev_slow and latest_rsi_fast > latest_rsi_slow and latest_rsi_fast < 70:
        return "buy", atr
    elif prev_fast >= prev_slow and latest_rsi_fast < latest_rsi_slow and latest_rsi_fast > 30:
        return "sell", atr

    return "none", atr

def process_tick_and_detect_signal(price):
    global current_candle, closed_candles, latest_price
    latest_price = price
    now = time.time()

    if current_candle is None:
        current_candle = {"open": price, "high": price, "low": price, "close": price, "start_time": now}
        return "none", 0.0004

    current_candle["high"] = max(current_candle["high"], price)
    current_candle["low"] = min(current_candle["low"], price)
    current_candle["close"] = price

    if now - current_candle["start_time"] >= CANDLE_TIMEFRAME_SEC:
        closed_candles.append(current_candle.copy())
        if len(closed_candles) > 40:
            closed_candles.pop(0)
        current_candle = {"open": price, "high": price, "low": price, "close": price, "start_time": now}

    return evaluate_scalp_signal(closed_candles)

# ------------------------------------------------------------
# EXECUTIONS & WIDER TRAILING STOP
# ------------------------------------------------------------
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
    return pos is not None and abs(pos["size"]) > 0

def close_position_market():
    pos = get_position()
    if pos and abs(pos["size"]) > 0:
        side = "sell" if pos["size"] > 0 else "buy"
        body = {"product_symbol": SYMBOL, "size": abs(pos["size"]), "side": side, "order_type": "market_order"}
        private_request("POST", "/v2/orders", body=body)

def run_scalp_exit_loop(entry_price, side, atr, prev_bal):
    global wins_count, losses_count
    sl_dist = max(atr * ATR_MULTIPLIER_SL, 0.0005)
    tp_dist = max(atr * ATR_MULTIPLIER_TP, 0.0008)

    if side == "buy":
        current_sl = entry_price - sl_dist
        max_tp = entry_price + tp_dist
    else:
        current_sl = entry_price + sl_dist
        max_tp = entry_price - tp_dist

    while has_position():
        live_p = get_live_ticker_data()
        if live_p is None:
            time.sleep(0.05)
            continue

        if side == "buy":
            if live_p >= max_tp:
                close_position_market()
                send_telegram(f"🎯 TARGET PROFIT HIT @ {live_p:.5f}")
                break
            if live_p - sl_dist > current_sl:
                current_sl = live_p - sl_dist
            if live_p <= current_sl:
                close_position_market()
                send_telegram(f"🛑 STOP LOSS TRIGGERED @ {live_p:.5f}")
                break

        elif side == "sell":
            if live_p <= max_tp:
                close_position_market()
                send_telegram(f"🎯 TARGET PROFIT HIT @ {live_p:.5f}")
                break
            if live_p + sl_dist < current_sl:
                current_sl = live_p + sl_dist
            if live_p >= current_sl:
                close_position_market()
                send_telegram(f"🛑 STOP LOSS TRIGGERED @ {live_p:.5f}")
                break

        time.sleep(0.05)

    time.sleep(0.5)
    cur_bal = get_wallet_balance()
    pnl = cur_bal - prev_bal

    with stats_lock:
        if pnl > 0:
            wins_count += 1
            st = "🎯 WIN"
        elif pnl < 0:
            losses_count += 1
            st = "💥 LOSS"
        else:
            st = "⚖️ EVEN"

        tot = wins_count + losses_count
        wr = (wins_count / tot * 100) if tot > 0 else 0.0

    send_telegram(f"{st} | PnL: ${pnl:+.2f} | Balance: ${cur_bal:.2f} | WR: {wr:.1f}%")

def place_market_order(side):
    body = {
        "product_symbol": SYMBOL, 
        "size": LOT_SIZE, 
        "side": side, 
        "order_type": "market_order", 
        "client_order_id": "SCALP_" + str(int(time.time() * 1000))
    }
    return private_request("POST", "/v2/orders", body=body)

def execute_trade(side, price, atr):
    global last_trade_time, order_in_progress
    with order_lock:
        if order_in_progress:
            return
        order_in_progress = True

    try:
        if has_position():
            return
            
        prev_bal = get_wallet_balance()
        res = place_market_order(side)
        
        if not res or res.get("success") is False:
            return
        
        time.sleep(0.1)
        pos = get_position()
        if not pos or abs(pos["size"]) == 0:
            return
        
        entry = pos["entry_price"]
        send_telegram(f"⚡ ENTRY {side.upper()} | Lots: {LOT_SIZE} @ {entry:.5f}")
        
        threading.Thread(target=run_scalp_exit_loop, args=(entry, side, atr, prev_bal), daemon=True).start()
        last_trade_time = time.time()
    except Exception as e:
        print(f"Execute Error: {e}")
    finally:
        with order_lock:
            order_in_progress = False

# ------------------------------------------------------------
# TELEGRAM LISTENERS
# ------------------------------------------------------------
def telegram_command_listener():
    global bot_active
    if not TELEGRAM_TOKEN:
        return
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    
    while True:
        try:
            res = session.get(url, params={"offset": last_update_id + 1, "timeout": 2}, timeout=2.5)
            if res and res.status_code == 200:
                data = res.json()
                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        last_update_id = update["update_id"]
                        msg = update.get("message", {})
                        text = msg.get("text", "").strip().lower()
                        
                        if text == "/stop":
                            bot_active = False
                            send_telegram("🔴 BOT PAUSED!")
                        elif text == "/start":
                            bot_active = True
                            send_telegram("🟢 BOT RESUMED!")
                        elif text == "/status":
                            cur_bal = get_wallet_balance()
                            send_telegram(f"🤖 BOT RUNNING\nPrice: {latest_price:.5f}\nBal: ${cur_bal:.2f}")
        except Exception:
            pass
        time.sleep(0.5)

threading.Thread(target=telegram_command_listener, daemon=True).start()

# ------------------------------------------------------------
# MAIN ENGINE LOOP (0.01s High Frequency)
# ------------------------------------------------------------
def start_scalping_engine():
    print("STARTING SCALPER ENGINE (LOT SIZE: 3)...", flush=True)
    if not load_product():
        return

    while True:
        try:
            price = get_live_ticker_data()
            if price is None:
                time.sleep(0.05)
                continue

            signal, atr_val = process_tick_and_detect_signal(price)

            if bot_active and signal in ("buy", "sell"):
                if time.time() - last_trade_time > COOLDOWN_SECONDS:
                    execute_trade(signal, price, atr_val)

            time.sleep(0.01)
        except Exception as e:
            time.sleep(0.05)

# Background Loop
threading.Thread(target=start_scalping_engine, daemon=True).start()

# Render Free Tier Web Server Binding
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
