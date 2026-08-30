from flask import Flask, jsonify
import os
import time
import threading
import requests

from telegram_bot import process_command
from delta_api import test_delta


# ============================================================
# APP
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIG
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
)

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    ""
)


# ============================================================
# TELEGRAM SEND
# ============================================================

def telegram_send(text, chat_id=None):

    try:

        token = os.getenv(
            "TELEGRAM_BOT_TOKEN",
            ""
        )

        target_chat = (
            chat_id
            if chat_id is not None
            else TELEGRAM_CHAT_ID
        )

        if not token:

            print(
                "❌ TELEGRAM_BOT_TOKEN missing"
            )

            return False

        if not target_chat:

            print(
                "❌ TELEGRAM_CHAT_ID missing"
            )

            return False

        url = (
            f"https://api.telegram.org/"
            f"bot{token}/sendMessage"
        )

        response = requests.post(

            url,

            json={
                "chat_id": target_chat,
                "text": text
            },

            timeout=15
        )

        print(
            "Telegram SEND:",
            response.status_code,
            response.text
        )

        return response.ok

    except Exception as e:

        print(
            "❌ Telegram SEND ERROR:",
            e
        )

        return False


# ============================================================
# TELEGRAM BOT INFORMATION TEST
# ============================================================

def telegram_connection_test():

    print(
        "=========================================="
    )

    print(
        "TELEGRAM CONNECTION TEST"
    )

    print(
        "=========================================="
    )

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        ""
    )

    if not token:

        print(
            "❌ TELEGRAM_BOT_TOKEN missing"
        )

        return False

    try:

        url = (
            f"https://api.telegram.org/"
            f"bot{token}/getMe"
        )

        response = requests.get(
            url,
            timeout=20
        )

        print(
            "Telegram getMe status:",
            response.status_code
        )

        print(
            "Telegram getMe response:",
            response.text
        )

        if response.ok:

            data = response.json()

            if data.get("ok"):

                bot = data.get(
                    "result",
                    {}
                )

                print(
                    "✅ BOT CONNECTED"
                )

                print(
                    "BOT USERNAME:",
                    bot.get("username")
                )

                return True

        print(
            "❌ BOT CONNECTION FAILED"
        )

        return False

    except Exception as e:

        print(
            "❌ TELEGRAM TEST ERROR:",
            e
        )

        return False


# ============================================================
# REMOVE OLD WEBHOOK
# ============================================================

def remove_webhook():

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        ""
    )

    if not token:

        return False

    try:

        url = (
            f"https://api.telegram.org/"
            f"bot{token}/deleteWebhook"
        )

        response = requests.get(

            url,

            params={
                "drop_pending_updates": False
            },

            timeout=20
        )

        print(
            "Webhook removal:",
            response.status_code
        )

        print(
            response.text
        )

        return response.ok

    except Exception as e:

        print(
            "Webhook removal error:",
            e
        )

        return False


# ============================================================
# TELEGRAM POLLING
# ============================================================

