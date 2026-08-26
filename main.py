import os
import time
import hmac
import hashlib
import json
import threading
import requests
import pandas as pd
import numpy as np
from flask import Flask
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# --- Flask Server for Render Port Binding ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Instant ARCUSD Bot is Live!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- Environment Variables ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
DELTA_API_KEY = os.getenv("DELTA_API_KEY", "YOUR_API_KEY")
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "YOUR_SECRET_KEY")

# --- Trading Config ---
SYMBOL = "ARCUSD"
TIMEFRAME = "1m"
LOT_SIZE = 1         
LEVERAGE = 3         

is_bot_active = True
product_id_cache = None
total_trades = 0
winning_trades = 0
losing_trades = 0

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
        print("Product ID Error:", e)
    return None

def get_wallet_balance():
    path = "/v2/wallet/balances"
    url = f"https://api.delta.exchange{path}"
    timestamp = str(int(time.time()))
    signature = generate_signature("GET", path, "", timestamp)

    headers = {
        "api-key": DELTA_API_KEY,
        "timestamp": timestamp,
        "signature": signature
    }

    try:
        response = requests.get(url, headers=headers)
        res_data = response.json()
        if response.status_code == 200 and res_data.get('success'):
            for asset in res_data.get('result', []):
                bal = float(asset.get('balance', 0))
                if bal > 0:
                    return bal
    except Exception as e:
        print("Balance Error:", e)
    return 0.0

def send_telegram_msg(message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
        except Exception as e:
            print("Telegram Error:", e)

def set_leverage(prod_id, leverage):
    path = "/v2/orders/leverage"
    url = f"https://api.delta.exchange{path}"
    timestamp = str(int(time.time()))
    payload_str = json.dumps({"product_id": prod_id, "leverage": leverage})
    signature = generate_signature("POST", path, payload_str, timestamp)

    headers = {
        "api-key": DELTA_API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "Content-Type": "application/json"
    }
    try:
        requests.post(url, data=payload_str, headers=headers)
    except Exception as e:
        print("Leverage Error:", e)

def place_instant_order(side, size, current_price):
    global total_trades
    old_balance = get_wallet_balance()
    prod_id = get_product_id(SYMBOL)
    if not prod_id:
        return

    set_leverage(prod_id, LEVERAGE)

    # इंस्टेंट और फास्ट टारगेट्स (0.5% SL और 1% TP)
    sl = current_price * (0.995 if side == "buy" else 1.005)
    tp = current_price * (1.010 if side == "buy" else 0.990)

    path = "/v2/orders"
    url = f"https://api.delta.exchange{path}"
    timestamp = str(int(time.time()))
    
    payload_dict = {
        "product_id": prod_id,
        "size": size,
        "side": side,
        "order_type": "market_order",
        "stop_loss_price": str(round(sl, 4)),
        "take_profit_price": str(round(tp, 4))
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
            total_trades += 1
            msg = f"⚡ *INSTANT TRADE EXECUTED*\n*Side:* {side.upper()}\n*Price:* {current_price}"
            send_telegram_msg(msg)
        else:
            send_telegram_msg(f"⚠️ *Trade Error:* {res_data}")
    except Exception as e:
        print("Order Exception:", e)

# --- Telegram Commands ---
def start_command(update: Update, context: CallbackContext):
    global is_bot_active
    is_bot_active = True
    update.message.reply_text("✅ *Instant Bot Started!*", parse_mode="Markdown")

def stop_command(update: Update, context: CallbackContext):
    global is_bot_active
    is_bot_active = False
    update.message.reply_text("🛑 *Bot Stopped!*", parse_mode="Markdown")

def status_command(update: Update, context: CallbackContext):
    current_balance = get_wallet_balance()
    status = "RUNNING 🟢" if is_bot_active else "STOPPED 🔴"
    text = f"📊 *Status:* {status}\n💰 *Balance:* ${current_balance:.4f}\n• Trades: {total_trades}"
    update.message.reply_text(text, parse_mode="Markdown")

def fast_trading_loop():
    global is_bot_active
    while True:
        if is_bot_active:
            try:
                url = f"https://api.delta.exchange/v2/history/candles?resolution=1m&symbol={SYMBOL}&limit=5"
                res = requests.get(url).json()
                if 'result' in res and len(res['result']) > 0:
                    latest = res['result'][0]
                    close_price = float(latest['close'])
                    open_price = float(latest['open'])
                    
                    # जैसे ही मार्केट में जरा भी ग्रीन कैंडल बने, तुरंत बाय ठोक देगा (इन्स्टेंट)
                    if close_price > open_price:
                        place_instant_order("buy", LOT_SIZE, close_price)
                        time.sleep(30) # बार-बार लगातार ट्रेड रोकने के लिए गैप
            except Exception as e:
                print("Loop Error:", e)
        time.sleep(10)

if __name__ == '__main__':
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=fast_trading_loop, daemon=True).start()

    updater = Updater(TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("stop", stop_command))
    dispatcher.add_handler(CommandHandler("status", status_command))
    
    updater.start_polling()
    updater.idle()
