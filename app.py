# ============================================================
# FLASK WEB SERVER (`app.py`)
# ============================================================

from flask import Flask, request
from telegram_bot import process_command, handle_callback_query, process_voice

app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def index():
    return "GH BOSS AI Trading Bot is Running Live! 🚀", 200

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.json
        if not data:
            return "OK", 200
        
        print("📥 Incoming Telegram Data:", data)
        
        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")
            if text:
                process_command(text, chat_id)
            elif "voice" in msg:
                process_voice(msg["voice"]["file_id"], chat_id)
                
        elif "callback_query" in data:
            cb = data["callback_query"]
            chat_id = cb["message"]["chat"]["id"]
            callback_data = cb.get("data", "")
            handle_callback_query(callback_data, chat_id)
            
        return "OK", 200
    except Exception as e:
        print(f"❌ CRITICAL WEBHOOK ERROR: {str(e)}")
        return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
