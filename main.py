# ============================================================
# FAST TRIPLE CONFIRMATION ENGINE WITH DYNAMIC TRAILING STOP LOSS
# DELTA EXCHANGE INDIA V2 | ARCUSD
# RULE: Rejection Candle Close + LIVE TICK BREAKOUT
# SL/TP: Dynamic ATR Based + Automatic Trailing SL (TSL)
# ============================================================

import os
import requests
import json
import time
import hmac
import hashlib
import threading
import math
from flask import Flask

BASE_URL = "https://api.india.delta.exchange"
SYMBOL = "ARCUSD"
LOT_SIZE = 3                      # 3 Lots Set

COOLDOWN_SECONDS = 5
CANDLE_TIMEFRAME_SEC = 5          # 5-Second Micro Candles
BOLLINGER_PERIOD = 20             # 20 SMA
BOLLINGER_STD = 2.0               # Standard Deviation 2.0
ATR_PERIOD = 14                   # ATR Volatility Period
ATR_MULTIPLIER_SL = 1.5           # Initial SL = 1.5 x ATR
ATR_MULTIPLIER_TP = 3.0           # Max TP Target = 3.0 x ATR

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

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=3, pool_connections=10, pool_maxsize=10)
session.mount("https://", adapter)
session.headers.update({"User-Agent": "TSL-TripleConf/1.0", "Accept": "application/json"})

# ------------------------------------------------------------
# FLASK SERVER FOR UPTIME
# ------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Trailing SL Bollinger Engine Live 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ------------------------------------------------------------
# HELPER & API FUNCTIONS
# ------------------------------------------------------------
def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        session.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=5)
    except Exception as e:
        print(f"⚠️ Telegram Error: {e}", flush=True)

def public_get(endpoint, params=None):
    try:
        url = BASE_URL + endpoint
        res = session.get(url, params=params, timeout=5)
        if res and res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        print(f"❌ Public API Error: {e}", flush=True)
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
            
        if res and res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        print(f"❌ Private API Error: {e}", flush=True)
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

def load_product():
    global product_id, tick_size, initial_wallet_balance
    for attempt in range(5):
        data = public_get("/v2/products/" + SYMBOL)
        if data and data.get("result"):
            result = data["result"]
            try:
                product_id = int(result["id"])
                tick_size = float(result.get("tick_size", 0.00001))
                initial_wallet_balance = get_wallet_balance()
                msg = (
                    f"⚡ TRAILING STOP LOSS ENGINE ONLINE!\n"
                    f"Symbol: {SYMBOL} | Lots: {LOT_SIZE}\n"
                    f"Strategy: Fast Tick Breakout + Trailing SL\n"
                    f"Balance: ${initial_wallet_balance:.2f}"
                )
                print(msg, flush=True)
                send_telegram(msg)
                return True
            except Exception:
                pass
        time.sleep(1)
    return False

def get_live_ticker_data():
    data = public_get(f"/v2/tickers/{SYMBOL}")
    if data and isinstance(data, dict) and "result" in data:
        res = data["result"]
        price = None
        for k in ("mark_price", "spot_price", "close"):
            if res.get(k) is not None:
                price = float(res.get(k))
                break
        return price
    return None

# ------------------------------------------------------------
# BOLLINGER & ATR COMPUTATION
# ------------------------------------------------------------
def calculate_bollinger_bands(candles, period=20, std_dev=2.0):
    if len(candles) < period:
        return None, None, None
    closes = [c["close"] for c in candles[-period:]]
    sma = sum(closes) / period
    variance = sum((x - sma) ** 2 for x in closes) / period
    stdev = math.sqrt(variance)
    upper_band = sma + (std_dev * stdev)
    lower_band = sma - (std_dev * stdev)
    return upper_band, sma, lower_band

def calculate_atr(candles, period=14):
    if len(candles) < period + 1:
        return 0.0005
    tr_list = []
    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i-1]["close"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)
    return sum(tr_list[-period:]) / period

