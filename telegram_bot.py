# ============================================================
# TELEGRAM BOT INTERFACE (`telegram_bot.py`)
# ============================================================

import os
import requests
from config import SYMBOL, DEFAULT_SIZE, PRODUCT_ID
from delta_api import place_order, test_delta, get_delta_balances
from trading_engine import get_signal, get_engine_status, toggle_engine_mode
from groq_ai import ask_groq_ai

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
        msg = (
            "🧠 **GH BOSS AI — SMART TRADING SYSTEM**\n\n"
            f"⚙️ Current Asset: `{SYMBOL}`\n"
            "✅ Telegram Connected\n"
            "✅ Groq AI Loaded\n"
            "✅ Trading Buttons Active\n\n"
            "आप नीचे दिए गए बटन्स का उपयोग कर सकते हैं या सीधे चैट में कोई भी सवाल पूछ सकते हैं!"
        )
        send_message(chat_id, msg, get_keyboard())
    elif text == "/signal":
        report = get_signal()
        send_message(chat_id, report, get_keyboard())
    elif text == "/status":
        send_message(chat_id, "📊 **GH BOSS STATUS**\nEngine: ONLINE\nGroq AI: CONNECTED 🟢\nDelta: CONNECTED 🟢", get_keyboard())
    elif text == "/balance":
        bal_res = get_delta_balances()
        if bal_res.get("success"):
            send_message(chat_id, f"💰 **Delta Balances:**\n`{bal_res.get('balances')}`", get_keyboard())
        else:
            send_message(chat_id, f"❌ Balance Error: {bal_res.get('error')}", get_keyboard())
    else:
        ai_response = ask_groq_ai(text)
        send_message(chat_id, f"🧠 **GH BOSS AI:**\n\n{ai_response}", get_keyboard())

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
    send_message(chat_id, "🎤 वॉइस नोट मिला। AI इसे प्रोसेस कर रहा है...", get_keyboard())
    ai_response = ask_groq_ai("User sent a voice note regarding crypto trading.")
    send_message(chat_id, f"🧠 **GH BOSS AI:**\n\n{ai_response}", get_keyboard())
