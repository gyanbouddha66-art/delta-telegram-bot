# ============================================================
# GH BOSS AI — FINAL STABLE POLLING BOT (`app.py`)
# ============================================================

import os
import time
import threading
import requests
from flask import Flask
from telegram_bot import process_command, process_voice, handle_callback_query

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

def run_telegram_polling():
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN is missing!")
        return

    print("🤖 GH BOSS AI Telegram Polling Started Successfully...")
    offset = 0
    
    # सबसे पहले पुराना कोई भी फंसा हुआ वेबहुक साफ़ कर देते हैं ताकि पोलिंग बिना रुकावट चले
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=10)
    except Exception:
        pass

    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=30"
            res = requests.get(url, timeout=35)
            
            if res.ok:
                data = res.json()
                for result in data.get("result", []):
                    offset = result["update_id"] + 1
                    
                    # 1. यदि बटन क्लिक किया गया है
                    if "callback_query" in result:
                        cq = result["callback_query"]
                        chat_id = cq["message"]["chat"]["id"]
                        callback_data = cq["data"]
                        handle_callback_query(chat_id, callback_data)
                    
                    # 2. यदि टेक्स्ट मैसेज या कमांड भेजी गई है
                    elif "message" in result:
                        msg = result["message"]
                        chat_id = msg["chat"]["id"]
                        
                        if "voice" in msg:
                            file_id = msg["voice"]["file_id"]
                            process_voice(chat_id, file_id)
                        elif "text" in msg:
                            text = msg["text"]
                            process_command(chat_id, text)
            
        except Exception as e:
            print("❌ Polling Loop Error:", e)
            time.sleep(3)

@app.route("/", methods=["GET"])
def index():
    return "GH BOSS AI Polling Server is Live and Running 🟢", 200

if __name__ == "__main__":
    # बैकग्राउंड थ्रेड में पोलिंग लूप शुरू करें ताकि Flask पोर्ट बाइंडिंग प्रभावित न हो
    t = threading.Thread(target=run_telegram_polling)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