def process_tick_and_detect_signal(price):
    global current_candle, closed_candles
    now = time.time()

    if current_candle is None:
        current_candle = {"open": price, "high": price, "low": price, "close": price, "start_time": now}
        return "none", 0.0

    current_candle["high"] = max(current_candle["high"], price)
    current_candle["low"] = min(current_candle["low"], price)
    current_candle["close"] = price

    if now - current_candle["start_time"] >= CANDLE_TIMEFRAME_SEC:
        closed_candles.append(current_candle.copy())
        if len(closed_candles) > 40:
            closed_candles.pop(0)

        current_candle = {"open": price, "high": price, "low": price, "close": price, "start_time": now}

    if len(closed_candles) >= BOLLINGER_PERIOD + 1:
        upper_b, sma, lower_b = calculate_bollinger_bands(closed_candles[:-1], period=BOLLINGER_PERIOD)
        if upper_b is None:
            return "none", 0.0

        c_prev = closed_candles[-1]
        atr = calculate_atr(closed_candles, period=ATR_PERIOD)

        # FAST BUY SIGNAL
        lower_touched = c_prev["low"] <= lower_b
        bullish_rejection = (c_prev["close"] > c_prev["open"]) and ((c_prev["open"] - c_prev["low"]) >= (c_prev["high"] - c_prev["close"]))
        live_high_break = price > (c_prev["high"] + (tick_size or 0.00001))

        if lower_touched and bullish_rejection and live_high_break:
            return "buy", atr

        # FAST SELL SIGNAL
        upper_touched = c_prev["high"] >= upper_b
        bearish_rejection = (c_prev["close"] < c_prev["open"]) and ((c_prev["high"] - c_prev["open"]) >= (c_prev["close"] - c_prev["low"]))
        live_low_break = price < (c_prev["low"] - (tick_size or 0.00001))

        if upper_touched and bearish_rejection and live_low_break:
            return "sell", atr

    return "none", 0.0

# ------------------------------------------------------------
# POSITIONS & TRAILING ENGINE
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

def round_price(price):
    try:
        if tick_size and tick_size > 0:
            decimals = max(0, -int(math.floor(math.log10(tick_size))))
            steps = round(price / tick_size)
            return round(steps * tick_size, decimals)
    except Exception:
        pass
    return round(price, 8)

def close_position_market():
    pos = get_position()
    if pos and abs(pos["size"]) > 0:
        side = "sell" if pos["size"] > 0 else "buy"
        body = {
            "product_symbol": SYMBOL,
            "size": abs(pos["size"]),
            "side": side,
            "order_type": "market_order"
        }
        private_request("POST", "/v2/orders", body=body)

# ------------------------------------------------------------
# LIVE TRAILING STOP LOSS THREAD
# ------------------------------------------------------------
def run_trailing_stop_loss(entry_price, side, atr, prev_bal):
    global wins_count, losses_count
    sl_dist = atr * ATR_MULTIPLIER_SL
    tp_dist = atr * ATR_MULTIPLIER_TP

    if side == "buy":
        current_sl = entry_price - sl_dist
        max_tp = entry_price + tp_dist
    else:
        current_sl = entry_price + sl_dist
        max_tp = entry_price - tp_dist

    print(f"🔄 Trailing Thread Started | Side: {side.upper()} | Init SL: {current_sl:.5f}", flush=True)

    while has_position():
        live_p = get_live_ticker_data()
        if live_p is None:
            time.sleep(0.3)
            continue

        if side == "buy":
            # Direct TP Hit
            if live_p >= max_tp:
                close_position_market()
                send_telegram(f"🎯 TARGET PROFIT HIT @ {live_p:.5f}")
                break
                
            # Trailing Up
            new_sl = live_p - sl_dist
            if new_sl > current_sl:
                current_sl = new_sl

            # SL Hit
            if live_p <= current_sl:
                close_position_market()
                send_telegram(f"🛑 TRAILING STOP LOSS TRIGGERED @ {live_p:.5f}")
                break

        elif side == "sell":
            # Direct TP Hit
            if live_p <= max_tp:
                close_position_market()
                send_telegram(f"🎯 TARGET PROFIT HIT @ {live_p:.5f}")
                break

            # Trailing Down
            new_sl = live_p + sl_dist
            if new_sl < current_sl:
                current_sl = new_sl

            # SL Hit
            if live_p >= current_sl:
                close_position_market()
                send_telegram(f"🛑 TRAILING STOP LOSS TRIGGERED @ {live_p:.5f}")
                break

        time.sleep(0.3)

    # Monitor PnL
    time.sleep(2)
    cur_bal = get_wallet_balance()
    pnl = cur_bal - prev_bal

    with stats_lock:
        if pnl > 0:
            wins_count += 1
            st = "🎉 WIN (PROFIT LOCK)"
        elif pnl < 0:
            losses_count += 1
            st = "💥 LOSS"
        else:
            st = "⚖️ BREAKEVEN"

        w_cnt, l_cnt = wins_count, losses_count
        tot = w_cnt + l_cnt
        wr = (w_cnt / tot * 100) if tot > 0 else 0.0

    report = (
        f"{st}\n"
        f"-----------------------------\n"
        f"📊 Trade PnL: ${pnl:+.2f}\n"
        f"🏆 Wins: {w_cnt} | ❌ Losses: {l_cnt} ({wr:.1f}% WinRate)\n"
        f"💳 Current Balance: ${cur_bal:.2f}"
    )
    send_telegram(report)

