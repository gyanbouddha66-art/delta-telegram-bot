# ============================================================
# GH BOSS AI — DEBUGGABLE & SAFE APP (`app.py`)
# ============================================================

import os
from flask import Flask, request
from telegram_bot import process_command, process_voice, handle_callback_query

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            data = request.json
            print("📥 Incoming Telegram Data:", data)  # यह Render के Logs में दिखेगा!
            
            if not data:
                return "OK", 200

            # बटन क्लिक हैंडल करें
            if "callback_query" in data:
                cq = data["callback_query"]
                chat_id = cq["message"]["chat"]["id"]
                callback_data = cq["data"]
                handle_callback_query(chat_id, callback_data)
                return "OK", 200

            # मैसेज या कमांड हैंडल करें
            if "message" in data:
                msg = data["message"]
                chat_id = msg["chat"]["id"]
                
                if "voice" in msg:
                    file_id = msg["voice"]["file_id"]
                    process_voice(chat_id, file_id)
                elif "text" in msg:
                    text = msg["text"]
                    process_command(chat_id, text)

            return "OK", 200
        except Exception as e:
            print("❌ CRITICAL WEBHOOK ERROR:", str(e))
            return "OK", 200

    return "GH BOSS AI Server is Live and Running 🟢", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
