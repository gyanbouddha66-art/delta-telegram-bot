from flask import Flask, jsonify
import os
import time
import threading
import requests

from telegram_bot import (
    process_command,
    process_voice
)

from delta_api import test_delta


# ============================================================
# GH BOSS AI — APP
# TELEGRAM + GROQ + DELTA + VOICE
# SINGLE POLLING WORKER
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIG
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    ""
).strip()

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    ""
).strip()


# ============================================================
# GLOBAL POLLING LOCK
# ============================================================

_polling_started = False
_polling_lock = threading.Lock()


# ============================================================
# TELEGRAM SEND
# ============================================================

def telegram_send(text, chat_id=None):

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        ""
    ).strip()

    target_chat = (
        chat_id
        if chat_id is not None
        else TELEGRAM_CHAT_ID
    )

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN missing")
        return False

    if not target_chat:
        print("❌ TELEGRAM_CHAT_ID missing")
        return False

    try:

        response = requests.post(

            f"https://api.telegram.org/"
            f"bot{token}/sendMessage",

            json={
                "chat_id": target_chat,
                "text": str(text)
            },

            timeout=20
        )

        print(
            "Telegram SEND:",
            response.status_code,
            response.text[:300]
        )

        return response.ok

    except Exception as e:

        print(
            "❌ TELEGRAM SEND ERROR:",
            e
        )

        return False


# ============================================================
# TELEGRAM CONNECTION TEST
# ============================================================

def telegram_connection_test():

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        ""
    ).strip()

    if not token:

        print(
            "❌ TELEGRAM_BOT_TOKEN missing"
        )

        return False

    try:

        response = requests.get(

            f"https://api.telegram.org/"
            f"bot{token}/getMe",

            timeout=20
        )

        print(
            "Telegram getMe:",
            response.status_code
        )

        if not response.ok:
            return False

        data = response.json()

        if not data.get("ok"):
            return False

        bot = data.get(
            "result",
            {}
        )

        print(
            "✅ TELEGRAM CONNECTED"
        )

        print(
            "BOT:",
            bot.get("username")
        )

        return True

    except Exception as e:

        print(
            "❌ TELEGRAM CONNECTION ERROR:",
            e
        )

        return False


# ============================================================
# DELETE WEBHOOK
# ============================================================

def remove_webhook():

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        ""
    ).strip()

    if not token:
        return False

    try:

        response = requests.get(

            f"https://api.telegram.org/"
            f"bot{token}/deleteWebhook",

            params={
                "drop_pending_updates": False
            },

            timeout=20
        )

        print(
            "Webhook removal:",
            response.status_code
        )

        return response.ok

    except Exception as e:

        print(
            "❌ WEBHOOK ERROR:",
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
    ).strip()

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

            params = {
                "timeout": 30
            }

            if offset is not None:

                params["offset"] = offset

            response = requests.get(

                f"https://api.telegram.org/"
                f"bot{token}/getUpdates",

                params=params,

                timeout=40
            )

            data = response.json()

            if not data.get("ok"):

                print(
                    "❌ Telegram API error:",
                    data
                )

                # 409 के बाद थोड़ी देर रुकें
                if data.get(
                    "error_code"
                ) == 409:

                    print(
                        "⚠️ Another polling process "
                        "is using this bot token."
                    )

                    time.sleep(10)

                else:

                    time.sleep(5)

                continue

            updates = data.get(
                "result",
                []
            )

            for update in updates:

                update_id = update.get(
                    "update_id"
                )

                if update_id is not None:

                    offset = update_id + 1

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

                if not chat_id:
                    continue

                # ====================================================
                # CHAT SECURITY
                # ====================================================

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

                # ====================================================
                # VOICE MESSAGE
                # ====================================================

                voice = message.get(
                    "voice"
                )

                if voice:

                    file_id = voice.get(
                        "file_id"
                    )

                    if file_id:

                        print(
                            "🎤 VOICE RECEIVED"
                        )

                        try:

                            process_voice(
                                chat_id,
                                file_id
                            )

                        except Exception as e:

                            print(
                                "❌ VOICE ERROR:",
                                e
                            )

                            telegram_send(
                                "❌ Voice processing error\n\n"
                                + str(e),
                                chat_id
                            )

                    continue

                # ====================================================
                # TEXT MESSAGE
                # ====================================================

                text = message.get(
                    "text"
                )

                if text is None:
                    continue

                text = str(
                    text
                ).strip()

                if not text:
                    continue

                print(
                    "📩 MESSAGE:",
                    text
                )

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
                        "❌ COMMAND ERROR:",
                        e
                    )

                    telegram_send(
                        "❌ Command processing error:\n"
                        + str(e),
                        chat_id
                    )

        except requests.exceptions.Timeout:

            print(
                "⏱️ Telegram polling timeout"
            )

            continue

        except Exception as e:

            print(
                "❌ POLLING ERROR:",
                e
            )

            time.sleep(5)


