# ============================================================
# GH BOSS AI — TELEGRAM BOT
# ============================================================

import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from trading_engine import get_engine_status, get_signal
from groq_ai import ask_groq
from delta_api import test_delta, get_delta_balances, place_order
from voice_utils import (
    send_message,
    send_voice,
    process_voice as voice_utils_process_voice,
    voice_status
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TRADING_MODE = os.getenv("TRADING_MODE", "MANUAL").upper()


def get_trading_keyboard():
    mode_text = f"⚙️ Mode: {TRADING_MODE}"
    keyboard = [
        [
            InlineKeyboardButton("🟢 BUY (LONG)", callback_data="btn_buy"),
            InlineKeyboardButton("🔴 SELL (SHORT)", callback_data="btn_sell")
        ],
        [
            InlineKeyboardButton(mode_text, callback_data="btn_toggle_mode"),
            InlineKeyboardButton("📊 Refresh Signal", callback_data="btn_signal")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def handle_ai_text_query(user_text):
    prompt = f"""
You are GH BOSS AI, an expert crypto and trading assistant specialized in SMC, Price Action, and Scalping (especially for ARCUSD, BTC, ETH).

User message:
{user_text}

Provide concise, accurate, and professional trading analysis in Hindi.
"""
    answer = ask_groq(prompt)
    return str(answer).strip()


def ai_chat(chat_id, user_text, voice_reply=True):
    send_message(chat_id, "🧠 GH BOSS AI analyzing...")
    try:
        answer = handle_ai_text_query(user_text)
        send_message_with_keyboard(chat_id, "🧠 GH BOSS AI\n\n" + answer)

        if voice_reply:
            from voice_utils import text_to_voice
            audio_file = text_to_voice(answer)
            if audio_file:
                try:
                    send_voice(chat_id, audio_file)
                finally:
                    try:
                        os.remove(audio_file)
                    except Exception:
                        pass
    except Exception as e:
        send_message(chat_id, "❌ GROQ AI ERROR\n\n" + str(e))


def send_message_with_keyboard(chat_id, text):
    if not TOKEN:
        return False
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": str(text),
            "reply_markup": get_trading_keyboard().to_dict()
        }
        res = requests.post(url, json=payload, timeout=20)
        return res.ok
    except Exception as e:
        return send_message(chat_id, text)


def command_start(chat_id):
    msg = (
        "🧠 GH BOSS AI — SMART TRADING SYSTEM\n\n"
        f"⚙️ Current Mode: {TRADING_MODE}\n"
        "✅ Telegram, Groq AI & Delta API Connected\n"
        "🎤 Voice & Buttons Enabled"
    )
    send_message_with_keyboard(chat_id, msg)


def command_status(chat_id):
    try:
        status = get_engine_status()
        delta = test_delta()
        msg = (
            "📊 GH BOSS STATUS\n\n"
            f"Mode: {TRADING_MODE}\n"
            f"Signal: {status.get('signal', 'NO SIGNAL')}\n"
            f"Confidence: {status.get('confidence', 0)}%\n\n"
            f"Delta: {'CONNECTED 🟢' if delta.get('success') else 'ERROR 🔴'}"
        )
        send_message_with_keyboard(chat_id, msg)
    except Exception as e:
        send_message(chat_id, "❌ STATUS ERROR\n\n" + str(e))


def command_delta(chat_id):
    send_message(chat_id, "🔄 Testing Delta API...")
    res = test_delta()
    if res.get("success"):
        send_message_with_keyboard(chat_id, "🟢 DELTA API OK")
    else:
        send_message(chat_id, "🔴 DELTA API ERROR: " + str(res.get("error")))


def command_balance(chat_id):
    send_message(chat_id, "💰 Checking Delta balance...")
    res = get_delta_balances()
    if res.get("success"):
        send_message_with_keyboard(chat_id, "💰 BALANCES:\n\n" + str(res.get("balances")))
    else:
        send_message(chat_id, "❌ BALANCE ERROR: " + str(res.get("error")))


def command_signal(chat_id):
    try:
        signal = get_signal()
        direction = signal.get("signal", "NO SIGNAL")
        confidence = signal.get("confidence", 0)
        reason = signal.get("reason", "No reason")
        symbol = signal.get('symbol', 'ARCUSD')

        msg = (
            f"📈 GH MARKET SIGNAL ({symbol})\n\n"
            f"Signal: {direction}\n"
            f"Confidence: {confidence}%\n\n"
            f"Analysis:\n{reason}\n\n"
            f"Mode: {TRADING_MODE}"
        )
        send_message_with_keyboard(chat_id, msg)

        if TRADING_MODE == "AUTO" and direction in ["BUY", "SELL"]:
            place_order(symbol=symbol, side=direction.lower())
            send_message(chat_id, f"🚀 AUTO TRADE EXECUTED: {direction} on {symbol}")
    except Exception as e:
        send_message(chat_id, "❌ SIGNAL ERROR: " + str(e))


def handle_callback_query(chat_id, data):
    global TRADING_MODE
    if data == "btn_buy":
        if TRADING_MODE == "AUTO":
            place_order(symbol="ARCUSD", side="buy")
            send_message(chat_id, "🟢 AUTO: BUY Order Placed on ARCUSD ✅")
        else:
            send_message(chat_id, "🟢 MANUAL: BUY Confirmed! Check Delta terminal.")
    elif data == "btn_sell":
        if TRADING_MODE == "AUTO":
            place_order(symbol="ARCUSD", side="sell")
            send_message(chat_id, "🔴 AUTO: SELL Order Placed on ARCUSD ✅")
        else:
            send_message(chat_id, "🔴 MANUAL: SELL Confirmed! Check Delta terminal.")
    elif data == "btn_toggle_mode":
        TRADING_MODE = "AUTO" if TRADING_MODE == "MANUAL" else "MANUAL"
        send_message_with_keyboard(chat_id, f"⚙️ Mode switched to: {TRADING_MODE}")
    elif data == "btn_signal":
        command_signal(chat_id)


def process_command(chat_id, command):
    if not command:
        return
    cmd = str(command).strip().lower().split("@")[0]

    if cmd == "/start":
        command_start(chat_id)
    elif cmd == "/status":
        command_status(chat_id)
    elif cmd == "/delta":
        command_delta(chat_id)
    elif cmd == "/balance":
        command_balance(chat_id)
    elif cmd == "/signal":
        command_signal(chat_id)
    elif cmd == "/ai":
        ai_chat(chat_id, "नमस्ते GH BOSS AI", voice_reply=True)
    else:
        ai_chat(chat_id, command, voice_reply=True)


def process_voice(chat_id, file_id):
    voice_utils_process_voice(chat_id, file_id, handle_ai_text_query)
