import os
import requests
from flask import Flask, request, jsonify
from delta_rest_client import DeltaRestClient

app = Flask(__name__)

# ============================================================
# DELTA EXCHANGE API KEYS (ADDED DIRECTLY)
# ============================================================
DELTA_API_KEY      = "UvOmLQABY3ppqe83KcPCWvfTxLkD8c"
DELTA_API_SECRET   = "05YCaLlNEM1C7qTxBGLYSICFsiP0viEv6g3zQILtLYguaPIgYF4DSJSJBpFP"

# Optional: Environment Variables fallback
WEBHOOK_PASSPHRASE = os.environ.get("WEBHOOK_PASSPHRASE", "MY_SUPER_SECRET_123")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")

# Delta Client Setup
delta_client = DeltaRestClient(
    base_url='https://api.delta.exchange',
    api_key=DELTA_API_KEY,
    api_secret=DELTA_API_SECRET
)

def send_telegram_msg(message):
    """Telegram Alert Helper"""
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print("Telegram Error:", str(e))

@app.route('/', methods=['GET'])
def home():
    return "Render Delta Bot is Active!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No Payload"}), 400

    # Security Passphrase Check
    if data.get('secret') != WEBHOOK_PASSPHRASE:
        return jsonify({"status": "unauthorized"}), 401

    symbol = data.get('symbol', 'BTCUSD')
    action = data.get('action')  # 'buy' or 'sell'
    size   = int(data.get('size', 1))

    try:
        # Executing Order directly on Delta Exchange
        order_res = delta_client.place_order(
            product_symbol=symbol,
            size=size,
            side=action,
            order_type='market_order'
        )
        
        # Telegram Notification
        tg_text = f"🟢 <b>ORDER EXECUTED</b>\n\n<b>Action:</b> {action.upper()}\n<b>Symbol:</b> {symbol}\n<b>Size:</b> {size} Lot(s)"
        send_telegram_msg(tg_text)

        print(f"Executed: {action.upper()} {symbol}")
        return jsonify({"status": "success", "order": order_res}), 200

    except Exception as e:
        error_msg = f"🔴 <b>ORDER FAILED</b>\n\n<b>Error:</b> {str(e)}"
        send_telegram_msg(error_msg)
        print("Execution Error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
