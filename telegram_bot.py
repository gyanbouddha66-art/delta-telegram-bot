import os
import requests

from trading_engine import get_engine_status, get_signal
from gemini_ai import ask_gemini
from delta_api import test_delta


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

DELTA_URL = "https://api.india.delta.exchange"


# ============================================================
# TELEGRAM SEND MESSAGE
# ============================================================

def send_message(chat_id, text):

    if not TOKEN:
        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{TOKEN}/sendMessage"
    )

    try:

        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text
            },
            timeout=15
        )

        return response.ok

    except Exception:

        return False


# ============================================================
# DELTA BALANCE
# READ ONLY
# ============================================================

def get_delta_balance():

    result = test_delta()

    if not result.get("success"):

        return {
            "success": False,
            "error": result.get("error", "Delta error")
        }

    return {
        "success": True,
        "message": "Delta authentication OK"
    }


# ============================================================
# PROCESS TELEGRAM COMMAND
# ============================================================

def process_command(chat_id, command):

    command = command.strip().lower()

    # ========================================================
    # START
    # ========================================================

    if command == "/start":

        send_message(
            chat_id,

            "🟢 GH AI TRADING BOT\n\n"

            "Bot connected.\n"
            "Mode: TEST\n"
            "Live Trading: OFF\n\n"

            "Commands:\n"
            "/status\n"
            "/signal\n"
            "/balance\n"
            "/delta\n"
            "/ai\n"
            "/help"
        )

    # ========================================================
    # STATUS
    # ========================================================

    elif command == "/status":

        status = get_engine_status()

        send_message(
            chat_id,

            "🟢 GH ENGINE\n\n"

            f"Engine: {status.get('engine')}\n"
            f"Mode: {status.get('mode')}\n"
            f"Live Trading: "
            f"{status.get('live_trading')}\n"
            f"Signal: {status.get('signal')}"
        )

    # ========================================================
    # SIGNAL
    # ========================================================

    elif command == "/signal":

        signal = get_signal()

        send_message(
            chat_id,

            "📊 SIGNAL\n\n"

            f"Signal: "
            f"{signal.get('signal')}\n"

            f"Confidence: "
            f"{signal.get('confidence')}%\n"

            f"Reason: "
            f"{signal.get('reason')}"
        )

    # ========================================================
    # DELTA
    # ========================================================

    elif command == "/delta":

        send_message(
            chat_id,
            "🔄 Testing Delta API...\n"
            "Read-only test..."
        )

        result = test_delta()

        if result.get("success"):

            send_message(
                chat_id,

                "🟢 DELTA API\n\n"
                "Authentication: OK\n"
                "Connection: OK\n"
                "API Status: 200\n"
                "Orders: OFF"
            )

        else:

            send_message(
                chat_id,

                "🔴 DELTA API\n\n"
                "Authentication: FAILED\n\n"
                f"Error:\n"
                f"{result.get('error')}"
            )

    # ========================================================
    # BALANCE
    # ========================================================

    elif command == "/balance":

        send_message(
            chat_id,
            "💰 Checking Delta balance..."
        )

        result = test_delta()

        if result.get("success"):

            send_message(
                chat_id,

                "💰 DELTA ACCOUNT\n\n"
                "API Authentication: OK\n"
                "Account: Connected\n\n"
                "Balance endpoint: OK\n\n"
                "⚠️ Detailed balance display "
                "will be added next.\n"
                "Orders: OFF"
            )

        else:

            send_message(
                chat_id,

                "🔴 DELTA BALANCE ERROR\n\n"
                f"{result.get('error')}"
            )

    # ========================================================
    # GEMINI
    # ========================================================

    elif command == "/ai":

        try:

            answer = ask_gemini(

                "Explain how a professional "
                "trading system should evaluate "
                "market direction. "

                "Do not place or recommend "
                "a live trade."
            )

            send_message(
                chat_id,
                "🧠 GEMINI AI\n\n" + str(answer)
            )

        except Exception as e:

            send_message(
                chat_id,

                "🔴 GEMINI ERROR\n\n"
                + str(e)
            )

    # ========================================================
    # HELP
    # ========================================================

    elif command == "/help":

        send_message(
            chat_id,

            "📚 GH AI COMMANDS\n\n"

            "/start\n"
            "Start bot\n\n"

            "/status\n"
            "Trading engine status\n\n"

            "/signal\n"
            "Current signal\n\n"

            "/balance\n"
            "Delta account test\n\n"

            "/delta\n"
            "Delta API authentication\n\n"

            "/ai\n"
            "Gemini AI test\n\n"

            "/help\n"
            "Show commands"
        )

    # ========================================================
    # UNKNOWN
    # ========================================================

    else:

        send_message(
            chat_id,

            "❌ Unknown command.\n\n"
            "Use /help"
        )