def telegram_polling():

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        ""
    )

    if not token:

        print(
            "❌ TELEGRAM_BOT_TOKEN missing"
        )

        return

    print(
        "📡 TELEGRAM POLLING STARTED"
    )

    offset = None

    while True:

        try:

            url = (
                f"https://api.telegram.org/"
                f"bot{token}/getUpdates"
            )

            params = {
                "timeout": 30
            }

            if offset is not None:

                params["offset"] = offset

            response = requests.get(

                url,

                params=params,

                timeout=40
            )

            data = response.json()

            if not data.get("ok"):

                print(
                    "❌ Telegram API error:",
                    data
                )

                time.sleep(5)

                continue

            updates = data.get(
                "result",
                []
            )

            for update in updates:

                offset = (
                    update.get(
                        "update_id",
                        0
                    ) + 1
                )

                print(
                    "🔥 TELEGRAM UPDATE RECEIVED"
                )

                print(
                    update
                )

                message = update.get(
                    "message"
                )

                if not message:

                    continue

                chat = message.get(
                    "chat",
                    {}
                )

                chat_id = chat.get(
                    "id"
                )

                text = message.get(
                    "text",
                    ""
                ).strip()

                if not chat_id:

                    continue

                if not text:

                    continue

                print(
                    "📩 MESSAGE:",
                    text
                )

                print(
                    "👤 CHAT ID:",
                    chat_id
                )

                # --------------------------------------------
                # CHAT ID SECURITY
                # --------------------------------------------

                if (

                    TELEGRAM_CHAT_ID

                    and

                    str(chat_id)
                    !=
                    str(TELEGRAM_CHAT_ID)

                ):

                    print(
                        "⚠️ UNAUTHORIZED CHAT:",
                        chat_id
                    )

                    continue

                # --------------------------------------------
                # COMMAND PROCESSOR
                # --------------------------------------------

                try:

                    result = process_command(

                        chat_id,

                        text
                    )

                    print(
                        "COMMAND RESULT:",
                        result
                    )

                except Exception as e:

                    print(
                        "❌ process_command ERROR:",
                        e
                    )

                    telegram_send(

                        "❌ Command processing error:\n"
                        + str(e),

                        chat_id
                    )

        except requests.exceptions.Timeout:

            print(
                "⏱️ Telegram polling timeout - retrying"
            )

            continue

        except Exception as e:

            print(
                "❌ TELEGRAM POLLING ERROR:",
                e
            )

            time.sleep(5)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return jsonify({

        "system": "GH AI TRADING",

        "status": "ONLINE",

        "telegram": (
            "CONFIGURED"
            if TELEGRAM_BOT_TOKEN
            else "MISSING"
        ),

        "telegram_mode": "POLLING",

        "gemini": (
            "CONFIGURED"
            if os.getenv(
                "GEMINI_API_KEY"
            )
            else "MISSING"
        ),

        "delta": (
            "CONFIGURED"
            if (
                os.getenv("DELTA_API_KEY")
                and
                os.getenv("DELTA_API_SECRET")
            )
            else "MISSING"
        )

    })


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "OK",

        "telegram_polling": True

    })


# ============================================================
# STATUS
# ============================================================

@app.route("/status")
def status():

    return jsonify({

        "server": "ONLINE",

        "telegram_token": bool(
            os.getenv(
                "TELEGRAM_BOT_TOKEN"
            )
        ),

        "telegram_chat_id": bool(
            os.getenv(
                "TELEGRAM_CHAT_ID"
            )
        ),

        "gemini": bool(
            os.getenv(
                "GEMINI_API_KEY"
            )
        ),

        "delta_key": bool(
            os.getenv(
                "DELTA_API_KEY"
            )
        ),

        "delta_secret": bool(
            os.getenv(
                "DELTA_API_SECRET"
            )
        ),

        "telegram_mode": "POLLING"

    })


# ============================================================
# DELTA TEST
# ============================================================

@app.route("/delta-test")
def delta_test():

    try:

        result = test_delta()

        return jsonify(result), 200

    except Exception as e:

        return jsonify({

            "ok": False,

            "error": str(e)

        }), 500


# ============================================================
# PUBLIC IP
# ============================================================

@app.route("/my-ip")
def my_ip():

    try:

        response = requests.get(

            "https://api.ipify.org",

            timeout=10
        )

        return jsonify({

            "public_ip":
            response.text.strip()

        })

    except Exception as e:

        return jsonify({

            "error": str(e)

        }), 500


# ============================================================
# START TELEGRAM POLLING
# ============================================================

def start_background_services():

    print(
        "🚀 STARTING BACKGROUND SERVICES"
    )

    # --------------------------------------------
    # TELEGRAM
    # --------------------------------------------

    telegram_thread = threading.Thread(

        target=telegram_polling,

        daemon=True,

        name="TelegramPolling"

    )

    telegram_thread.start()

    print(
        "✅ Telegram thread started"
    )


# ============================================================
# START SERVICES WHEN GUNICORN IMPORTS APP
# ============================================================

start_background_services()


# ============================================================
# LOCAL SERVER
# ============================================================

if __name__ == "__main__":

    port = int(

        os.environ.get(
            "PORT",
            10000
        )

    )

    app.run(

        host="0.0.0.0",

        port=port
    )
