# ============================================================
# GH V12 ENGINE - VWAP + PRICE ACTION + CANDLESTICK PATTERNS
# DELTA EXCHANGE INDIA V2 | ARCUSD
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
LOT_SIZE = 5                      # 5 लॉट सेट हैं

SL_PCT = 0.004                    # 0.4% Stop Loss
TP_PCT = SL_PCT * (0.70 / 0.30)   # 0.93% Take Profit
COOLDOWN_SECONDS = 10

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

# Win/Loss & PnL Trackers
wins_count = 0
losses_count = 0
initial_wallet_balance = 0.0
last_valid_balance = 0.0

# VWAP & Candle Buffers
price_history = []      # Memory for tick candles
volume_history = []
cum_volume = 0.0
cum_pv = 0.0
vwap_price = None

recent_swing_high = None
recent_swing_low = None

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=3, pool_connections=10, pool_maxsize=10)
session.mount("https://", adapter)
session.headers.update({"User-Agent": "GH-V12-LiveSMC/10.0", "Accept": "application/json"})

# ------------------------------------------------------------
# DUMMY FLASK SERVER FOR RENDER FREE TIER
# ------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "SMC VWAP Engine is Live and Running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ------------------------------------------------------------
# HELPER FUNCTIONS
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
                msg = f"✅ VWAP & CANDLESTICK ENGINE ONLINE!\nSymbol: {SYMBOL}\nLots: {LOT_SIZE}\nInitial Balance: ${initial_wallet_balance:.2f}"
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
        vol = float(res.get("volume", 1.0))
        return price, vol
    return None, 1.0

# ------------------------------------------------------------
# VWAP & CANDLESTICK STRATEGY LOGIC
# ------------------------------------------------------------
def update_vwap_and_candles(price, volume):
    global cum_volume, cum_pv, vwap_price, recent_swing_high, recent_swing_low
    
    # VWAP Calculation
    cum_volume += volume
    cum_pv += price * volume
    if cum_volume > 0:
        vwap_price = cum_pv / cum_volume
    else:
        vwap_price = price

    # Update Ticks for Candlesticks
    price_history.append(price)
    if len(price_history) > 30:
        price_history.pop(0)

    # Dynamic Swings
    if recent_swing_high is None or recent_swing_low is None:
        recent_swing_high = price * 1.0008
        recent_swing_low = price * 0.9992
    else:
        recent_swing_high = max(recent_swing_high, price)
        recent_swing_low = min(recent_swing_low, price)

def check_candlestick_pattern():
    if len(price_history) < 5:
        return "none"

    p_curr = price_history[-1]
    p_prev = price_history[-2]
    p_prev2 = price_history[-3]
    p_open = price_history[-4]

    # Bullish Engulfing / Hammer Simulation
    is_bullish_candle = p_curr > p_prev and p_prev <= p_prev2
    is_bearish_candle = p_curr < p_prev and p_prev >= p_prev2

    if is_bullish_candle:
        return "bullish"
    elif is_bearish_candle:
        return "bearish"

    return "none"

def get_vwap_pa_signal(price):
    global recent_swing_high, recent_swing_low, vwap_price
    
    if vwap_price is None or recent_swing_high is None or recent_swing_low is None:
        return "none"

    candle_pattern = check_candlestick_pattern()

    # BUY SIGNAL: Price > VWAP + Bullish Pattern + Break Above Swing
    if price > vwap_price and candle_pattern == "bullish" and price >= recent_swing_high:
        recent_swing_high = price * 1.0015
        return "buy"

    # SELL SIGNAL: Price < VWAP + Bearish Pattern + Break Below Swing
    elif price < vwap_price and candle_pattern == "bearish" and price <= recent_swing_low:
        recent_swing_low = price * 0.9985
        return "sell"

    return "none"

# ------------------------------------------------------------
# ORDER EXECUTION & MONITORING
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

def place_market_order(side):
    body = {
        "product_symbol": SYMBOL, 
        "size": LOT_SIZE, 
        "side": side, 
        "order_type": "market_order", 
        "client_order_id": "GH_VWAP_" + str(int(time.time()))
    }
    return private_request("POST", "/v2/orders", body=body)

def wait_for_fill():
    for _ in range(20):
        pos = get_position()
        if pos and abs(pos["size"]) > 0 and pos["entry_price"] > 0:
            return pos
        time.sleep(0.3)
    return None

def round_price(price):
    try:
        if tick_size and tick_size > 0:
            decimals = max(0, -int(math.floor(math.log10(tick_size))))
            steps = round(price / tick_size)
            return round(steps * tick_size, decimals)
    except Exception:
        pass
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

