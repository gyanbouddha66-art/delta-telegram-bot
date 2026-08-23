import os
import time
import json
import hmac
import hashlib
import requests
import threading
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# ==========================================
# CONFIGURATION FROM ENVIRONMENT VARIABLES
# ==========================================
API_KEY = os.environ.get("API_KEY", "")
API_SECRET = os.environ.get("API_SECRET", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ALLOWED_CHAT_ID = os.environ.get("CHAT_ID", "")

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

# Global State
bot_active = False
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

def send_telegram_msg(bot, text):
    if ALLOWED_CHAT_ID:
        try:
            bot.send_message(chat_id=ALLOWED_CHAT_ID, text=text)
        except Exception as e:
            print(f"Telegram error: {e}")

def public_get(endpoint, params=None):
    try:
        res = session.get(BASE_URL + endpoint, params=params, timeout=5)
        return res.json()
    except Exception as e:
        print(f"Public API Error: {e}")
        return None

def make_signature(method, timestamp, endpoint, query="", payload=""):
    message = method.upper() + str(timestamp) + endpoint + query + payload
    return hmac.new(API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()

def private_request(method, endpoint, params=None, body=None):
    try:
        method = method.upper()
        query = "?" + "&".join([f"{k}={v}" for k, v in params.items()]) if params else ""
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
        print(f"Private API Error: {e}")
        return None

def load_product():
    global product_id, tick_size
    data = public_get("/v2/products/" + SYMBOL)
    if data and data.get("result"):
        result = data["result"]
        product_id = int(result["id"])
        tick_size = float(result.get("tick_size", 0.00001))
        return True
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
    return direction / volatility if volatility > 0 else 0.0

def momentum_signal(price):
    if len(candles) < (MOMENTUM_LOOKBACK + 1):
        return "buy"
    reference = candles[-1 - MOMENTUM_LOOKBACK]["close"]
    if reference <= 0:
        return "buy"
    return "buy" if ((price - reference) / reference) >= 0 else "sell"

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
        return {"size": int(float(res.get("size", 0))), "entry_price": float(res.get("entry_price", 0))}
    except Exception:
        return {"size": 0, "entry_price": 0.0}

def place_market_order(side):
    body = {
        "product_symbol": SYMBOL,
        "size": LOT_SIZE,
        "side": side,
        "order_type": "market_order",
        "client_order_id": "GHV12_" + str(int(time.time()))
    }
    return private_request("POST", "/v2/orders", body=body)

def wait_for_fill():
    for _ in range(10):
        pos = get_position()
        if pos and abs(pos["size"]) > 0 and pos["entry_price"] > 0:
            return pos
        time.sleep(0.3)
    return None

def round_price(price):
    return round(round(price / tick_size) * tick_size, 8) if tick_size else round(price, 8)

def place_bracket(entry_price, side):
    sl = round_price(entry_price * (1 - SL_PCT if side == "buy" else 1 + SL_PCT))
    tp = round_price(entry_price * (1 + TP_PCT if side == "buy" else 1 - TP_PCT))
    body = {
        "product_id": product_id,
        "product_symbol": SYMBOL,
        "stop_loss_order": {"order_type": "market_order", "stop_price": f"{sl:.8f}"},
        "take_profit_order": {"order_type": "market_order", "stop_price": f"{tp:.8f}"},
        "bracket_stop_trigger_method": "last_traded_price"
    }
    return private_request("POST", "/v2/orders/bracket", body=body)

def execute_trade(side, price, er, bot):
    global last_trade_time, order_in_progress
    with order_lock:
        if order_in_progress:
            return
        order_in_progress = True

    try:
        pos = get_position()
        if pos and abs(pos["size"]) > 0:
            return
            
        send_telegram_msg(bot, f"⚡ SIGNAL TRIGGERED\nSide: {side.upper()}\nPrice: {price:.8f}\nER: {er:.4f}")
        res = place_market_order(side)
        if not res or res.get("success") is False:
            send_telegram_msg(bot, "❌ Order Placement Failed!")
            return
        
        pos = wait_for_fill()
        if not pos:
            send_telegram_msg(bot, "🚨 Position verification pending...")
            return
        
        entry = pos["entry_price"]
        bracket = place_bracket(entry, side)
        if not bracket or bracket.get("success") is False:
            send_telegram_msg(bot, "🚨 BRACKET FAILED!")
            return
        
        send_telegram_msg(bot, f"✅ ORDER & BRACKET SUCCESSFUL!\nEntry: {entry}")
        last_trade_time = time.time()
    finally:
        with order_lock:
            order_in_progress = False

def trading_loop(bot):
    global candles, bot_active
    load_product()
    candles = fetch_history()
    last_candle_fetch = time.time()
    
    while bot_active:
        try:
            price = get_live_price()
            if price is None:
                time.sleep(0.3)
                continue
            
            if time.time() - last_candle_fetch > 10 or not candles:
                candles = fetch_history()
                last_candle_fetch = time.time()

            signal, er = get_signal(price)
            if time.time() - last_trade_time > COOLDOWN_SECONDS:
                execute_trade(signal, price, er, bot)
                
            time.sleep(0.3)
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(0.3)

# TELEGRAM COMMAND HANDLERS
def cmd_start(update: Update, context: CallbackContext):
    global bot_active
    if str(update.effective_chat.id) != ALLOWED_CHAT_ID:
        return
    if not bot_active:
        bot_active = True
        threading.Thread(target=trading_loop, args=(context.bot,), daemon=True).start()
        update.message.reply_text("🟢 GH-V12 Trading Engine STARTED!")
    else:
        update.message.reply_text("⚠️ Engine is already running.")

def cmd_stop(update: Update, context: CallbackContext):
    global bot_active
    if str(update.effective_chat.id) != ALLOWED_CHAT_ID:
        return
    bot_active = False
    update.message.reply_text("🔴 GH-V12 Trading Engine STOPPED!")

def cmd_status(update: Update, context: CallbackContext):
    if str(update.effective_chat.id) != ALLOWED_CHAT_ID:
        return
    status_str = "🟢 RUNNING" if bot_active else "🔴 STOPPED"
    price = get_live_price()
    pos = get_position()
    pos_str = f"Size: {pos['size']} | Entry: {pos['entry_price']}" if pos else "No Active Position"
    update.message.reply_text(f"Status: {status_str}\nLive Price: {price}\nPosition: {pos_str}")

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("stop", cmd_stop))
    dp.add_handler(CommandHandler("status", cmd_status))
    
    updater.start_polling()
    print("Telegram Bot Running...")
    updater.idle()

if __name__ == "__main__":
    main()
