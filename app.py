# ============================================================
# GH BOSS AI — MAIN FLASK APP (`app.py`)
# ============================================================

import os
import requests
from flask import Flask, request
from telegram_bot import process_command, process_voice, handle_callback_query

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# 1. ब्राउज़र से एक क्लिक में वेबहुक सेट करने का राउट
@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    if not TOKEN:
        return "❌ TELEGRAM_BOT_TOKEN is missing in Environment Variables!", 400
    
    # Render का लाइव URL अपने आप ले लेगा
    render_url = request.host_url.rstrip('/')
    
    webhook_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={render_url}"
    try:
        res = requests.get(webhook_url, timeout=10)
        return f"🟢 Webhook Response: {res.text} <br> 🔗 Set URL: {render_url}"
    except Exception as e:
        return f"❌ Error setting webhook: {str(e)}", 500

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            data = request.json
            if not data:
                return "OK", 200

            # बटन क्लिक हैंडल करने के लिए
            if "callback_query" in data:
                cq = data["callback_query"]
                chat_id = cq["message"]["chat"]["id"]
                callback_data = cq["data"]
                handle_callback_query(chat_id, callback_data)
                return "OK", 200

            # मैसेज या कमांड हैंडल करने के लिए
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
            print("❌ Webhook Error:", e)
            return "OK", 200

    return "GH BOSS AI Server is Live and Running 🟢", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
