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

# --- Trading Configuration for ARCUSD (3x Leverage, 3 Lots) ---
SYMBOL = "ARCUSD"
TIMEFRAME = "1m"
LOT_SIZE = 3         # Total 30 ARC
LEVERAGE = 3         # 3x Leverage

is_bot_active = True
product_id_cache = None

# --- Performance Tracking Variables ---
total_trades = 0
winning_trades = 0
losing_trades = 0

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

def get_wallet_balance():
    """ डेल्टा अकाउंट से लाइव वॉलेट बैलेंस फेच करने के लिए """
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
                if asset['asset_symbol'] == 'USDT' or asset['asset_symbol'] == 'USD':
                    return float(asset.get('balance', 0))
    except Exception as e:
        print("Balance Fetch Error:", e)
    return 0.0

def send_telegram_msg(message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
        except Exception as e:
            print("Telegram Alert Error:", e)

# --- Set Leverage Function ---
def set_leverage(prod_id, leverage):
    path = "/v2/orders/leverage"
    url = f"https://api.delta.exchange{path}"
    timestamp = str(int(time.time()))
    
    payload_dict = {
        "product_id": prod_id,
        "leverage": leverage
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
        requests.post(url, data=payload_str, headers=headers)
    except Exception as e:
        print("Set Leverage Exception:", e)

# --- Delta Order Execution Engine with Balance & Winrate Tracker ---
def place_delta_order(side, size, sl_price, tp_price):
    global total_trades, winning_trades, losing_trades
    
    # ट्रेड लेने से पहले पुराना बैलेंस नोट करें
    old_balance = get_wallet_balance()

    prod_id = get_product_id(SYMBOL)
    if not prod_id:
        print("Product ID not found!")
        return

    set_leverage(prod_id, LEVERAGE)

    path = "/v2/orders"
    url = f"https://api.delta.exchange{path}"
    timestamp = str(int(time.time()))
    
    payload_dict = {
        "product_id": prod_id,
        "size": size,
        "side": side,
        "order_type": "market_order",
        "stop_loss_price": str(round(sl_price, 4)),
        "take_profit_price": str(round(tp_price, 4))
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
            msg = (f"🚀 *ARCUSD TRADE EXECUTED (3x | 3 Lots)*\n\n"
                   f"*Side:* {side.upper()}\n"
                   f"*Old Balance:* ${old_balance:.2f}\n"
                   f"*SL:* {sl_price:.4f} | *TP:* {tp_price:.4f}\n\n"
                   f"⏳ *Target / Stoploss का इंतज़ार है...*")
            send_telegram_msg(msg)
            
            # बैकग्राउंड में ट्रेड क्लोज होने और नए बैलेंस/विनरेट को ट्रैक करने का थ्रेड
            threading.Thread(target=track_trade_result, args=(old_balance,)).start()
        else:
            print("Order Failed:", res_data)
    except Exception as e:
        print("Execution Exception:", e)

def track_trade_result(old_balance):
    global total_trades, winning_trades, losing_trades
    # ट्रेड पूरी होने (TP या SL हिट होने) का अनुमानित इंतज़ार लूप
    for _ in range(120): # 20 मिनट तक चेक करेगा
        time.sleep(10)
        new_balance = get_wallet_balance()
        if new_balance != old_balance and new_balance > 0:
            diff = new_balance - old_balance
            if diff > 0:
                winning_trades += 1
                status_text = "🟢 *TP HIT (PROFIT)* 🎉"
            else:
                losing_trades += 1
                status_text = "🔴 *SL HIT (LOSS)* ⚠️"
            
            winrate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            result_msg = (f"{status_text}\n\n"
                          f"*Old Balance:* ${old_balance:.2f}\n"
                          f"*New Balance:* ${new_balance:.2f}\n"
                          f"*P&L:* ${diff:+.2f}\n\n"
                          f"📊 *Winrate Stats:*\n"
                          f"• Total Trades: {total_trades}\n"
                          f"• Wins: {winning_trades} | Losses: {losing_trades}\n"
                          f"• Winrate: {winrate:.1f}%")
            send_telegram_msg(result_msg)
            break

# --- Telegram Handlers (v13.15 Compatible) ---
def start_command(update: Update, context: CallbackContext):
    global is_bot_active
    is_bot_active = True
    update.message.reply_text("✅ *ARCUSD Tracker Bot Started!* बैलेंस और विनरेट ट्रैकिंग चालू है।", parse_mode="Markdown")

def stop_command(update: Update, context: CallbackContext):
    global is_bot_active
    is_bot_active = False
    update.message.reply_text("🛑 *Bot Stopped!*", parse_mode="Markdown")

def status_command(update: Update, context: CallbackContext):
    winrate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    status = "RUNNING 🟢" if is_bot_active else "STOPPED 🔴"
    text = (f"📊 *Bot Status:* {status}\n"
            f"• Total Trades: {total_trades}\n"
            f"• Winrate: {winrate:.1f}%")
    update.message.reply_text(text, parse_mode="Markdown")

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
    
    print("Balance & Winrate Tracker Bot Ready...")
    updater.start_polling()
    updater.idle()
