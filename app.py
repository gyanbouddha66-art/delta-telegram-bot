from flask import Flask, jsonify
import os
import time
import threading
import requests

from telegram_bot import process_command, process_voice
from delta_api import test_delta


# ============================================================
# GH BOSS AI — APP
# GROQ + TELEGRAM + DELTA + VOICE
# GEMINI REMOVED
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
# TELEGRAM SEND
# ============================================================

def telegram_send(text, chat_id=None):

    try:

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
                "text": str(text)
            },

            timeout=15
        )

        print(
            "Telegram SEND:",
            response.status_code,
            response.text[:500]
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
    ).strip()

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

        print(
            response.text[:500]
        )

        return False

    except Exception as e:

        print(
            "❌ TELEGRAM TEST ERROR:",
            e
        )

        return False


# ============================================================
# REMOVE WEBHOOK
# ============================================================

def remove_webhook():

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        ""
    ).strip()

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
            response.text[:500]
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
# TEXT + VOICE
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

                # ============================================
                # UPDATE OFFSET
                # ============================================

                offset = (
                    update.get(
                        "update_id",
                        0
                    ) + 1
                )

                print(
                    "🔥 TELEGRAM UPDATE RECEIVED"
                )

                # ============================================
                # MESSAGE
                # ============================================

                message = update.get(
                    "message"
                )

                if not message:

                    continue

                # ============================================
                # CHAT
                # ============================================

                chat = message.get(
                    "chat",
                    {}
                )

                chat_id = chat.get(
                    "id"
                )

                if not chat_id:

                    continue

                print(
                    "👤 CHAT ID:",
                    chat_id
                )

                # ============================================
                # CHAT SECURITY
                # ============================================

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

                # ============================================
                # VOICE MESSAGE
                # ============================================

                voice = message.get(
                    "voice"
                )

                if voice:

                    file_id = voice.get(
                        "file_id"
                    )

                    if not file_id:

                        print(
                            "❌ Voice file_id missing"
                        )

                        telegram_send(

                            "❌ Voice file नहीं मिला।",

                            chat_id
                        )

                        continue

                    print(
                        "🎤 VOICE MESSAGE RECEIVED"
                    )

                    print(
                        "🎤 FILE ID:",
                        file_id
                    )

                    try:

                        result = process_voice(

                            chat_id,

                            file_id

                        )

                        print(
                            "VOICE RESULT:",
                            result
                        )

                    except Exception as e:

                        print(
                            "❌ process_voice ERROR:",
                            e
                        )

                        telegram_send(

                            "❌ Voice processing error:\n"
                            + str(e),

                            chat_id
                        )

                    continue

                # ============================================
                # TEXT MESSAGE
                # ============================================

                text = message.get(
                    "text",
                    ""
                )

                text = str(
                    text
                ).strip()

                if not text:

                    continue

                print(
                    "📩 MESSAGE:",
                    text
                )

                # ============================================
                # PROCESS TEXT COMMAND
                # ============================================

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

        "system":
        "GH BOSS AI TRADING",

        "status":
        "ONLINE",

        "telegram":
        (
            "CONFIGURED"
            if TELEGRAM_BOT_TOKEN
            else
            "MISSING"
        ),

        "telegram_mode":
        "POLLING",

        "text_chat":
        "ENABLED",

        "voice_input":
        "ENABLED",

        "voice_reply":
        "ENABLED",

        "ai":
        (
            "GROQ"
            if GROQ_API_KEY
            else
            "GROQ KEY MISSING"
        ),

        "voice_stt":
        "GROQ WHISPER",

        "voice_tts":
        "EDGE-TTS",

        "gemini":
        "REMOVED",

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
        )

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
        True,

        "text_chat":
        True,

        "voice_input":
        True,

        "voice_reply":
        True,

        "ai":
        "GROQ",

        "voice_stt":
        "GROQ WHISPER",

        "voice_tts":
        "EDGE-TTS",

        "gemini":
        False

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

        "gemini":
        False,

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

        "telegram_mode":
        "POLLING",

        "text_chat":
        "ENABLED",

        "voice_input":
        "ENABLED",

        "voice_reply":
        "ENABLED",

        "voice_stt":
        "GROQ WHISPER",

        "voice_tts":
        "EDGE-TTS"

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

            "ok":
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
# START BACKGROUND SERVICES
# ============================================================

def start_background_services():

    print(
        "🚀 STARTING BACKGROUND SERVICES"
    )

    # ========================================
    # REMOVE WEBHOOK
    # ========================================

    remove_webhook()

    # ========================================
    # TELEGRAM CONNECTION TEST
    # ========================================

    telegram_connection_test()

    # ========================================
    # TELEGRAM POLLING THREAD
    # ========================================

    telegram_thread = threading.Thread(

        target=telegram_polling,

        daemon=True,

        name="TelegramPolling"

    )

    telegram_thread.start()

    print(
        "✅ Telegram thread started"
    )

    print(
        "🎤 Voice input enabled"
    )

    print(
        "🔊 Voice reply enabled"
    )


# ============================================================
# START SERVICES
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
