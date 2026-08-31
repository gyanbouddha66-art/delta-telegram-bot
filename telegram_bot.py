import os
import requests

from trading_engine import get_engine_status, get_signal
from groq_ai import ask_groq
from delta_api import test_delta, get_delta_balances
from voice_utils import (
    send_message,
    send_voice,
    process_voice as voice_utils_process_voice,
    voice_status
)


# ============================================================
# GH BOSS AI — TELEGRAM BOT (CLEAN & INTEGRATED)
# ============================================================

TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    ""
).strip()


# ============================================================
# AI CHAT WRAPPER (FOR VOICE UTILS)
# ============================================================

def handle_ai_text_query(user_text):
    """
    यह फंक्शन voice_utils द्वारा transcribe किए गए टेक्स्ट को 
    Groq AI पर भेजकर जवाब वापस देता है।
    """
    prompt = f"""
You are GH BOSS AI.

User message:

{user_text}

Understand the exact question.

NORMAL CONVERSATION:
Answer general questions normally.

CRYPTO:
You can discuss BTC, ETH, SOL, ARCUSD
and other cryptocurrencies.

TRADING:
When relevant discuss:

Direction
Trend
Momentum
Price Action
Support
Resistance
Entry
Stop Loss
Take Profit
Risk/Reward
Invalidation

LIVE DATA RULE:

Never invent a live price.

If verified live market data is not supplied,
say:

"मेरे पास verified live market data उपलब्ध नहीं है।"

Do not pretend old data is current.

EXECUTION RULE:

Normal AI chat must NOT place an order.

Never claim an order was executed unless
the actual trading engine confirms execution.

Reply in Hindi unless the user uses another language.

Keep answers concise and useful.

Trading execution remains under manual control.
"""

    answer = ask_groq(prompt)
    return str(answer).strip()


# ============================================================
# AI CHAT (TEXT → AI → TEXT + VOICE)
# ============================================================

def ai_chat(
    chat_id,
    user_text,
    voice_reply=True
):

    print(
        "🧠 GH BOSS AI:",
        user_text
    )

    send_message(
        chat_id,
        "🧠 GH BOSS AI analyzing..."
    )

    try:
        answer = handle_ai_text_query(user_text)

        if not answer:
            answer = "AI ने कोई response नहीं दिया।"

        # Text Response भेजना
        remaining = answer
        while len(remaining) > 3900:
            part = remaining[:3900]
            remaining = remaining[3900:]
            send_message(chat_id, "🧠 GH BOSS AI\n\n" + part)

        if remaining:
            send_message(chat_id, "🧠 GH BOSS AI\n\n" + remaining)

        # Voice Reply भेजना (voice_utils का tts इस्तेमाल करके)
        if voice_reply:
            from voice_utils import text_to_voice
            audio_file = text_to_voice(answer)
            if audio_file:
                try:
                    success = send_voice(chat_id, audio_file)
                    if not success:
                        send_message(chat_id, "⚠️ Voice Telegram पर भेजा नहीं जा पाया।")
                finally:
                    try:
                        os.remove(audio_file)
                    except Exception:
                        pass
            else:
                send_message(chat_id, "⚠️ Voice reply generate नहीं हो पाया।")

    except Exception as e:
        print(
            "❌ GROQ CHAT ERROR:",
            e
        )
        send_message(
            chat_id,
            "❌ GROQ AI ERROR\n\n"
            + str(e)
        )


# ============================================================
# PROCESS VOICE (DELEGATED TO VOICE UTILS)
# ============================================================

def process_voice(chat_id, file_id):
    # यह voice_utils.py के process_voice को कॉल करता है
    # और साथ में हमारा AI हैंडलर पास करता है
    voice_utils_process_voice(
        chat_id,
        file_id,
        handle_ai_text_query
    )


# ============================================================
# START
# ============================================================

def command_start(chat_id):

    send_message(
        chat_id,
        "🧠 GH BOSS AI\n\n"

        "✅ Telegram Connected\n"
        "✅ Command System Online\n"
        "✅ Groq AI Loaded\n"
        "✅ Delta Module Loaded\n"
        "🎤 Voice Input Enabled\n"
        "🔊 Voice Reply Enabled\n\n"

        "🤖 NORMAL CHAT ENABLED\n\n"

        "आप text या voice दोनों में सवाल पूछ सकते हैं।\n\n"

        "Text → AI → Text + Voice\n"
        "Voice → Whisper → AI → Text + Voice\n\n"

        "Examples:\n"
        "BTC कैसा है?\n"
        "ETH analysis करो\n"
        "SOL trend बताओ\n"
        "ARCUSD analysis करो\n"
        "नमस्ते\n\n"

        "COMMANDS\n\n"

        "/status\n"
        "/delta\n"
        "/balance\n"
        "/signal\n"
        "/ai\n"
        "/help\n\n"

        "🧠 AI: GROQ\n"
        "🎤 STT: GROQ WHISPER\n"
        "🔊 TTS: EDGE-TTS\n\n"

        "Trading Execution: MANUAL"
    )


