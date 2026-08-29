import os
import requests


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def send_message(chat_id, text):
    if not TOKEN:
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text
            },
            timeout=15
        )

        return response.ok

    except Exception:
        return False


def test_message(chat_id):
    return send_message(
        chat_id,
        "🟢 GH AI TRADING\n\nTelegram connection OK."
    )