def place_market_order(side):
    body = {
        "product_symbol": SYMBOL, 
        "size": LOT_SIZE, 
        "side": side, 
        "order_type": "market_order", 
        "client_order_id": "GH_TSL_" + str(int(time.time()))
    }
    return private_request("POST", "/v2/orders", body=body)

def wait_for_fill():
    for _ in range(15):
        pos = get_position()
        if pos and abs(pos["size"]) > 0 and pos["entry_price"] > 0:
            return pos
        time.sleep(0.1)
    return None

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
            send_telegram(f"❌ Order Failed: {res}")
            return
        
        pos = wait_for_fill()
        if not pos:
            return
        
        entry = pos["entry_price"]

        msg = (
            f"⚡ FAST TICK TRADE EXECUTED!\n"
            f"Side: {side.upper()} | Lots: {LOT_SIZE}\n"
            f"Entry Price: {entry:.5f}\n"
            f"Trailing Mode: ACTIVE (ATR Trailing SL)\n"
            f"Balance: ${prev_bal:.2f}"
        )
        send_telegram(msg)
        
        # Start Live Trailing
        threading.Thread(target=run_trailing_stop_loss, args=(entry, side, atr, prev_bal), daemon=True).start()
        last_trade_time = time.time()
    except Exception as e:
        send_telegram(f"⚠️ Execution Exception: {e}")
    finally:
        with order_lock:
            order_in_progress = False

# ------------------------------------------------------------
# TELEGRAM LISTENERS
# ------------------------------------------------------------
def telegram_command_listener():
    global bot_active, order_in_progress
    if not TELEGRAM_TOKEN:
        return
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    
    while True:
        try:
            res = session.get(url, params={"offset": last_update_id + 1, "timeout": 2}, timeout=5)
            if res and res.status_code == 200:
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
                            send_telegram("🔴 TSL ENGINE PAUSED!")
                        elif text == "/start":
                            bot_active = True
                            send_telegram("🟢 TSL ENGINE RESUMED!")
                        elif text == "/reset":
                            with order_lock:
                                order_in_progress = False
                            send_telegram("🔄 ENGINE UNLOCKED!")
                        elif text == "/status":
                            st = "🟢 RUNNING" if bot_active else "🔴 PAUSED"
                            cur_bal = get_wallet_balance()
                            pos_status = "In Position" if has_position() else "No Active Position"
                            with stats_lock:
                                w_cnt, l_cnt = wins_count, losses_count
                            total_trades = w_cnt + l_cnt
                            wr = (w_cnt / total_trades * 100) if total_trades > 0 else 0.0
                            
                            report = (
                                f"🤖 BOT STATUS: {st}\n"
                                f"📍 Mode: Live Tick Breakout + Trailing SL\n"
                                f"📍 Position: {pos_status}\n"
                                f"🏆 Wins: {w_cnt} | ❌ Losses: {l_cnt} ({wr:.1f}% WR)\n"
                                f"💵 Balance: ${cur_bal:.2f}"
                            )
                            send_telegram(report)
        except Exception:
            pass
        time.sleep(1)

threading.Thread(target=telegram_command_listener, daemon=True).start()

# ------------------------------------------------------------
# MAIN LOOP
# ------------------------------------------------------------
print("STARTING TRAILING STOP LOSS ENGINE...", flush=True)
if not load_product():
    raise SystemExit

while True:
    try:
        price = get_live_ticker_data()
        if price is None:
            time.sleep(0.1)
            continue

        signal, atr_val = process_tick_and_detect_signal(price)
        
        if bot_active:
            if signal in ("buy", "sell") and time.time() - last_trade_time > COOLDOWN_SECONDS:
                execute_trade(signal, price, atr_val)
        time.sleep(0.1)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"⚠️ Loop Exception Recovered: {e}", flush=True)
        time.sleep(0.5)
