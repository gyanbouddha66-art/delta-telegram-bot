# ============================================================
# GH BOSS AI — TELEGRAM BOT MODULE (`telegram_bot.py`)
# ============================================================

import os
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8919168139:AAFijo1uf4BoJo1oJjqKvO9UjYj96wASpw8").strip()
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

def send_message(chat_id, text):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("❌ Send message error:", e)

def send_message_with_keyboard(chat_id, text):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🟢 BUY (Long)", "callback_data": "BUY_SIGNAL"},
                    {"text": "🔴 SELL (Short)", "callback_data": "SELL_SIGNAL"}
                ],
                [
                    {"text": "📊 Check Status", "callback_data": "STATUS"},
                    {"text": "⚡ AI Signal", "callback_data": "AI_SIGNAL"}
                ]
            ]
        }
        payload = {
            "chat_id": chat_id, 
            "text": text, 
            "reply_markup": keyboard
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("❌ Keyboard message error:", e)
        send_message(chat_id, text)

def command_start(chat_id):
    try:
        msg = (
            "🧠 GH BOSS AI — SMART TRADING SYSTEM\n\n"
            "⚙️ Status: System Connected & Ready\n"
            "🚀 Select an option below to control trading:"
        )
        send_message_with_keyboard(chat_id, msg)
    except Exception as e:
        print("❌ Start Command Error:", e)
        send_message(chat_id, "🟢 GH BOSS AI is Online and Running!")

def process_command(chat_id, text):
    text = text.strip().lower()
    print(f"📥 Received command from user: {text}")
    
    if text == "/start" or text == "start":
        command_start(chat_id)
    elif text == "/signal" or text == "signal":
        send_message(chat_id, "📊 Analyzing market structure and order blocks...")
    else:
        send_message(chat_id, f"🤖 Command received: {text}. Type /start to see menu.")

def handle_callback_query(chat_id, callback_data):
    print(f"🔘 Button clicked: {callback_data}")
    if callback_data == "BUY_SIGNAL":
        send_message(chat_id, "🚀 BUY order signal triggered via button!")
    elif callback_data == "SELL_SIGNAL":
        send_message(chat_id, "🔻 SELL order signal triggered via button!")
    elif callback_data == "STATUS":
        send_message(chat_id, "🟢 System is Active and Monitoring Delta Exchange.")
    elif callback_data == "AI_SIGNAL":
        send_message(chat_id, "⚡ AI is scanning SMC & Order Flow...")
    else:
        send_message(chat_id, f"⚙️ Action processed: {callback_data}")

def process_voice(chat_id, file_id):
    send_message(chat_id, "🎙️ Voice note received! Processing audio command...")
