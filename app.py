# ============================================================
# GH BOSS AI — MAIN FLASK APP (`app.py`)
# ============================================================

import os
from flask import Flask, request
from telegram_bot import process_command, process_voice, handle_callback_query

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            data = request.json
            if not data:
                return "OK", 200

            # 1. यदि यूजर ने कोई Inline Button दबाया है (जैसे BUY, SELL, Mode Toggle)
            if "callback_query" in data:
                cq = data["callback_query"]
                chat_id = cq["message"]["chat"]["id"]
                callback_data = cq["data"]
                
                # यहाँ से बटन का डेटा सीधा telegram_bot.py के फंक्शन में जाएगा
                handle_callback_query(chat_id, callback_data)
                return "OK", 200

            # 2. यदि यूजर ने कोई टेक्स्ट मैसेज या कमांड भेजा है
            if "message" in data:
                msg = data["message"]
                chat_id = msg["chat"]["id"]
                
                # वॉयस मैसेज चेक करें
                if "voice" in msg:
                    file_id = msg["voice"]["file_id"]
                    process_voice(chat_id, file_id)
                
                # सामान्य टेक्स्ट या कमांड चेक करें (/start, /signal आदि)
                elif "text" in msg:
                    text = msg["text"]
                    process_command(chat_id, text)

            return "OK", 200
        except Exception as e:
            print("❌ Webhook Error:", e)
            return "OK", 200

    return "GH BOSS AI Server is Live and Running 🟢", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
