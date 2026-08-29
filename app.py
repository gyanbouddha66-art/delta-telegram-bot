from flask import Flask, request, jsonify
import os

from telegram_bot import process_command
from delta_api import test_delta

app = Flask(__name__)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return jsonify({
        "system": "GH AI TRADING",
        "status": "ONLINE",
        "mode": "TEST",
        "live_trading": False
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():
    return jsonify({
        "status": "OK",
        "service": "GH AI TRADING"
    }), 200


# ============================================================
# SYSTEM STATUS
# ============================================================

@app.route("/status")
def status():

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_key = os.getenv("GEMINI_API_KEY")
    delta_key = os.getenv("DELTA_API_KEY")
    delta_secret = os.getenv("DELTA_API_SECRET")

    return jsonify({
        "server": "ONLINE",

        "telegram": bool(
            telegram_token
        ),

        "gemini": bool(
            gemini_key
        ),

        "delta_key": bool(
            delta_key
        ),

        "delta_secret": bool(
            delta_secret
        ),

        "delta": bool(
            delta_key and delta_secret
        ),

        "live_trading": False
    }), 200


# ============================================================
# DELTA AUTHENTICATION TEST
# READ ONLY — NO ORDER
# ============================================================

@app.route("/delta-test")
def delta_test():

    result = test_delta()

    return jsonify(result), 200


# ============================================================
# TELEGRAM WEBHOOK
# ============================================================

@app.route("/telegram", methods=["POST"])
def telegram_webhook():

    data = request.get_json(
        silent=True
    ) or {}

    message = data.get(
        "message",
        {}
    )

    chat = message.get(
        "chat",
        {}
    )

    text = message.get(
        "text"
    )

    chat_id = chat.get(
        "id"
    )

    if chat_id and text:

        process_command(
            chat_id,
            text
        )

    return jsonify({
        "ok": True
    }), 200


# ============================================================
# RUN SERVER
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