# ============================================================
# STATUS
# ============================================================

def command_status(chat_id):

    try:
        status = get_engine_status()
        delta = test_delta()
        groq_ok = bool(GROQ_API_KEY)

        send_message(
            chat_id,
            "📊 GH BOSS STATUS\n\n"
            f"Engine: {status.get('engine', 'UNKNOWN')}\n"
            f"Mode: {status.get('mode', 'UNKNOWN')}\n"
            f"Signal: {status.get('signal', 'NO SIGNAL')}\n"
            f"Confidence: {status.get('confidence', 0)}%\n\n"
            "Telegram: CONNECTED 🟢\n"
            f"Groq: {'CONNECTED 🟢' if groq_ok else 'MISSING 🔴'}\n"
            f"Delta: {'CONNECTED 🟢' if delta.get('success') else 'ERROR 🔴'}\n"
            "Voice Input: ENABLED 🎤\n"
            "Voice Reply: ENABLED 🔊\n"
            "Gemini: REMOVED\n"
            "Execution: MANUAL"
        )

    except Exception as e:
        send_message(
            chat_id,
            "❌ STATUS ERROR\n\n"
            + str(e)
        )


# ============================================================
# DELTA
# ============================================================

def command_delta(chat_id):
    send_message(chat_id, "🔄 Testing Delta API...")
    try:
        result = test_delta()
        if result.get("success"):
            send_message(
                chat_id,
                "🟢 DELTA API OK\n\n"
                "Authentication: OK\n"
                "Connection: OK\n"
                "Read-only test completed.\n"
                "No order placed."
            )
        else:
            send_message(
                chat_id,
                "🔴 DELTA API ERROR\n\n"
                + str(result.get("error", "Unknown error"))
            )
    except Exception as e:
        send_message(chat_id, "❌ DELTA ERROR\n\n" + str(e))


# ============================================================
# BALANCE
# ============================================================

def command_balance(chat_id):
    send_message(chat_id, "💰 Checking Delta balance...")
    try:
        result = get_delta_balances()
        if not result.get("success"):
            send_message(
                chat_id,
                "❌ BALANCE ERROR\n\n"
                + str(result.get("error", "Unknown error"))
            )
            return

        send_message(
            chat_id,
            "💰 DELTA ACCOUNT\n\n"
            + str(result)
        )
    except Exception as e:
        send_message(chat_id, "❌ BALANCE ERROR\n\n" + str(e))


# ============================================================
# SIGNAL
# ============================================================

def command_signal(chat_id):
    try:
        signal = get_signal()
        direction = signal.get("signal", "NO SIGNAL")
        confidence = signal.get("confidence", 0)
        reason = signal.get("reason", "No reason available")
        entry = signal.get("entry")
        sl = signal.get("sl")
        tp = signal.get("tp")

        message = (
            "📈 GH MARKET SIGNAL\n\n"
            f"Symbol: {signal.get('symbol', 'UNKNOWN')}\n"
            f"Timeframe: {signal.get('timeframe', 'UNKNOWN')}\n\n"
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

        message += "\nExecution: MANUAL"
        send_message(chat_id, message)

    except Exception as e:
        send_message(chat_id, "❌ SIGNAL ERROR\n\n" + str(e))


# ============================================================
# AI COMMAND
# ============================================================

def command_ai(chat_id):
    ai_chat(
        chat_id,
        "नमस्ते GH BOSS AI, सामान्य बातचीत शुरू करो।",
        voice_reply=True
    )


# ============================================================
# HELP
# ============================================================

def command_help(chat_id):

    send_message(
        chat_id,
        "🧠 GH BOSS AI\n\n"
        "COMMANDS\n\n"
        "/start\nBot start\n\n"
        "/status\nSystem status\n\n"
        "/delta\nDelta API test\n\n"
        "/balance\nDelta balance\n\n"
        "/signal\nTrading signal\n\n"
        "/ai\nAI chat\n\n"
        "/help\nCommands\n\n"
        "━━━━━━━━━━━━━━\n"
        "🎤 VOICE AI\n"
        "━━━━━━━━━━━━━━\n\n"
        "🎤 Voice → Whisper → Text → AI → Text + Voice\n\n"
        "Trading Execution: MANUAL"
    )


# ============================================================
# MAIN ROUTER
# ============================================================

def process_command(chat_id, command):
    if not command:
        return

    original_text = str(command).strip()
    if not original_text:
        return

    command_lower = original_text.lower()

    if command_lower.startswith("/") and "@" in command_lower:
        command_lower = command_lower.split("@")[0]

    print("🎯 TELEGRAM MESSAGE:", original_text)

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
            command_ai(chat_id)
        elif command_lower == "/help":
            command_help(chat_id)
        else:
            ai_chat(chat_id, original_text, voice_reply=True)

    except Exception as e:
        print("❌ COMMAND ROUTER ERROR:", e)
        send_message(chat_id, "❌ SYSTEM ERROR\n\n" + str(e))
