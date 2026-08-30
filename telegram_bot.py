import os
import requests

from trading_engine import get_engine_status, get_signal
from gemini_ai import ask_gemini
from delta_api import test_delta, get_delta_balances


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# ============================================================
# SEND TELEGRAM MESSAGE
# ============================================================

def send_message(chat_id, text):

    if not TOKEN:
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": str(text)
            },
            timeout=15
        )

        return response.ok

    except Exception:
        return False


# ============================================================
# /START
# ============================================================

def command_start(chat_id):

    send_message(
        chat_id,

        "GH AI TRADING BOT\n\n"
        "Bot connected successfully.\n\n"
        "Mode: TEST\n"
        "Live Trading: OFF\n\n"

        "COMMANDS\n\n"
        "/status - System status\n"
        "/delta - Delta API test\n"
        "/balance - Delta balance\n"
        "/signal - Trading signal\n"
        "/ai - Gemini AI\n"
        "/help - Commands"
    )


# ============================================================
# /STATUS
# ============================================================

def command_status(chat_id):

    try:

        status = get_engine_status()
        delta = test_delta()

        delta_status = (
            "CONNECTED"
            if delta.get("success")
            else "ERROR"
        )

        send_message(
            chat_id,

            "GH SYSTEM STATUS\n\n"

            f"Engine: "
            f"{status.get('engine', 'UNKNOWN')}\n"

            f"Mode: "
            f"{status.get('mode', 'TEST')}\n"

            f"Live Trading: "
            f"{status.get('live_trading', False)}\n"

            f"Signal: "
            f"{status.get('signal', 'NO SIGNAL')}\n\n"

            f"Delta API: {delta_status}\n"
            "Gemini: AVAILABLE\n"
            "Telegram: CONNECTED\n\n"

            "Orders: OFF"
        )

    except Exception as e:

        send_message(
            chat_id,
            "STATUS ERROR\n\n" + str(e)
        )


# ============================================================
# /DELTA
# ============================================================

def command_delta(chat_id):

    send_message(
        chat_id,
        "Testing Delta API...\n\n"
        "Read-only request.\n"
        "No order will be placed."
    )

    try:

        result = test_delta()

        if result.get("success"):

            send_message(
                chat_id,

                "DELTA API\n\n"
                "Authentication: OK\n"
                "Connection: OK\n"
                "HTTP Status: 200\n\n"
                "Account API: CONNECTED\n"
                "Orders: OFF"
            )

        else:

            send_message(
                chat_id,

                "DELTA API ERROR\n\n"
                f"Stage: "
                f"{result.get('stage', 'unknown')}\n\n"
                f"Error:\n"
                f"{result.get('error')}"
            )

    except Exception as e:

        send_message(
            chat_id,
            "DELTA ERROR\n\n" + str(e)
        )


# ============================================================
# /BALANCE
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
                + str(result.get("error"))
            )

            return

        usd = result.get("usd") or {}
        inr = result.get("inr") or {}
        eth = result.get("eth") or {}
        btc = result.get("btc") or {}

        usd_balance = usd.get(
            "balance",
            "0"
        )

        usd_available = usd.get(
            "available_balance",
            "0"
        )

        usd_inr = usd.get(
            "balance_inr",
            "0"
        )

        inr_balance = inr.get(
            "balance",
            "0"
        )

        inr_available = inr.get(
            "available_balance",
            "0"
        )

        eth_balance = eth.get(
            "balance",
            "0"
        )

        btc_balance = btc.get(
            "balance",
            "0"
        )

        send_message(
            chat_id,

            "DELTA ACCOUNT\n\n"

            "USD\n"
            f"Balance: {usd_balance}\n"
            f"Available: {usd_available}\n"
            f"INR Value: {usd_inr}\n\n"

            "INR\n"
            f"Balance: {inr_balance}\n"
            f"Available: {inr_available}\n\n"

            "CRYPTO\n"
            f"ETH: {eth_balance}\n"
            f"BTC: {btc_balance}\n\n"

            "API: CONNECTED\n"
            "Orders: OFF"
        )

    except Exception as e:

        send_message(
            chat_id,

            "BALANCE ERROR\n\n"
            + str(e)
        )


# ============================================================
# /SIGNAL
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

            "GH TRADING SIGNAL\n\n"

            f"Signal: {direction}\n"
            f"Confidence: {confidence}%\n\n"

            f"Reason:\n{reason}\n\n"

            "LIVE ORDER: OFF"
        )

    except Exception as e:

        send_message(
            chat_id,

            "SIGNAL ERROR\n\n"
            + str(e)
        )


# ============================================================
# /AI
# ============================================================

def command_ai(chat_id):

    send_message(
        chat_id,
        "Gemini AI processing..."
    )

    try:

        answer = ask_gemini(

            "Explain how a professional "
            "trading system evaluates market "
            "direction using price action, "
            "trend, momentum, volume and risk "
            "management. Do not recommend a "
            "live trade."
        )

        answer = str(answer)

        # Telegram maximum message protection
        if len(answer) > 4000:

            answer = (
                answer[:3900]
                + "\n\n...[truncated]"
            )

        send_message(
            chat_id,
            "GEMINI AI\n\n" + answer
        )

    except Exception as e:

        send_message(
            chat_id,

            "GEMINI ERROR\n\n"
            + str(e)
        )


# ============================================================
# /HELP
# ============================================================

def command_help(chat_id):

    send_message(
        chat_id,

        "GH AI TRADING BOT\n\n"

        "/start\n"
        "Start bot\n\n"

        "/status\n"
        "System status\n\n"

        "/delta\n"
        "Delta API test\n\n"

        "/balance\n"
        "Delta account balance\n\n"

        "/signal\n"
        "Trading signal\n\n"

        "/ai\n"
        "Gemini AI\n\n"

        "/help\n"
        "Commands\n\n"

        "LIVE TRADING: OFF"
    )


# ============================================================
# MAIN COMMAND ROUTER
# ============================================================

def process_command(chat_id, command):

    if not command:
        return

    command = command.strip().lower()

    # Handles /start@botname
    if "@" in command:
        command = command.split("@")[0]

    if command == "/start":

        command_start(chat_id)

    elif command == "/status":

        command_status(chat_id)

    elif command == "/delta":

        command_delta(chat_id)

    elif command == "/balance":

        command_balance(chat_id)

    elif command == "/signal":

        command_signal(chat_id)

    elif command == "/ai":

        command_ai(chat_id)

    elif command == "/help":

        command_help(chat_id)

    else:

        send_message(
            chat_id,

            "Unknown command.\n\n"
            "Use /help"
        )
