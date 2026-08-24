# ============================================================
# ULTRA-FAST 50-STRATEGY ENSEMBLE ENGINE (MAX SPEED EDITION)
# DELTA EXCHANGE INDIA V2 | ARCUSD (1-MIN TIMEFRAME)
# FEATURES: Low Threshold 20/50 (40%), 100ms Execution Loop, Fast Telegram & Terminal Updates
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
LOT_SIZE = 1                      # Lot Size

COOLDOWN_SECONDS = 5              # Cooldown reduced to 5s
CANDLE_TIMEFRAME_SEC = 60         # 1-Minute Timeframe
SCORE_THRESHOLD = 20              # 40% Score Threshold (Super Fast Execution Trigger)

ATR_PERIOD = 14
ATR_MULTIPLIER_SL = 1.5           # Trailing Stop-Loss = 1.5 x ATR
ATR_MULTIPLIER_TP = 3.0           # Target Profit = 3.0 x ATR

# Environment Variables
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

latest_bull_score = 0
latest_bear_score = 0
latest_price = 0.0
last_score_telegram_time = 0

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=2, pool_connections=20, pool_maxsize=20)
session.mount("https://", adapter)
session.headers.update({"User-Agent": "Fast-50Engine/3.0", "Accept": "application/json"})

# ------------------------------------------------------------
# FLASK SERVER FOR UPTIME
# ------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Ultra-Fast 50-Strategy Engine Live 24/7!"

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
        session.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=3)
    except Exception as e:
        print(f"⚠️ Telegram Error: {e}", flush=True)

def public_get(endpoint, params=None):
    try:
        url = BASE_URL + endpoint
        res = session.get(url, params=params, timeout=2)
        if res and res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
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
            res = session.get(url, params=params, headers=headers, timeout=2)
        elif method == "POST":
            res = session.post(url, data=payload, headers=headers, timeout=2)
        else:
            res = session.request(method, url, params=params, data=payload, headers=headers, timeout=2)
            
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

def fetch_historical_candles():
    global closed_candles
    end_time = int(time.time())
    start_time = end_time - (75 * 60)
    params = {
        "symbol": SYMBOL,
        "resolution": "1m",
        "start": str(start_time),
        "end": str(end_time)
    }
    data = public_get("/v2/ohlc", params=params)
    if data and data.get("result"):
        raw_candles = data["result"]
        parsed = []
        for c in raw_candles:
            parsed.append({
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "start_time": float(c["time"])
            })
        closed_candles = parsed[-70:]
        print(f"✅ Pre-loaded {len(closed_candles)} historical 1-Min candles.", flush=True)

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
                fetch_historical_candles()
                msg = (
                    f"⚡ ULTRA-FAST 50-STRATEGY ENGINE ONLINE!\n"
                    f"Symbol: {SYMBOL} | Lots: {LOT_SIZE}\n"
                    f"Threshold: {SCORE_THRESHOLD}/50 (Fast Mode 40%)\n"
                    f"Balance: ${initial_wallet_balance:.2f}"
                )
                print(msg, flush=True)
                send_telegram(msg)
                return True
            except Exception as e:
                print(f"Product Init Error: {e}")
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
# MATHEMATICAL INDICATORS
# ------------------------------------------------------------
def calculate_ema(candles, period):
    if len(candles) < period:
        return None
    closes = [c["close"] for c in candles]
    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = (price * k) + (ema * (1 - k))
    return ema

def calculate_bollinger_bands(candles, period=20, std_dev=2.0):
    if len(candles) < period:
        return None, None, None
    closes = [c["close"] for c in candles[-period:]]
    sma = sum(closes) / period
    variance = sum((x - sma) ** 2 for x in closes) / period
    stdev = math.sqrt(variance)
    return sma + (std_dev * stdev), sma, sma - (std_dev * stdev)

def calculate_atr(candles, period=14):
    if len(candles) < period + 1:
        return 0.0005
    tr_list = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i-1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        tr_list.append(tr)
    return sum(tr_list[-period:]) / period

