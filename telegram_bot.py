# ============================================================
# TELEGRAM BOT INTERFACE (`telegram_bot.py`)
# ============================================================

import os
import requests
from config import SYMBOL, DEFAULT_SIZE, PRODUCT_ID
from delta_api import place_order, test_delta, get_delta_balances
from trading_engine import get_signal, get_engine_status, toggle_engine_mode

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

def send_message(chat_id, text, reply_markup=None):
    if not chat_id:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram send error:", e)

def get_keyboard():
    auto_on = get_engine_status()
    mode_text = "⚙️ Mode: AUTO" if auto_on else "⚙️ Mode: MANUAL"
    return {
        "inline_keyboard": [
            [{"text": "🟢 BUY (LONG)", "callback_data": "btn_buy"}, {"text": "🔴 SELL (SHORT)", "callback_data": "btn_sell"}],
            [{"text": mode_text, "callback_data": "btn_toggle_mode"}, {"text": "📊 Refresh Signal", "callback_data": "btn_signal"}]
        ]
    }

def process_command(text, chat_id):
    if text == "/start":
        test_res = test_delta()
        status_msg = test_res.get("message", "Connected")
        msg = f"🧠 **GH BOSS AI — SMART TRADING SYSTEM**\n\n⚙️ Current Asset: `{SYMBOL}`\n✅ {status_msg}\n🎤 Voice & Buttons Enabled"
        send_message(chat_id, msg, get_keyboard())
    elif text == "/signal":
        report = get_signal()
        send_message(chat_id, report, get_keyboard())

def handle_callback_query(callback_data, chat_id):
    if callback_data == "btn_signal":
        report = get_signal()
        send_message(chat_id, report, get_keyboard())
    elif callback_data == "btn_toggle_mode":
        new_status = toggle_engine_mode()
        status_str = "AUTO" if new_status else "MANUAL"
        send_message(chat_id, f"⚙️ Mode switched to: {status_str}", get_keyboard())
    elif callback_data == "btn_buy":
        result = place_order(product_id=PRODUCT_ID, symbol=SYMBOL, side="buy", size=DEFAULT_SIZE)
        if result.get("success"):
            send_message(chat_id, f"🟢 **BUY ORDER EXECUTED!**\nAsset: `{SYMBOL}`\nSize: `{DEFAULT_SIZE}`", get_keyboard())
        else:
            send_message(chat_id, f"❌ **Order Failed:** {result.get('error')}", get_keyboard())
    elif callback_data == "btn_sell":
        result = place_order(product_id=PRODUCT_ID, symbol=SYMBOL, side="sell", size=DEFAULT_SIZE)
        if result.get("success"):
            send_message(chat_id, f"🔴 **SELL ORDER EXECUTED!**\nAsset: `{SYMBOL}`\nSize: `{DEFAULT_SIZE}`", get_keyboard())
        else:
            send_message(chat_id, f"❌ **Order Failed:** {result.get('error')}", get_keyboard())

def process_voice(file_id, chat_id):
    send_message(chat_id, "🎤 वॉइस कमांड प्रोसेस की जा रही है...", get_keyboard())
