import os
import requests

from trading_engine import get_engine_status, get_signal
from groq_ai import ask_groq
from delta_api import test_delta, get_delta_balances


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()


# ============================================================
# SEND TELEGRAM MESSAGE
# ============================================================

def send_message(chat_id, text):

    if not TOKEN:

        print("❌ TELEGRAM_BOT_TOKEN missing")

        return False

    try:

        url = (
            f"https://api.telegram.org/"
            f"bot{TOKEN}/sendMessage"
        )

        response = requests.post(

            url,

            json={
                "chat_id": chat_id,
                "text": str(text)
            },

            timeout=20
        )

        print(
            "Telegram:",
            response.status_code,
            response.text[:300]
        )

        return response.ok

    except Exception as e:

        print(
            "❌ Telegram Error:",
            e
        )

        return False


# ============================================================
# GROQ AI CHAT
# ============================================================

def ai_chat(chat_id, user_text):

    print(
        "🧠 GROQ MESSAGE:",
        user_text
    )

    send_message(
        chat_id,
        "🧠 GH BOSS AI analyzing..."
    )

    try:

        prompt = f"""
You are GH BOSS AI.

User message:

{user_text}

Understand the exact user question.

You can have normal conversation.

You can discuss cryptocurrencies including:

BTC
ETH
SOL
ARCUSD

If another cryptocurrency is mentioned,
discuss that cryptocurrency too.

For trading-analysis questions discuss when appropriate:

- Direction
- Trend
- Momentum
- Price action
- Support
- Resistance
- Entry
- Stop Loss
- Take Profit
- Risk/Reward
- Invalidation

IMPORTANT:

Never invent a live price.

If verified live market data is not supplied,
say clearly that live price data is unavailable.

Separate analysis from confirmed live execution.

Do not place any real order.

The user has manual control over execution.

Answer the actual question.
Do not repeat a fixed response.

Reply in Hindi unless the user uses another language.

Be concise but useful.
"""

        answer = ask_groq(prompt)

        answer = str(answer).strip()

        if not answer:

            answer = (
                "AI ने कोई response नहीं दिया।"
            )

        # ====================================================
        # TELEGRAM MESSAGE LIMIT
        # ====================================================

        while len(answer) > 3900:

            part = answer[:3900]

            answer = answer[3900:]

            send_message(
                chat_id,
                "🧠 GH BOSS AI\n\n" + part
            )

        if answer:

            send_message(
                chat_id,
                "🧠 GH BOSS AI\n\n" + answer
            )

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
# START
# ============================================================

def command_start(chat_id):

    send_message(

        chat_id,

        "🧠 GH BOSS AI\n\n"

        "✅ Telegram Connected\n"
        "✅ Command System Online\n"
        "✅ Groq AI Loaded\n"
        "✅ Delta Module Loaded\n\n"

        "🤖 NORMAL CHAT ENABLED\n\n"

        "आप सीधे कोई भी सवाल पूछ सकते हैं।\n\n"

        "Examples:\n"
        "BTC कैसा है?\n"
        "ETH analysis करो\n"
        "SOL trend बताओ\n"
        "ARCUSD analysis करो\n"
        "नमस्ते\n"
        "भारत की राजधानी क्या है?\n\n"

        "COMMANDS\n\n"

        "/status\n"
        "/delta\n"
        "/balance\n"
        "/signal\n"
        "/ai\n"
        "/help"
    )


# ============================================================
# STATUS
# ============================================================

def command_status(chat_id):

    try:

        status = get_engine_status()

        delta = test_delta()

        groq_ok = bool(
            os.getenv(
                "GROQ_API_KEY",
                ""
            ).strip()
        )

        send_message(

            chat_id,

            "📊 GH BOSS STATUS\n\n"

            f"Engine: "
            f"{status.get('engine', 'UNKNOWN')}\n"

            f"Mode: "
            f"{status.get('mode', 'UNKNOWN')}\n"

            f"Signal: "
            f"{status.get('signal', 'NO SIGNAL')}\n"

            f"Confidence: "
            f"{status.get('confidence', 0)}%\n\n"

            "Telegram: CONNECTED 🟢\n"

            f"Groq: "
            f"{'CONFIGURED 🟢' if groq_ok else 'MISSING 🔴'}\n"

            f"Delta: "
            f"{'CONNECTED 🟢' if delta.get('success') else 'ERROR 🔴'}\n"

            "Gemini: REMOVED"
        )

    except Exception as e:

        send_message(
            chat_id,
            "❌ STATUS ERROR\n\n" + str(e)
        )