def calculate_rsi(candles, period=14):
    if len(candles) < period + 1:
        return 50.0
    gains, losses = 0.0, 0.0
    for i in range(len(candles) - period, len(candles)):
        change = candles[i]["close"] - candles[i-1]["close"]
        if change > 0: gains += change
        else: losses += abs(change)
    if losses == 0: return 100.0
    rs = (gains / period) / (losses / period)
    return 100.0 - (100.0 / (1.0 + rs))

# ------------------------------------------------------------
# 50-STRATEGY SCORING MATRIX ENGINE
# ------------------------------------------------------------
def evaluate_50_strategies(price, candles):
    global latest_bull_score, latest_bear_score, latest_price
    latest_price = price

    if len(candles) < 55:
        return "none", 0.0, 0, 0

    bullish_score = 0
    bearish_score = 0
    c = candles[-1]
    c_prev = candles[-2]
    c_prev2 = candles[-3]
    
    total_range = max(c["high"] - c["low"], 0.00001)
    lower_wick = min(c["open"], c["close"]) - c["low"]
    upper_wick = c["high"] - max(c["open"], c["close"])
    body_size = abs(c["close"] - c["open"])
    
    ema_9 = calculate_ema(candles, 9) or price
    ema_20 = calculate_ema(candles, 20) or price
    ema_50 = calculate_ema(candles, 50) or price
    upper_b, sma_20, lower_b = calculate_bollinger_bands(candles, 20, 2.0)
    sma_20 = sma_20 or price
    upper_b = upper_b or price
    lower_b = lower_b or price
    atr = calculate_atr(candles, 14)
    rsi = calculate_rsi(candles, 14)

    # 1. Trend & Structure
    if price > ema_50: bullish_score += 1
    else: bearish_score += 1
    if price > ema_20: bullish_score += 1
    else: bearish_score += 1
    if price > ema_9: bullish_score += 1
    else: bearish_score += 1
    if ema_9 > ema_20: bullish_score += 1
    else: bearish_score += 1
    if ema_20 > ema_50: bullish_score += 1
    else: bearish_score += 1
    if c["close"] > c_prev["high"]: bullish_score += 1
    if c["close"] < c_prev["low"]: bearish_score += 1
    if c["low"] > c_prev["low"]: bullish_score += 1
    if c["high"] < c_prev["high"]: bearish_score += 1
    if c["close"] > c_prev2["high"]: bullish_score += 1
    if c["close"] < c_prev2["low"]: bearish_score += 1
    if price > sma_20: bullish_score += 1
    else: bearish_score += 1
    if c["open"] > ema_50 and c["close"] > ema_50: bullish_score += 1
    if c["open"] < ema_50 and c["close"] < ema_50: bearish_score += 1
    if c_prev["close"] > ema_20: bullish_score += 1
    else: bearish_score += 1

    # 2. Volatility & Bollinger
    if c["low"] <= lower_b: bullish_score += 1
    if c["high"] >= upper_b: bearish_score += 1
    if (lower_wick / total_range) >= 0.40: bullish_score += 1
    if (upper_wick / total_range) >= 0.40: bearish_score += 1
    if (lower_wick / total_range) >= 0.50: bullish_score += 1
    if (upper_wick / total_range) >= 0.50: bearish_score += 1
    if total_range > (atr * 1.2):
        if c["close"] > c["open"]: bullish_score += 1
        else: bearish_score += 1
    if total_range < (atr * 0.8):
        if price > ema_20: bullish_score += 1
        else: bearish_score += 1
    if c["close"] > upper_b: bullish_score += 1
    if c["close"] < lower_b: bearish_score += 1
    if lower_wick > body_size: bullish_score += 1
    if upper_wick > body_size: bearish_score += 1
    if c["low"] > lower_b and c_prev["low"] <= lower_b: bullish_score += 1
    if c["high"] < upper_b and c_prev["high"] >= upper_b: bearish_score += 1
    if (upper_b - lower_b) > (atr * 2.5):
        if price > ema_9: bullish_score += 1
        else: bearish_score += 1

    # 3. Momentum & Oscillator
    if rsi < 30: bullish_score += 1
    if rsi > 70: bearish_score += 1
    if 50 < rsi < 65: bullish_score += 1
    if 35 < rsi < 50: bearish_score += 1
    if rsi > 50 and price > ema_20: bullish_score += 1
    if rsi < 50 and price < ema_20: bearish_score += 1
    if c["close"] > c["open"] and c_prev["close"] > c_prev["open"]: bullish_score += 1
    if c["close"] < c["open"] and c_prev["close"] < c_prev["open"]: bearish_score += 1
    if c["close"] > (c["high"] + c["low"]) / 2: bullish_score += 1
    if c["close"] < (c["high"] + c["low"]) / 2: bearish_score += 1

    # 4. Micro Patterns & FVG
    if c_prev2["high"] < c["low"]: bullish_score += 1
    if c_prev2["low"] > c["high"]: bearish_score += 1
    if c["close"] > c_prev["open"] and c["open"] < c_prev["close"]: bullish_score += 1
    if c["close"] < c_prev["open"] and c["open"] > c_prev["close"]: bearish_score += 1
    if c["low"] < c_prev["low"] and c["close"] > c_prev["high"]: bullish_score += 1
    if c["high"] > c_prev["high"] and c["close"] < c_prev["low"]: bearish_score += 1
    if c["close"] > (c_prev["open"] + c_prev["close"])/2 and c_prev["close"] < c_prev["open"]: bullish_score += 1
    if c["close"] < (c_prev["open"] + c_prev["close"])/2 and c_prev["close"] > c_prev["open"]: bearish_score += 1
    if price > (c_prev["high"] + (tick_size or 0.00001)): bullish_score += 1
    if price < (c_prev["low"] - (tick_size or 0.00001)): bearish_score += 1

    latest_bull_score = bullish_score
    latest_bear_score = bearish_score

    # FAST THRESHOLD (20)
    if bullish_score >= SCORE_THRESHOLD and bullish_score > bearish_score:
        return "buy", atr, bullish_score, bearish_score
    elif bearish_score >= SCORE_THRESHOLD and bearish_score > bullish_score:
        return "sell", atr, bullish_score, bearish_score

    return "none", atr, bullish_score, bearish_score

