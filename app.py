# ============================================================
# MAIN APPLICATION (`app.py`)
# ============================================================

import os
from flask import Flask, request, jsonify
from telegram_bot import process_command, handle_callback_query, process_voice

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "GH BOSS AI Trading Bot is Running Successfully!", 200

@app.route(f"/webhook/{os.getenv('TELEGRAM_BOT_TOKEN', 'secret')}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error"}), 400

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        
        if "text" in msg:
            text = msg["text"]
            process_command(text, chat_id)
        elif "voice" in msg:
            file_id = msg["voice"]["file_id"]
            process_voice(file_id, chat_id)

    elif "callback_query" in data:
        cq = data["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        callback_data = cq["data"]
        handle_callback_query(callback_data, chat_id)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
