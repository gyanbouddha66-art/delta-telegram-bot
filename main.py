import os
import time
import hmac
import hashlib
import json
import threading
import requests
import pandas as pd
import numpy as np
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# --- Environment Variables ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
DELTA_API_KEY = os.getenv("DELTA_API_KEY", "YOUR_API_KEY")
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "YOUR_API_SECRET")

SYMBOL = "BTCUSD"
TIMEFRAME = "1m"
LOT_SIZE = 5

is_bot_active = True
product_id_cache = None

# --- Delta API Signature Generator ---
def generate_signature(method, path, payload, timestamp):
    signature_data = method + timestamp + path + payload
    return hmac.new(
        DELTA_API_SECRET.encode('utf-8'),
        signature_data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_product_id(symbol):
    global product_id_cache
    if product_id_cache:
        return product_id_cache
    try:
        res = requests.get("https://api.delta.exchange/v2/products").json()
        if 'result' in res:
            for p in res['result']:
                if p['symbol'] == symbol:
                    product_id_cache = p['id']
                    return product_id_cache
    except Exception as e:
        print("Product ID Fetch Error:", e)
    return None

def send_telegram_msg(message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
        except Exception as e:
            print("Telegram Alert Error:", e)

# --- Delta Order Execution Engine ---
def place_delta_order(side, size, sl_price, tp_price):
    prod_id = get_product_id(SYMBOL)
    if not prod_id:
        print("Product ID not found!")
        return

    path = "/v2/orders"
    url = f"https://api.delta.exchange{path}"
    timestamp = str(int(time.time()))
    
    payload_dict = {
        "product_id": prod_id,
        "size": size,
        "side": side,
        "order_type": "market_order",
        "stop_loss_price": str(round(sl_price, 1)),
        "take_profit_price": str(round(tp_price, 1))
    }
    
    payload_str = json.dumps(payload_dict)
    signature = generate_signature("POST", path, payload_str, timestamp)

    headers = {
        "api-key": DELTA_API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, data=payload_str, headers=headers)
        res_data = response.json()
        if response.status_code == 200 and res_data.get('success'):
            msg = f"🚀 *TRADE EXECUTED!*\n\n*Side:* {side.upper()}\n*Lots:* {size}\n*SL:* {sl_price:.1f}\n*TP:* {tp_price:.1f}"
            send_telegram_msg(msg)
            print("Order Success:", res_data)
        else:
            print("Order Failed:", res_data)
    except Exception as e:
        print("Execution Exception:", e)

# --- Telegram Handlers (v13.15 Compatible) ---
def start_command(update: Update, context: CallbackContext):
    global is_bot_active
    is_bot_active = True
    update.message.reply_text("✅ *Trading Bot Started!* 24/7 ऑटो-ट्रेडिंग चालू है।", parse_mode="Markdown")

def stop_command(update: Update, context: CallbackContext):
    global is_bot_active
    is_bot_active = False
    update.message.reply_text("🛑 *Trading Bot Stopped!* ऑटो-ट्रेडिंग रोक दी गई है।", parse_mode="Markdown")

def status_command(update: Update, context: CallbackContext):
    status = "RUNNING 🟢" if is_bot_active else "STOPPED 🔴"
    update.message.reply_text(f"📊 *Bot Status:* {status}", parse_mode="Markdown")

# --- Fast Strategy Loop ---
def fetch_candles(symbol, resolution, limit=250):
    url = f"https://api.delta.exchange/v2/history/candles?resolution={resolution}&symbol={symbol}&limit={limit}"
    try:
        res = requests.get(url).json()
        if 'result' in res:
            df = pd.DataFrame(res['result']).iloc[::-1].reset_index(drop=True)
            for col in ['close', 'high', 'low', 'open']:
                df[col] = df[col].astype(float)
            return df
    except Exception as e:
        print("API Fetch Error:", e)
    return None

def trading_loop():
    global is_bot_active
    last_trade_time = 0
    
    while True:
        if is_bot_active:
            try:
                df = fetch_candles(SYMBOL, TIMEFRAME)
                if df is not None and len(df) >= 200:
                    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
                    
                    high_low = df['high'] - df['low']
                    high_close = np.abs(df['high'] - df['close'].shift())
                    low_close = np.abs(df['low'] - df['close'].shift())
                    df['tr'] = np.maximum(high_low, np.maximum(high_close, low_close))
                    df['atr'] = df['tr'].rolling(14).mean()

                    df['swing_high'] = df['high'].shift(1).rolling(5).max()
                    df['swing_low'] = df['low'].shift(1).rolling(5).min()

                    curr = df.iloc[-1]
                    
                    bullish_sweep = (curr['low'] < curr['swing_low']) and (curr['close'] > curr['swing_low']) and (curr['close'] > curr['ema200'])
                    bearish_sweep = (curr['high'] > curr['swing_high']) and (curr['close'] < curr['swing_high']) and (curr['close'] < curr['ema200'])

                    if time.time() - last_trade_time > 60:
                        if bullish_sweep:
                            sl = curr['low'] - (curr['atr'] * 1.5)
                            tp = curr['close'] + (curr['atr'] * 1.0)
                            place_delta_order("buy", LOT_SIZE, sl, tp)
                            last_trade_time = time.time()

                        elif bearish_sweep:
                            sl = curr['high'] + (curr['atr'] * 1.5)
                            tp = curr['close'] - (curr['atr'] * 1.0)
                            place_delta_order("sell", LOT_SIZE, sl, tp)
                            last_trade_time = time.time()

            except Exception as e:
                print("Strategy Loop Error:", e)
        time.sleep(10)

# --- Main Entry ---
if __name__ == '__main__':
    t = threading.Thread(target=trading_loop, daemon=True)
    t.start()

    updater = Updater(TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("stop", stop_command))
    dispatcher.add_handler(CommandHandler("status", status_command))
    
    print("Bot Controller Ready (v13.15)...")
    updater.start_polling()
    updater.idle()