def monitor_trade_outcome(entry_price, side, prev_bal):
    global wins_count, losses_count
    try:
        zero_count = 0
        while zero_count < 3:
            if not has_position():
                zero_count += 1
            else:
                zero_count = 0
            time.sleep(1)
        
        current_bal = prev_bal
        for _ in range(5):
            time.sleep(1)
            fetched_bal = get_wallet_balance()
            if abs(fetched_bal - prev_bal) > 0.0001:
                current_bal = fetched_bal
                break
                
        pnl = current_bal - prev_bal
        
        with stats_lock:
            if pnl > 0:
                wins_count += 1
                status_text = "🎉 TAKE PROFIT (WIN) HIT!"
            elif pnl < 0:
                losses_count += 1
                status_text = "💥 STOP LOSS (LOSS) HIT!"
            else:
                status_text = "⚖️ BREAK-EVEN / NO CHANGE"
                
            total_trades = wins_count + losses_count
            win_rate = (wins_count / total_trades * 100) if total_trades > 0 else 0.0
            w_cnt, l_cnt, w_rt = wins_count, losses_count, win_rate

        report = (
            f"{status_text}\n"
            f"-----------------------------\n"
            f"📊 Side: {side.upper()} | Lots: {LOT_SIZE}\n"
            f"💰 Trade PnL: ${pnl:+.2f}\n"
            f"🏆 Wins: {w_cnt} | ❌ Losses: {l_cnt}\n"
            f"📈 Win Rate: {w_rt:.1f}%\n"
            f"-----------------------------\n"
            f"💵 Prev Balance: ${prev_bal:.2f}\n"
            f"💳 Current Balance: ${current_bal:.2f}\n"
            f"🏠 Start Balance: ${initial_wallet_balance:.2f}"
        )
        send_telegram(report)
    except Exception as e:
        print(f"⚠️ Outcome Monitor Error: {e}", flush=True)

def execute_trade(side, price):
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
        bracket = place_bracket(entry, side)
        if not bracket or bracket.get("success") is False:
            send_telegram(f"🚨 BRACKET FAILED! Response: {bracket}")
            return
        
        if side == "buy":
            sl_val = round_price(entry * (1 - SL_PCT))
            tp_val = round_price(entry * (1 + TP_PCT))
        else:
            sl_val = round_price(entry * (1 + SL_PCT))
            tp_val = round_price(entry * (1 - TP_PCT))

        success_msg = (
            f"⚡ VWAP + PA TRADE EXECUTED!\n"
            f"Side: {side.upper()} | Lots: {LOT_SIZE}\n"
            f"Entry: {entry:.8f}\n"
            f"VWAP Level: {vwap_price:.8f}\n"
            f"SL: {sl_val:.8f} | TP: {tp_val:.8f}\n"
            f"Wallet Balance: ${prev_bal:.2f}\n"
            f"⏳ Monitoring Position..."
        )
        send_telegram(success_msg)
        
        threading.Thread(target=monitor_trade_outcome, args=(entry, side, prev_bal), daemon=True).start()
        last_trade_time = time.time()
    except Exception as e:
        send_telegram(f"⚠️ Execution Exception: {e}")
    finally:
        with order_lock:
            order_in_progress = False

# ------------------------------------------------------------
# TELEGRAM LISTENER
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
                            send_telegram("🔴 ENGINE PAUSED!")
                        elif text == "/start":
                            bot_active = True
                            send_telegram("🟢 ENGINE RESUMED!")
                        elif text == "/reset":
                            with order_lock:
                                order_in_progress = False
                            send_telegram("🔄 ENGINE UNLOCKED & RESET SUCCESSFUL!")
                        elif text == "/status":
                            st = "🟢 RUNNING" if bot_active else "🔴 PAUSED"
                            cur_bal = get_wallet_balance()
                            pos_status = "In Position" if has_position() else "No Active Position"
                            vwap_str = f"{vwap_price:.8f}" if vwap_price else "Calculating..."
                            with stats_lock:
                                w_cnt, l_cnt = wins_count, losses_count
                            total_trades = w_cnt + l_cnt
                            wr = (w_cnt / total_trades * 100) if total_trades > 0 else 0.0
                            
                            report = (
                                f"🤖 BOT STATUS: {st}\n"
                                f"📍 Position: {pos_status}\n"
                                f"📊 Live VWAP: {vwap_str}\n"
                                f"-----------------------------\n"
                                f"🏆 Wins: {w_cnt} | ❌ Losses: {l_cnt}\n"
                                f"📈 Win Rate: {wr:.1f}%\n"
                                f"-----------------------------\n"
                                f"💵 Current Balance: ${cur_bal:.2f}\n"
                                f"🏠 Initial Balance: ${initial_wallet_balance:.2f}\n"
                                f"📊 Net PnL: ${(cur_bal - initial_wallet_balance):+.2f}"
                            )
                            send_telegram(report)
        except Exception:
            pass
        time.sleep(1)

threading.Thread(target=telegram_command_listener, daemon=True).start()

# ------------------------------------------------------------
# MAIN AUTO-RECOVERY TICK LOOP
# ------------------------------------------------------------
print("STARTING VWAP + PA + CANDLESTICK ENGINE...", flush=True)
if not load_product():
    raise SystemExit

while True:
    try:
        price, vol = get_live_ticker_data()
        if price is None:
            time.sleep(0.3)
            continue

        update_vwap_and_candles(price, vol)
        signal = get_vwap_pa_signal(price)
        
        if bot_active:
            if signal in ("buy", "sell") and time.time() - last_trade_time > COOLDOWN_SECONDS:
                execute_trade(signal, price)
        time.sleep(0.3)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"⚠️ Loop Exception Recovered: {e}", flush=True)
        time.sleep(1)
