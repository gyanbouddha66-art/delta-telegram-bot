import os
import requests

from trading_engine import get_engine_status, get_signal
from gemini_ai import ask_gemini, ask_gemini_chat, ask_gemini_analysis
from delta_api import test_delta, get_delta_balances


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


# ============================================================
# SEND TELEGRAM
# ============================================================

def send_message(chat_id, text):

    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN missing")
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
            "Telegram SEND:",
            response.status_code,
            response.text[:500]
        )

        return response.ok

    except Exception as e:

        print("❌ Telegram send error:", e)
        return False


# ============================================================
# START
# ============================================================

def command_start(chat_id):

    send_message(
        chat_id,

        "🧠 GH BOSS AI\n\n"
        "✅ Telegram Connected\n"
        "✅ Command System Online\n"
        "✅ Gemini Module Loaded\n"
        "✅ Delta Module Loaded\n\n"

        "COMMANDS\n\n"

        "/status - System status\n"
        "/delta - Delta connection test\n"
        "/balance - Account balance\n"
        "/signal - Current signal\n"
        "/ai - Normal Gemini Chat\n"
        "/analyse - Crypto Analysis\n"
        "/help - Commands"
    )


# ============================================================
# STATUS
# ============================================================

def command_status(chat_id):

    try:

        status = get_engine_status()
        delta = test_delta()

        delta_ok = delta.get("success", False)

        send_message(
            chat_id,

            "📊 GH BOSS STATUS\n\n"

            f"Engine: {status.get('engine', 'UNKNOWN')}\n"
            f"Mode: {status.get('mode', 'UNKNOWN')}\n"
            f"Signal: {status.get('signal', 'NO SIGNAL')}\n"
            f"Confidence: {status.get('confidence', 0)}%\n\n"

            f"Delta: "
            f"{'CONNECTED 🟢' if delta_ok else 'ERROR 🔴'}\n"

            "Telegram: CONNECTED 🟢\n"

            f"Gemini: "
            f"{'CONFIGURED 🟢' if os.getenv('GEMINI_API_KEY') else 'MISSING 🔴'}"
        )

    except Exception as e:

        print("STATUS ERROR:", e)

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
                "Read-only test completed."
            )

        else:

            send_message(
                chat_id,

                "🔴 DELTA API ERROR\n\n"
                f"{result.get('error', 'Unknown error')}"
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
            "❌ BALANCE ERROR\n\n" + str(e)
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
            "No reason"
        )

        send_message(
            chat_id,

            "📈 GH MARKET SIGNAL\n\n"

            f"Signal: {direction}\n"
            f"Confidence: {confidence}%\n\n"

            f"Analysis:\n{reason}"
        )

    except Exception as e:

        send_message(
            chat_id,
            "❌ SIGNAL ERROR\n\n" + str(e)
        )


# ============================================================
# NORMAL GEMINI CHAT
# ============================================================

def command_ai(chat_id, user_text):

    if not user_text:

        send_message(
            chat_id,
            "🧠 Gemini से क्या पूछना है?\n\n"
            "Example:\n"
            "/ai नमस्ते BOSS\n"
            "/ai BTC क्या है?\n"
            "/ai मुझे trading समझाओ"
        )

        return

    send_message(
        chat_id,
        "🧠 Gemini सोच रहा है..."
    )

    try:

        answer = ask_gemini_chat(user_text)

        answer = str(answer)

        if len(answer) > 4000:

            answer = (
                answer[:3900]
                + "\n\n...[message shortened]"
            )

        send_message(
            chat_id,
            "🧠 GEMINI\n\n" + answer
        )

    except Exception as e:

        print(
            "GEMINI COMMAND ERROR:",
            e
        )

        send_message(
            chat_id,
            "❌ GEMINI ERROR\n\n" + str(e)
        )


# ============================================================
# CRYPTO ANALYSIS
# ============================================================

def command_analyse(chat_id, symbol):

    if not symbol:

        send_message(
            chat_id,

            "📊 Crypto लिखें।\n\n"
            "Examples:\n"
            "/analyse ARCUSD\n"
            "/analyse ETH\n"
            "/analyse SOL\n"
            "/analyse BTC"
        )

        return

    symbol = symbol.upper()

    # अभी market-data provider से data आने के लिए
    # trading_engine का function बाद में जोड़ा जाएगा।

    send_message(
        chat_id,

        f"🧠 GEMINI ANALYSIS\n\n"
        f"Crypto: {symbol}\n\n"
        "Live market-data connection next module में जोड़ा जाएगा।"
    )


# ============================================================
# HELP
# ============================================================

def command_help(chat_id):

    send_message(
        chat_id,

        "🧠 GH BOSS COMMANDS\n\n"

        "/start\n"
        "Start / connection test\n\n"

        "/status\n"
        "System status\n\n"

        "/delta\n"
        "Delta API test\n\n"

        "/balance\n"
        "Account balance\n\n"

        "/signal\n"
        "Current market signal\n\n"

        "/ai <message>\n"
        "Normal Gemini conversation\n\n"

        "/analyse <crypto>\n"
        "Gemini market analysis\n\n"

        "Supported priority:\n"
        "ARCUSD\n"
        "ETH\n"
        "SOL\n"
        "BTC"
    )


# ============================================================
# COMMAND ROUTER
# ============================================================

def process_command(chat_id, command):

    if not command:
        return

    original = command.strip()

    print(
        f"🎯 COMMAND RECEIVED: {original}"
    )

    # --------------------------------------------------------
    # COMMAND + ARGUMENT
    # --------------------------------------------------------

    parts = original.split(maxsplit=1)

    command_name = parts[0].lower()

    argument = ""

    if len(parts) > 1:
        argument = parts[1].strip()

    # /start@botname
    if "@" in command_name:
        command_name = command_name.split("@")[0]

    try:

        # ----------------------------------------------------
        # START
        # ----------------------------------------------------

        if command_name == "/start":

            command_start(chat_id)

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        elif command_name == "/status":

            command_status(chat_id)

        # ----------------------------------------------------
        # DELTA
        # ----------------------------------------------------

        elif command_name == "/delta":

            command_delta(chat_id)

        # ----------------------------------------------------
        # BALANCE
        # ----------------------------------------------------

        elif command_name == "/balance":

            command_balance(chat_id)

        # ----------------------------------------------------
        # SIGNAL
        # ----------------------------------------------------

        elif command_name == "/signal":

            command_signal(chat_id)

        # ----------------------------------------------------
        # GEMINI NORMAL CHAT
        # ----------------------------------------------------

        elif command_name == "/ai":

            command_ai(
                chat_id,
                argument
            )

        # ----------------------------------------------------
        # CRYPTO ANALYSIS
        # ----------------------------------------------------

        elif command_name in [
            "/analyse",
            "/analysis"
        ]:

            command_analyse(
                chat_id,
                argument
            )

        # ----------------------------------------------------
        # HELP
        # ----------------------------------------------------

        elif command_name == "/help":

            command_help(chat_id)

        # ----------------------------------------------------
        # UNKNOWN
        # ----------------------------------------------------

        else:

            send_message(
                chat_id,

                "❓ Unknown command.\n\n"
                "Use /help"
            )

    except Exception as e:

        print(
            "❌ COMMAND ROUTER ERROR:",
            e
        )

        send_message(
            chat_id,

            "❌ COMMAND ERROR\n\n"
            + str(e)
        )