def process_tick_and_detect_signal(price):
    global current_candle, closed_candles
    now = time.time()

    if current_candle is None:
        current_candle = {"open": price, "high": price, "low": price, "close": price, "start_time": now}
        return "none", 0.0, 0, 0

    current_candle["high"] = max(current_candle["high"], price)
    current_candle["low"] = min(current_candle["low"], price)
    current_candle["close"] = price

    if now - current_candle["start_time"] >= CANDLE_TIMEFRAME_SEC:
        closed_candles.append(current_candle.copy())
        if len(closed_candles) > 75:
            closed_candles.pop(0)
        current_candle = {"open": price, "high": price, "low": price, "close": price, "start_time": now}

    return evaluate_50_strategies(price, closed_candles)

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

    while has_position():
        live_p = get_live_ticker_data()
        if live_p is None:
            time.sleep(0.1)
            continue

        if side == "buy":
            if live_p >= max_tp:
                close_position_market()
                send_telegram(f"🎯 TARGET PROFIT HIT @ {live_p:.5f}")
                break
                
            new_sl = live_p - sl_dist
            if new_sl > current_sl:
                current_sl = new_sl

            if live_p <= current_sl:
                close_position_market()
                send_telegram(f"🛑 TRAILING STOP LOSS TRIGGERED @ {live_p:.5f}")
                break

        elif side == "sell":
            if live_p <= max_tp:
                close_position_market()
                send_telegram(f"🎯 TARGET PROFIT HIT @ {live_p:.5f}")
                break

            new_sl = live_p + sl_dist
            if new_sl < current_sl:
                current_sl = new_sl

            if live_p >= current_sl:
                close_position_market()
                send_telegram(f"🛑 TRAILING STOP LOSS TRIGGERED @ {live_p:.5f}")
                break

        time.sleep(0.1)

    time.sleep(1)
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
        f"🏆 Wins: {w_cnt} | ❌ Losses: {l_cnt} ({wr:.1f}% WR)\n"
        f"💳 Current Balance: ${cur_bal:.2f}"
    )
    send_telegram(report)

