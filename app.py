from flask import Flask, request, jsonify
import os

from telegram_bot import process_command

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "system": "GH AI TRADING",
        "status": "ONLINE",
        "mode": "TEST"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "OK"
    }), 200


@app.route("/status")
def status():
    return jsonify({
        "server": "ONLINE",
        "live_trading": False,
        "telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "delta": bool(
            os.getenv("DELTA_API_KEY")
            and os.getenv("DELTA_API_SECRET")
        )
    }), 200


@app.route("/telegram", methods=["POST"])
def telegram_webhook():

    data = request.get_json(silent=True) or {}

    message = data.get("message", {})
    chat = message.get("chat", {})
    text = message.get("text")

    chat_id = chat.get("id")

    if chat_id and text:
        process_command(chat_id, text)

    return jsonify({
        "ok": True
    })


if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