# ============================================================
# START POLLING ONLY ONCE
# ============================================================

def start_telegram_polling():

    global _polling_started

    with _polling_lock:

        if _polling_started:

            print(
                "⚠️ Telegram polling already started"
            )

            return

        _polling_started = True

    thread = threading.Thread(

        target=telegram_polling,

        daemon=True,

        name="TelegramPolling"

    )

    thread.start()

    print(
        "✅ Telegram polling thread started"
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return jsonify({

        "system":
        "GH BOSS AI TRADING",

        "status":
        "ONLINE",

        "telegram":
        (
            "CONFIGURED"
            if TELEGRAM_BOT_TOKEN
            else "MISSING"
        ),

        "telegram_mode":
        "POLLING",

        "voice":
        "ENABLED",

        "ai":
        (
            "GROQ"
            if GROQ_API_KEY
            else "GROQ KEY MISSING"
        ),

        "delta":
        (
            "CONFIGURED"
            if (
                os.getenv(
                    "DELTA_API_KEY"
                )
                and
                os.getenv(
                    "DELTA_API_SECRET"
                )
            )
            else
            "MISSING"
        ),

        "execution":
        "CONFIRMATION REQUIRED"

    })


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status":
        "OK",

        "telegram_polling":
        _polling_started,

        "voice":
        True,

        "ai":
        "GROQ",

        "delta":
        True,

        "execution":
        "CONFIRMATION REQUIRED"

    })


# ============================================================
# STATUS
# ============================================================

@app.route("/status")
def status():

    return jsonify({

        "server":
        "ONLINE",

        "telegram_token":
        bool(
            os.getenv(
                "TELEGRAM_BOT_TOKEN",
                ""
            ).strip()
        ),

        "telegram_chat_id":
        bool(
            os.getenv(
                "TELEGRAM_CHAT_ID",
                ""
            ).strip()
        ),

        "groq_api_key":
        bool(
            os.getenv(
                "GROQ_API_KEY",
                ""
            ).strip()
        ),

        "delta_key":
        bool(
            os.getenv(
                "DELTA_API_KEY",
                ""
            ).strip()
        ),

        "delta_secret":
        bool(
            os.getenv(
                "DELTA_API_SECRET",
                ""
            ).strip()
        ),

        "telegram_polling":
        _polling_started,

        "voice_input":
        True,

        "voice_reply":
        True,

        "gemini":
        False,

        "execution":
        "CONFIRMATION REQUIRED"

    })


# ============================================================
# DELTA TEST
# ============================================================

@app.route("/delta-test")
def delta_test():

    try:

        result = test_delta()

        return jsonify(
            result
        ), 200

    except Exception as e:

        return jsonify({

            "success":
            False,

            "error":
            str(e)

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

            "error":
            str(e)

        }), 500


# ============================================================
# START TELEGRAM
# ============================================================

def start_background_services():

    print(
        "=========================================="
    )

    print(
        "🚀 GH BOSS AI STARTING"
    )

    print(
        "=========================================="
    )

    remove_webhook()

    telegram_connection_test()

    start_telegram_polling()


# ============================================================
# START
# ============================================================

start_background_services()


# ============================================================
# LOCAL / RENDER SERVER
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
