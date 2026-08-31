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

# ============================================================
# GH BOSS AI — TELEGRAM BOT (DUAL MODE + INTERACTIVE BUTTONS)
# ============================================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# ट्रेडिंग मोड: "MANUAL" या "AUTO"
TRADING_MODE = os.getenv("TRADING_MODE", "MANUAL").upper()


# ============================================================
# KEYBOARD BUTTONS HELPER
# ============================================================

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


# ============================================================
# AI CHAT WRAPPER
# ============================================================

def handle_ai_text_query(user_text):
    prompt = f"""
You are GH BOSS AI, an expert crypto and trading assistant specialized in SMC, Price Action, and Scalping (especially for ARCUSD, BTC, ETH).

User message:
{user_text}

Provide concise, accurate, and professional trading analysis in Hindi.
Never invent live market data. If live data is missing, state it clearly.
"""
    answer = ask_groq(prompt)
    return str(answer).strip()


def ai_chat(chat_id, user_text, voice_reply=True):
    print("🧠 GH BOSS AI:", user_text)
    send_message(chat_id, "🧠 GH BOSS AI analyzing...")

    try:
        answer = handle_ai_text_query(user_text)
        if not answer:
            answer = "AI ने कोई response नहीं दिया।"

        # Send Text with Keyboard
        send_message_with_keyboard(chat_id, "🧠 GH BOSS AI\n\n" + answer)

        # Voice Reply
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
        print("❌ GROQ CHAT ERROR:", e)
        send_message(chat_id, "❌ GROQ AI ERROR\n\n" + str(e))


def send_message_with_keyboard(chat_id, text):
    """संदेश को बटंस के साथ भेजने का फंक्शन"""
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
        print("❌ Send keyboard error:", e)
        return send_message(chat_id, text)


# ============================================================
# COMMANDS
# ============================================================

def command_start(chat_id):
    msg = (
        "🧠 GH BOSS AI — SMART TRADING SYSTEM\n\n"
        f"⚙️ Current Execution Mode: {TRADING_MODE}\n"
        "✅ Telegram & Groq AI Connected\n"
        "✅ Delta API Module Loaded\n"
        "🎤 Voice Input & 🔊 Voice Reply Enabled\n\n"
        "बटन्स का उपयोग करके तुरंत ट्रेड या सिग्नल कंट्रोल करें!"
    )
    send_message_with_keyboard(chat_id, msg)


def command_status(chat_id):
    try:
        status = get_engine_status()
        delta = test_delta()
        msg = (
            "📊 GH BOSS STATUS\n\n"
            f"Engine: {status.get('engine', 'UNKNOWN')}\n"
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
    try:
        result = test_delta()
        if result.get("success"):
            send_message_with_keyboard(chat_id, "🟢 DELTA API OK\nAuthentication & Connection successful.")
        else:
            send_message(chat_id, "🔴 DELTA API ERROR\n" + str(result.get("error", "Unknown")))
    except Exception as e:
        send_message(chat_id, "❌ DELTA ERROR\n" + str(e))


def command_balance(chat_id):
    send_message(chat_id, "💰 Checking Delta balance...")
    try:
        result = get_delta_balances()
        if not result.get("success"):
            send_message(chat_id, "❌ BALANCE ERROR\n" + str(result.get("error", "Unknown")))
            return
        send_message_with_keyboard(chat_id, "💰 DELTA ACCOUNT BALANCES:\n\n" + str(result))
    except Exception as e:
        send_message(chat_id, "❌ BALANCE ERROR\n" + str(e))


def command_signal(chat_id):
    try:
        signal = get_signal()
        direction = signal.get("signal", "NO SIGNAL")
        confidence = signal.get("confidence", 0)
        reason = signal.get("reason", "No reason available")
        entry = signal.get("entry")
        sl = signal.get("sl")
        tp = signal.get("tp")
        symbol = signal.get('symbol', 'ARCUSD')

        message = (
            f"📈 GH MARKET SIGNAL ({symbol})\n\n"
            f"Signal: {direction}\n"
            f"Confidence: {confidence}%\n\n"
            f"Analysis:\n{reason}\n"
        )
        if entry is not None:
            message += f"\nEntry: {entry}\n"
        if sl is not None:
            message += f"Stop Loss: {sl}\n"
        if tp is not None:
            message += f"Take Profit: {tp}\n"

        message += f"\nExecution Mode: {TRADING_MODE}"
        send_message_with_keyboard(chat_id, message)

        # यदि ऑटो मोड ऑन है और सिग्नल स्ट्रॉन्ग है, तो आर्डर खुद ले लें
        if TRADING_MODE == "AUTO" and direction in ["BUY", "SELL"]:
            send_message(chat_id, f"🚀 AUTO MODE ACTIVE: Executing {direction} for {symbol}...")
            # order_res = place_order(...)

    except Exception as e:
        send_message(chat_id, "❌ SIGNAL ERROR\n" + str(e))


# ============================================================
# BUTTON CALLBACK HANDLER (INLINE BUTTONS CLICK)
# ============================================================

def handle_callback_query(chat_id, data, message_id):
    global TRADING_MODE
    if data == "btn_buy":
        if TRADING_MODE == "AUTO":
            send_message(chat_id, "🟢 AUTO MODE: Placing BUY Order on ARCUSD...")
            # place_order logic here
        else:
            send_message(chat_id, "🟢 MANUAL MODE: BUY signal confirmed! Check Delta terminal to execute.")
            
    elif data == "btn_sell":
        if TRADING_MODE == "AUTO":
            send_message(chat_id, "🔴 AUTO MODE: Placing SELL Order on ARCUSD...")
            # place_order logic here
        else:
            send_message(chat_id, "🔴 MANUAL MODE: SELL signal confirmed! Check Delta terminal to execute.")
            
    elif data == "btn_toggle_mode":
        TRADING_MODE = "AUTO" if TRADING_MODE == "MANUAL" else "MANUAL"
        send_message_with_keyboard(chat_id, f"⚙️ Trading Mode switched to: **{TRADING_MODE}**")
        
    elif data == "btn_signal":
        command_signal(chat_id)


# ============================================================
# MAIN ROUTER
# ============================================================

def process_command(chat_id, command):
    if not command:
        return
    command_lower = str(command).strip().lower()

    if command_lower.startswith("/") and "@" in command_lower:
        command_lower = command_lower.split("@")[0]

    try:
        if command_lower == "/start":
            command_start(chat_id)
        elif command_lower == "/status":
            command_status(chat_id)
        elif command_lower == "/delta":
            command_delta(chat_id)
        elif command_lower == "/balance":
            command_balance(chat_id)
        elif command_lower == "/signal":
            command_signal(chat_id)
        elif command_lower == "/ai":
            ai_chat(chat_id, "नमस्ते GH BOSS AI, ट्रेडिंग चर्चा शुरू करो।", voice_reply=True)
        else:
            ai_chat(chat_id, command, voice_reply=True)
    except Exception as e:
        print("❌ ROUTER ERROR:", e)
        send_message(chat_id, "❌ SYSTEM ERROR\n\n" + str(e))


def process_voice(chat_id, file_id):
    voice_utils_process_voice(chat_id, file_id, handle_ai_text_query)
