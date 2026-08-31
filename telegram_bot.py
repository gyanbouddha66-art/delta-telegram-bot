import os
import requests

from trading_engine import get_engine_status, get_signal
from gemini_ai import ask_gemini
from delta_api import test_delta, get_delta_balances


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


# ============================================================
# TELEGRAM SEND
# ============================================================

def send_message(chat_id, text):

    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN missing")
        return False

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

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
        print("Telegram Error:", e)
        return False


# ============================================================
# GEMINI NORMAL CHAT
# ============================================================

def gemini_chat(chat_id, user_text):

    print("Gemini request:", user_text)

    send_message(
        chat_id,
        "Gemini AI analyzing..."
    )

    try:

        prompt = f"""
You are GH BOSS AI.

The user message is:

{user_text}

Understand the user's actual question.

You can have normal conversations.

You can discuss:
BTC
ETH
SOL
ARCUSD
and other cryptocurrencies.

If the user asks about a cryptocurrency,
focus specifically on that cryptocurrency.

If the user asks for market analysis,
discuss price action, trend, momentum,
support, resistance, volatility and risk.

If verified live market data is not provided,
do not invent a current price.

If the user asks about entry or exit,
give analysis and possible levels only when
there is enough information.

The user has manual control of trading execution.

Do not place real orders from this chat function.

Reply naturally in Hindi when the user uses Hindi.

Do not repeat a fixed answer.
Answer the exact question asked by the user.

User message:
{user_text}
"""

        answer = ask_gemini(prompt)

        answer = str(answer).strip()

        if not answer:
            answer = "Gemini ने कोई response नहीं दिया।"

        # Telegram message size protection
        max_length = 3900

        if len(answer) <= max_length:

            send_message(
                chat_id,
                "GEMINI\n\n" + answer
            )

        else:

            start = 0

            while start < len(answer):

                part = answer[start:start + max_length]

                send_message(
                    chat_id,
                    "GEMINI\n\n" + part
                )

                start += max_length

    except Exception as e:

        print(
            "GEMINI CHAT ERROR:",
            e
        )

        send_message(
            chat_id,
            "GEMINI ERROR\n\n" + str(e)
        )


# ============================================================
# START
# ============================================================

def command_start(chat_id):

    send_message(
        chat_id,

        "GH BOSS AI\n\n"
        "Telegram Connected\n"
        "Command System Online\n"
        "Gemini Module Loaded\n"
        "Delta Module Loaded\n\n"

        "NORMAL CHAT ENABLED\n\n"

        "Aap seedha koi bhi message bhej sakte hain.\n\n"

        "Examples:\n"
        "ETH\n"
        "SOL\n"
        "ARCUSD\n"
        "BTC kaisa hai?\n"
        "ETH analysis karo\n"
        "SOL trend batao\n"
        "ARCUSD analysis karo\n\n"

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

        gemini_ok = bool(
            os.getenv(
                "GEMINI_API_KEY",
                ""
            ).strip()
        )

        send_message(
            chat_id,

            "GH BOSS STATUS\n\n"

            f"Engine: "
            f"{status.get('engine', 'UNKNOWN')}\n"

            f"Mode: "
            f"{status.get('mode', 'UNKNOWN')}\n"

            f"Signal: "
            f"{status.get('signal', 'NO SIGNAL')}\n"

            f"Confidence: "
            f"{status.get('confidence', 0)}%\n\n"

            "Telegram: CONNECTED\n"

            f"Gemini: "
            f"{'CONFIGURED' if gemini_ok else 'MISSING'}\n"

            f"Delta: "
            f"{'CONNECTED' if delta.get('success') else 'ERROR'}"
        )

    except Exception as e:

        print("STATUS ERROR:", e)

        send_message(
            chat_id,
            "STATUS ERROR\n\n" + str(e)
        )


# ============================================================
# DELTA
# ============================================================

def command_delta(chat_id):

    send_message(
        chat_id,
        "Testing Delta API..."
    )

    try:

        result = test_delta()

        if result.get("success"):

            send_message(
                chat_id,

                "DELTA API OK\n\n"
                "Authentication: OK\n"
                "Connection: OK\n"
                "Read-only test completed.\n"
                "No order placed."
            )

        else:

            send_message(
                chat_id,

                "DELTA API ERROR\n\n"
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
            "DELTA ERROR\n\n" + str(e)
        )


# ============================================================
# BALANCE
# ============================================================

def command_balance(chat_id):

    send_message(
        chat_id,
        "Checking Delta balance..."
    )

    try:

        result = get_delta_balances()

        if not result.get("success"):

            send_message(
                chat_id,

                "BALANCE ERROR\n\n"
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

            "DELTA ACCOUNT\n\n"
            + str(result)
        )

    except Exception as e:

        send_message(
            chat_id,
            "BALANCE ERROR\n\n" + str(e)
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

            "GH MARKET SIGNAL\n\n"

            f"Signal: {direction}\n"
            f"Confidence: {confidence}%\n\n"

            f"Analysis:\n{reason}"
        )

    except Exception as e:

        send_message(
            chat_id,
            "SIGNAL ERROR\n\n" + str(e)
        )


# ============================================================
# AI COMMAND
# ============================================================

def command_ai(chat_id):

    gemini_chat(
        chat_id,
        "Namaste. Normal conversation start karo."
    )


# ============================================================
# HELP
# ============================================================

def command_help(chat_id):

    send_message(
        chat_id,

        "GH BOSS AI\n\n"

        "COMMANDS\n\n"

        "/start\n"
        "Bot start\n\n"

        "/status\n"
        "System status\n\n"

        "/delta\n"
        "Delta API test\n\n"

        "/balance\n"
        "Delta account balance\n\n"

        "/signal\n"
        "Trading signal\n\n"

        "/ai\n"
        "Gemini AI chat\n\n"

        "/help\n"
        "Commands\n\n"

        "NORMAL CHAT\n\n"

        "ETH\n"
        "SOL\n"
        "ARCUSD\n"
        "BTC kaisa hai?\n"
        "ETH analysis karo\n"
        "SOL trend batao\n"
        "ARCUSD analysis karo\n"
        "Koi bhi normal question pooch sakte hain."
    )


# ============================================================
# COMMAND ROUTER
# ============================================================

def process_command(chat_id, command):

    if not command:
        return

    original_text = command.strip()
    command_lower = original_text.lower()

    # Handle /start@botname
    if command_lower.startswith("/") and "@" in command_lower:
        command_lower = command_lower.split("@")[0]

    print(
        "TELEGRAM MESSAGE:",
        original_text
    )

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

            # Any normal text goes to Gemini
            gemini_chat(
                chat_id,
                original_text
            )

    except Exception as e:

        print(
            "COMMAND ROUTER ERROR:",
            e
        )

        send_message(
            chat_id,

            "SYSTEM ERROR\n\n"
            + str(e)
        )
