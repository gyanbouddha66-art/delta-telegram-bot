import os
import requests

from trading_engine import get_engine_status, get_signal
from gemini_ai import ask_gemini
from delta_api import test_delta, get_delta_balances

============================================================

CONFIG

============================================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

============================================================

TELEGRAM SEND

============================================================

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

============================================================

GEMINI NORMAL CHAT

============================================================

def gemini_chat(chat_id, user_text):

print("Sending message to Gemini:", user_text)

send_message(
    chat_id,
    "Gemini AI analyzing..."
)

try:

    prompt = f"""

You are GH BOSS AI.

User message:

{user_text}

Understand the user's exact question and answer it.

You can handle:

Normal conversation
Crypto discussion
Market analysis
Price action
Trend
Momentum
Volume
Support and resistance
Entry and exit analysis
Risk/reward
Trading system discussion

Important assets:

BTC
ETH
SOL
ARCUSD

If the user mentions another cryptocurrency,
analyze that cryptocurrency too.

Do not repeat a fixed answer.

If the user asks a normal question,
answer normally.

If the user asks about a cryptocurrency,
focus specifically on that cryptocurrency.

If the user asks for trading analysis,
give a structured analysis.

Do not invent live prices.

If verified live market data is not supplied,
clearly say that live price data is not available.

For entry and exit requests,
separate analysis from actual order execution.

This Telegram chat does NOT place real orders.

The user's trading execution is controlled separately.

Reply in Hindi unless the user uses another language.

Answer the exact question.
"""

    answer = ask_gemini(prompt)

    answer = str(answer).strip()

    if not answer:

        answer = "Gemini ने कोई response नहीं दिया।"

    # Telegram message size protection

    if len(answer) <= 3900:

        send_message(
            chat_id,
            "GEMINI\n\n" + answer
        )

    else:

        start = 0

        while start < len(answer):

            part = answer[
                start:start + 3900
            ]

            send_message(
                chat_id,
                "GEMINI\n\n" + part
            )

            start += 3900

except Exception as e:

    print(
        "GEMINI CHAT ERROR:",
        e
    )

    send_message(
        chat_id,
        "GEMINI ERROR\n\n"
        + str(e)
    )

============================================================

START

============================================================

def command_start(chat_id):

send_message(
    chat_id,

    "GH BOSS AI\n\n"

    "Telegram Connected\n"
    "Command System Online\n"
    "Gemini Module Loaded\n"
    "Delta Module Loaded\n\n"

    "NORMAL CHAT ENABLED\n\n"

    "Direct examples:\n"
    "ETH\n"
    "SOL\n"
    "ARCUSD\n"
    "BTC कैसा है?\n"
    "ETH analysis करो\n"
    "SOL का trend बताओ\n"
    "ARCUSD entry exit बताओ\n\n"

    "COMMANDS\n\n"

    "/status\n"
    "/delta\n"
    "/balance\n"
    "/signal\n"
    "/ai\n"
    "/help"
)

============================================================

STATUS

============================================================

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

    delta_ok = delta.get(
        "success",
        False
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

        f"Telegram: CONNECTED\n"

        f"Gemini: "
        f"{'CONNECTED' if gemini_ok else 'MISSING'}\n"

        f"Delta: "
        f"{'CONNECTED' if delta_ok else 'ERROR'}"
    )

except Exception as e:

    print(
        "STATUS ERROR:",
        e
    )

    send_message(
        chat_id,
        "STATUS ERROR\n\n"
        + str(e)
    )

============================================================

DELTA

============================================================

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
        "DELTA ERROR\n\n"
        + str(e)
    )

============================================================

BALANCE

============================================================

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
        "BALANCE ERROR\n\n"
        + str(e)
    )

============================================================

SIGNAL

============================================================

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
        "SIGNAL ERROR\n\n"
        + str(e)
    )

============================================================

AI

============================================================

def command_ai(chat_id):

gemini_chat(
    chat_id,
    "नमस्ते GH BOSS AI। सामान्य बातचीत शुरू करो।"
)

============================================================

HELP

============================================================

def command_help(chat_id):

send_message(
    chat_id,

    "GH BOSS AI\n\n"

    "COMMANDS\n\n"

    "/start - Start bot\n"
    "/status - System status\n"
    "/delta - Delta API test\n"
    "/balance - Account balance\n"
    "/signal - Trading signal\n"
    "/ai - Gemini AI\n"
    "/help - Commands\n\n"

    "NORMAL CHAT\n\n"

    "ETH\n"
    "SOL\n"
    "ARCUSD\n"
    "BTC कैसा है?\n"
    "ETH analysis करो\n"
    "SOL trend बताओ\n"
    "ARCUSD entry बताओ\n"
    "कोई भी सामान्य सवाल पूछें।"
)

============================================================

MAIN ROUTER

============================================================

def process_command(chat_id, command):

if not command:

    return

original_text = command.strip()

command_lower = original_text.lower()

# Handle /start@botname

if (
    command_lower.startswith("/")
    and "@" in command_lower
):

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

        # Every other message goes to Gemini

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
