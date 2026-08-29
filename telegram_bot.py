import os
import requests

from trading_engine import get_engine_status, get_signal
from gemini_ai import ask_gemini


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def send_message(chat_id, text):

    if not TOKEN:
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

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


def process_command(chat_id, command):

    command = command.strip().lower()

    # =========================
    # START
    # =========================

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
            "/ai\n"
            "/help"
        )

    # =========================
    # STATUS
    # =========================

    elif command == "/status":

        status = get_engine_status()

        send_message(
            chat_id,
            f"🟢 GH ENGINE\n\n"
            f"Engine: {status['engine']}\n"
            f"Mode: {status['mode']}\n"
            f"Live Trading: {status['live_trading']}\n"
            f"Signal: {status['signal']}"
        )

    # =========================
    # SIGNAL
    # =========================

    elif command == "/signal":

        signal = get_signal()

        send_message(
            chat_id,
            f"📊 SIGNAL\n\n"
            f"Signal: {signal['signal']}\n"
            f"Confidence: {signal['confidence']}%\n"
            f"Reason: {signal['reason']}"
        )

    # =========================
    # GEMINI
    # =========================

    elif command == "/ai":

        answer = ask_gemini(
            "Explain how a professional trading system "
            "should evaluate market direction. "
            "Do not place or recommend a live trade."
        )

        send_message(
            chat_id,
            "🧠 GEMINI AI\n\n" + answer
        )

    # =========================
    # HELP
    # =========================

    elif command == "/help":

        send_message(
            chat_id,
            "📚 COMMANDS\n\n"
            "/start - Start bot\n"
            "/status - System status\n"
            "/signal - Current signal\n"
            "/ai - Gemini AI test\n"
            "/help - Commands"
        )

    else:

        send_message(
            chat_id,
            "❌ Unknown command.\n\n"
            "Use /help"
        )