def place_market_order(side):
    body = {
        "product_symbol": SYMBOL, 
        "size": LOT_SIZE, 
        "side": side, 
        "order_type": "market_order", 
        "client_order_id": "FAST50_" + str(int(time.time()))
    }
    return private_request("POST", "/v2/orders", body=body)

def wait_for_fill():
    for _ in range(15):
        pos = get_position()
        if pos and abs(pos["size"]) > 0 and pos["entry_price"] > 0:
            return pos
        time.sleep(0.05)
    return None

def execute_trade(side, price, atr, score):
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
            f"⚡ FAST TRADE EXECUTED!\n"
            f"Side: {side.upper()} | Lots: {LOT_SIZE}\n"
            f"Confluence Score: {score}/50\n"
            f"Entry Price: {entry:.5f}\n"
            f"Balance: ${prev_bal:.2f}"
        )
        send_telegram(msg)
        
        threading.Thread(target=run_trailing_stop_loss, args=(entry, side, atr, prev_bal), daemon=True).start()
        last_trade_time = time.time()
    except Exception as e:
        send_telegram(f"⚠️ Execution Exception: {e}")
    finally:
        with order_lock:
            order_in_progress = False

# ------------------------------------------------------------
# TELEGRAM LISTENERS & AUTO SCORE BROADCASTER
# ------------------------------------------------------------
def send_status_report():
    st = "🟢 RUNNING" if bot_active else "🔴 PAUSED"
    cur_bal = get_wallet_balance()
    pos_status = "In Position" if has_position() else "No Active Position"
    with stats_lock:
        w_cnt, l_cnt = wins_count, losses_count
    total_trades = w_cnt + l_cnt
    wr = (w_cnt / total_trades * 100) if total_trades > 0 else 0.0
    
    report = (
        f"🤖 BOT STATUS: {st}\n"
        f"-----------------------------\n"
        f"💵 Price: {latest_price:.5f}\n"
        f"📈 Bull: {latest_bull_score}/50 | 📉 Bear: {latest_bear_score}/50\n"
        f"🎯 Target Threshold: {SCORE_THRESHOLD}/50\n"
        f"📍 Position: {pos_status}\n"
        f"🏆 Wins: {w_cnt} | ❌ Losses: {l_cnt} ({wr:.1f}% WR)\n"
        f"💳 Balance: ${cur_bal:.2f}"
    )
    send_telegram(report)

def telegram_command_listener():
    global bot_active, order_in_progress
    if not TELEGRAM_TOKEN:
        return
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    
    while True:
        try:
            res = session.get(url, params={"offset": last_update_id + 1, "timeout": 2}, timeout=3)
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
                            send_telegram("🔴 ENGINE PAUSED!")
                        elif text == "/start":
                            bot_active = True
                            send_telegram("🟢 ENGINE RESUMED!")
                        elif text == "/reset":
                            with order_lock:
                                order_in_progress = False
                            send_telegram("🔄 ENGINE UNLOCKED!")
                        elif text == "/status":
                            send_status_report()
        except Exception:
            pass
        time.sleep(0.5)

threading.Thread(target=telegram_command_listener, daemon=True).start()

# ------------------------------------------------------------
# MAIN EXECUTION LOOP (100ms Speed)
# ------------------------------------------------------------
print("STARTING ULTRA-FAST 50-STRATEGY ENGINE...", flush=True)
if not load_product():
    raise SystemExit

last_score_telegram_time = time.time()

while True:
    try:
        price = get_live_ticker_data()
        if price is None:
            time.sleep(0.1)
            continue

        signal, atr_val, bull_score, bear_score = process_tick_and_detect_signal(price)
        
        print(f"⏱️ P: {price:.5f} | Bull: {bull_score}/50 | Bear: {bear_score}/50 | Target: {SCORE_THRESHOLD}", flush=True)

        if time.time() - last_score_telegram_time >= 300:
            send_status_report()
            last_score_telegram_time = time.time()

        if bot_active:
            if signal in ("buy", "sell") and time.time() - last_trade_time > COOLDOWN_SECONDS:
                score_used = bull_score if signal == "buy" else bear_score
                execute_trade(signal, price, atr_val, score_used)
        time.sleep(0.1)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"⚠️ Loop Exception: {e}", flush=True)
        time.sleep(0.1)
