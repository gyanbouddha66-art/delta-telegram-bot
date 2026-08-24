# ============================================================
# MULTI-FACTOR 50-STRATEGY ENSEMBLE ENGINE
# DELTA EXCHANGE INDIA V2 | ARCUSD (1-MIN TIMEFRAME)
# ARCHITECTURE: 70% Confluence Matrix (35/50 Score Threshold)
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

COOLDOWN_SECONDS = 10
CANDLE_TIMEFRAME_SEC = 60         # 1-Minute Timeframe
SCORE_THRESHOLD = 35              # 70% Confluence Rule (35/50)

ATR_PERIOD = 14
ATR_MULTIPLIER_SL = 1.5           # Trailing Stop-Loss = 1.5 x ATR
ATR_MULTIPLIER_TP = 3.0           # Target Profit = 3.0 x ATR

# Environment Variables (Fallback keys kept secure)
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
session.headers.update({"User-Agent": "MultiFactor-50Engine/2.0", "Accept": "application/json"})

# ------------------------------------------------------------
# FLASK SERVER FOR UPTIME
# ------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "50-Strategy Multi-Factor Decision Engine Live 24/7!"

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
                    f"🚀 50-STRATEGY ENGINE ONLINE!\n"
                    f"Symbol: {SYMBOL} | Lots: {LOT_SIZE}\n"
                    f"Confluence Threshold: {SCORE_THRESHOLD}/50 (70% Score)\n"
                    f"Initial Balance: ${initial_wallet_balance:.2f}"
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
# MATHEMATICAL INDICATOR CALCULATIONS
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
    
    # Pre-calculated Indicators
    ema_9 = calculate_ema(candles, 9) or price
    ema_20 = calculate_ema(candles, 20) or price
    ema_50 = calculate_ema(candles, 50) or price
    upper_b, sma_20, lower_b = calculate_bollinger_bands(candles, 20, 2.0)
    sma_20 = sma_20 or price
    upper_b = upper_b or price
    lower_b = lower_b or price
    atr = calculate_atr(candles, 14)
    rsi = calculate_rsi(candles, 14)

    # --------------------------------------------------------
    # CATEGORY 1: TREND & STRUCTURE (15 STRATEGIES)
    # --------------------------------------------------------
    if price > ema_50: bullish_score += 1; 
    else: bearish_score += 1                                  # 1. 50 EMA Trend
    if price > ema_20: bullish_score += 1; 
    else: bearish_score += 1                                  # 2. 20 EMA Trend
    if price > ema_9: bullish_score += 1; 
    else: bearish_score += 1                                   # 3. 9 EMA Micro Trend
    if ema_9 > ema_20: bullish_score += 1; 
    else: bearish_score += 1                                  # 4. Fast EMA Cross
    if ema_20 > ema_50: bullish_score += 1; 
    else: bearish_score += 1                                 # 5. Medium EMA Cross
    if c["close"] > c_prev["high"]: bullish_score += 1       # 6. Bullish BOS (Structure Break)
    if c["close"] < c_prev["low"]: bearish_score += 1        # 7. Bearish BOS
    if c["low"] > c_prev["low"]: bullish_score += 1          # 8. Higher Low Structure
    if c["high"] < c_prev["high"]: bearish_score += 1        # 9. Lower High Structure
    if c["close"] > c_prev2["high"]: bullish_score += 1      # 10. Multi-Candle Breakout Up
    if c["close"] < c_prev2["low"]: bearish_score += 1       # 11. Multi-Candle Breakout Down
    if price > sma_20: bullish_score += 1; 
    else: bearish_score += 1                                  # 12. Mid-Band Trend Alignment
    if c["open"] > ema_50 and c["close"] > ema_50: bullish_score += 1 # 13. Pure Bull Body above EMA
    if c["open"] < ema_50 and c["close"] < ema_50: bearish_score += 1 # 14. Pure Bear Body below EMA
    if c_prev["close"] > ema_20: bullish_score += 1; 
    else: bearish_score += 1                                 # 15. Previous Candle Trend Check

    # --------------------------------------------------------
    # CATEGORY 2: VOLATILITY & BOLLINGER (15 STRATEGIES)
    # --------------------------------------------------------
    if c["low"] <= lower_b: bullish_score += 1               # 16. Lower BB Rejection Zone
    if c["high"] >= upper_b: bearish_score += 1              # 17. Upper BB Rejection Zone
    if (lower_wick / total_range) >= 0.40: bullish_score += 1# 18. Strong Bullish Wick (40%+)
    if (upper_wick / total_range) >= 0.40: bearish_score += 1# 19. Strong Bearish Wick (40%+)
    if (lower_wick / total_range) >= 0.50: bullish_score += 1# 20. Extreme Bullish Pinbar (50%+)
    if (upper_wick / total_range) >= 0.50: bearish_score += 1# 21. Extreme Bearish Pinbar (50%+)
    if total_range > (atr * 1.2):                            # 22. Volatility Expansion Filter
        if c["close"] > c["open"]: bullish_score += 1
        else: bearish_score += 1
    if total_range < (atr * 0.8):                            # 23. Compression Squeeze Filter
        if price > ema_20: bullish_score += 1
        else: bearish_score += 1
    if c["close"] > upper_b: bullish_score += 1              # 24. Upper BB Momentum Ride
    if c["close"] < lower_b: bearish_score += 1              # 25. Lower BB Momentum Ride
    if lower_wick > body_size: bullish_score += 1            # 26. Wick > Body Bullish Power
    if upper_wick > body_size: bearish_score += 1            # 27. Wick > Body Bearish Power
    if c["low"] > lower_b and c_prev["low"] <= lower_b: bullish_score += 1 # 28. BB Bounce Confirmation
    if c["high"] < upper_b and c_prev["high"] >= upper_b: bearish_score += 1 # 29. BB Drop Confirmation
    if (upper_b - lower_b) > (atr * 2.5):                    # 30. High Band Width Volatility
        if price > ema_9: bullish_score += 1
        else: bearish_score += 1

    # --------------------------------------------------------
    # CATEGORY 3: MOMENTUM & OSCILLATOR PROXIES (10 STRATEGIES)
    # --------------------------------------------------------
    if rsi < 30: bullish_score += 1                          # 31. RSI Oversold
    if rsi > 70: bearish_score += 1                          # 32. RSI Overbought
    if 50 < rsi < 65: bullish_score += 1                     # 33. RSI Bullish Momentum Zone
    if 35 < rsi < 50: bearish_score += 1                     # 34. RSI Bearish Momentum Zone
    if rsi > 50 and price > ema_20: bullish_score += 1       # 35. RSI + Price Confluence Bull
    if rsi < 50 and price < ema_20: bearish_score += 1       # 36. RSI + Price Confluence Bear
    if c["close"] > c["open"] and c_prev["close"] > c_prev["open"]: bullish_score += 1 # 37. Double Green Candles
    if c["close"] < c["open"] and c_prev["close"] < c_prev["open"]: bearish_score += 1 # 38. Double Red Candles
    if c["close"] > (c["high"] + c["low"]) / 2: bullish_score += 1 # 39. Close in Upper 50% Range
    if c["close"] < (c["high"] + c["low"]) / 2: bearish_score += 1 # 40. Close in Lower 50% Range

    # --------------------------------------------------------
    # CATEGORY 4: MICRO STRUCTURE, FVG & PATTERNS (10 STRATEGIES)
    # --------------------------------------------------------
    if c_prev2["high"] < c["low"]: bullish_score += 1        # 41. Bullish Fair Value Gap (FVG)
    if c_prev2["low"] > c["high"]: bearish_score += 1        # 42. Bearish Fair Value Gap (FVG)
    if c["close"] > c_prev["open"] and c["open"] < c_prev["close"]: bullish_score += 1 # 43. Bullish Engulfing
    if c["close"] < c_prev["open"] and c["open"] > c_prev["close"]: bearish_score += 1 # 44. Bearish Engulfing
    if c["low"] < c_prev["low"] and c["close"] > c_prev["high"]: bullish_score += 1    # 45. Outside Key Reversal Up
    if c["high"] > c_prev["high"] and c["close"] < c_prev["low"]: bearish_score += 1   # 46. Outside Key Reversal Down
    if c["close"] > (c_prev["open"] + c_prev["close"])/2 and c_prev["close"] < c_prev["open"]: bullish_score += 1 # 47. Piercing Pattern
    if c["close"] < (c_prev["open"] + c_prev["close"])/2 and c_prev["close"] > c_prev["open"]: bearish_score += 1 # 48. Dark Cloud Cover
    if price > (c_prev["high"] + (tick_size or 0.00001)): bullish_score += 1 # 49. Live Micro Breakout Up
    if price < (c_prev["low"] - (tick_size or 0.00001)): bearish_score += 1  # 50. Live Micro Breakout Down

    # --------------------------------------------------------
    # DECISION THRESHOLD EXECUTION
    # --------------------------------------------------------
    if bullish_score >= SCORE_THRESHOLD:
        return "buy", atr, bullish_score, bearish_score
    elif bearish_score >= SCORE_THRESHOLD:
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
# POSITIONS & DYNAMIC TRAILING SL ENGINE
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
            time.sleep(0.3)
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

        time.sleep(0.3)

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
        "client_order_id": "MULTI50_" + str(int(time.time()))
    }
    return private_request("POST", "/v2/orders", body=body)