# ============================================================
# DELTA
# ============================================================

def command_delta(chat_id):

    send_message(
        chat_id,
        "🔄 Testing Delta API..."
    )

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
                + str(
                    result.get(
                        "error",
                        "Unknown error"
                    )
                )
            )

    except Exception as e:

        send_message(
            chat_id,
            "❌ DELTA ERROR\n\n" + str(e)
        )


# ============================================================
# BALANCE
# ============================================================

def command_balance(chat_id):

    send_message(
        chat_id,
        "💰 Checking Delta balance..."
    )

    try:

        result = get_delta_balances()

        if not result.get("success"):

            send_message(

                chat_id,

                "❌ BALANCE ERROR\n\n"
                + str(
                    result.get(
                        "error",
                        "Unknown error"
                    )
                )
            )

            return

        send_message(

            chat_id,

            "💰 DELTA ACCOUNT\n\n"
            + str(result)
        )

    except Exception as e:

        send_message(

            chat_id,

            "❌ BALANCE ERROR\n\n"
            + str(e)
        )


# ============================================================
# SIGNAL
# ============================================================

def command_signal(chat_id):

    try:

        signal = get_signal()

        direction = signal.get(
            "signal",
            "NO SIGNAL"
        )

        confidence = signal.get(
            "confidence",
            0
        )

        reason = signal.get(
            "reason",
            "No reason available"
        )

        send_message(

            chat_id,

            "📈 GH MARKET SIGNAL\n\n"

            f"Signal: {direction}\n"
            f"Confidence: {confidence}%\n\n"

            f"Analysis:\n{reason}\n\n"

            "Execution: MANUAL"
        )

    except Exception as e:

        send_message(

            chat_id,

            "❌ SIGNAL ERROR\n\n"
            + str(e)
        )


# ============================================================
# AI COMMAND
# ============================================================

def command_ai(chat_id):

    ai_chat(
        chat_id,
        "नमस्ते GH BOSS AI, सामान्य बातचीत शुरू करो।"
    )


# ============================================================
# HELP
# ============================================================

def command_help(chat_id):

    send_message(

        chat_id,

        "🧠 GH BOSS AI\n\n"

        "COMMANDS\n\n"

        "/start\n"
        "Bot start\n\n"

        "/status\n"
        "System status\n\n"

        "/delta\n"
        "Delta API test\n\n"

        "/balance\n"
        "Delta balance\n\n"

        "/signal\n"
        "Trading signal\n\n"

        "/ai\n"
        "AI chat\n\n"

        "/help\n"
        "Commands\n\n"

        "━━━━━━━━━━━━━━\n"
        "🤖 NORMAL CHAT\n"
        "━━━━━━━━━━━━━━\n\n"

        "BTC\n"
        "ETH\n"
        "SOL\n"
        "ARCUSD\n\n"

        "BTC कैसा है?\n"
        "ETH analysis करो\n"
        "SOL trend बताओ\n"
        "ARCUSD analysis करो\n"
        "कोई भी सामान्य सवाल पूछें।\n\n"

        "AI: GROQ\n"
        "Gemini: REMOVED\n"
        "Trading Execution: MANUAL"
    )


# ============================================================
# MAIN ROUTER
# ============================================================

def process_command(chat_id, command):

    if not command:

        return

    original_text = str(
        command
    ).strip()

    if not original_text:

        return

    command_lower = (
        original_text.lower()
    )

    # /start@botname
    if (
        command_lower.startswith("/")
        and "@"
        in command_lower
    ):

        command_lower = (
            command_lower
            .split("@")[0]
        )

    print(
        "🎯 TELEGRAM MESSAGE:",
        original_text
    )

    try:

        # ====================================================
        # COMMANDS
        # ====================================================

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

        # ====================================================
        # NORMAL CHAT
        # ====================================================

        else:

            ai_chat(
                chat_id,
                original_text
            )

    except Exception as e:

        print(
            "❌ COMMAND ROUTER ERROR:",
            e
        )

        send_message(

            chat_id,

            "❌ SYSTEM ERROR\n\n"
            + str(e)
        )