def wait_for_fill():
    for _ in range(15):
        pos = get_position()
        if pos and abs(pos["size"]) > 0 and pos["entry_price"] > 0:
            return pos
        time.sleep(0.1)
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
            f"⚡ 50-STRATEGY CONFLUENCE TRADE EXECUTED!\n"
            f"Side: {side.upper()} | Lots: {LOT_SIZE}\n"
            f"Confluence Score: {score}/50 Strategies Match\n"
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
# TELEGRAM COMMAND LISTENERS
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
                            send_telegram("🔴 50-STRATEGY ENGINE PAUSED!")
                        elif text == "/start":
                            bot_active = True
                            send_telegram("🟢 50-STRATEGY ENGINE RESUMED!")
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
                                f"📍 Mode: 50-Strategy Multi-Factor Engine\n"
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
# MAIN EXECUTION LOOP
# ------------------------------------------------------------
print("STARTING 50-STRATEGY MULTI-FACTOR ENGINE...", flush=True)
if not load_product():
    raise SystemExit

while True:
    try:
        price = get_live_ticker_data()
        if price is None:
            time.sleep(0.1)
            continue

        signal, atr_val, bull_score, bear_score = process_tick_and_detect_signal(price)
        
        if bot_active:
            if signal in ("buy", "sell") and time.time() - last_trade_time > COOLDOWN_SECONDS:
                score_used = bull_score if signal == "buy" else bear_score
                execute_trade(signal, price, atr_val, score_used)
        time.sleep(0.1)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"⚠️ Loop Exception Recovered: {e}", flush=True)
        time.sleep(0.5)
