import os
import time
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Delta API Credentials
DELTA_API_KEY      = "UvOmLQABY3ppqe83KcPCWvfTxLkD8c"
DELTA_API_SECRET   = "05YCaLlNEM1C7qTxBGLYSICFsiP0viEv6g3zQILtLYguaPIgYF4DSJSJBpFP"

WEBHOOK_PASSPHRASE = os.environ.get("WEBHOOK_PASSPHRASE", "MY_SUPER_SECRET_123")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")

# POSITION & TRAILING CONFIGURATION
FIXED_LOT_SIZE = 20    # 20 Lots
LEVERAGE       = 5     # 5x Leverage
SL_AMOUNT      = 7.5   # 25% Stop Loss (Initial)
TRAIL_VALUE    = 7.5   # Trailing SL Steps (7.5 पॉइंट्स पर खिसकेगा)
TP_AMOUNT      = 15.0  # 50% Take Profit

def generate_signature(method, endpoint, payload_str, timestamp):
    """Delta Exchange Signature Generator"""
    signature_data = method + timestamp + endpoint + payload_str
    return hmac.new(
        DELTA_API_SECRET.encode('utf-8'),
        signature_data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def send_telegram_msg(message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print("Telegram Error:", str(e))

def set_leverage(symbol, leverage_value):
    """5x Leverage Setup"""
    endpoint = "/v2/products/leverage"
    url = "https://api.delta.exchange" + endpoint
    timestamp = str(int(time.time()))
    
    payload = {
        "product_symbol": symbol,
        "leverage": str(leverage_value)
    }
    
    import json
    payload_str = json.dumps(payload)
    signature = generate_signature("POST", endpoint, payload_str, timestamp)
    
    headers = {
        "api-key": DELTA_API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "Content-Type": "application/json"
    }
    requests.post(url, data=payload_str, headers=headers)

@app.route('/', methods=['GET'])
def home():
    return "Render Delta Engine Active | 5x Leverage + Trailing SL Enabled", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No Payload"}), 400

    if data.get('secret') != WEBHOOK_PASSPHRASE:
        return jsonify({"status": "unauthorized"}), 401

    symbol = data.get('symbol', 'BTCUSD')
    action = data.get('action') # 'buy' or 'sell'
    size   = int(data.get('size', FIXED_LOT_SIZE))

    try:
        # 1. Set 5x Leverage
        set_leverage(symbol, LEVERAGE)

        # 2. Bracket Order with Trailing SL
        endpoint = "/v2/orders"
        url = "https://api.delta.exchange" + endpoint
        timestamp = str(int(time.time()))

        payload = {
            "product_symbol": symbol,
            "size": size,
            "side": action,
            "order_type": "market_order",
            "bracket_stop_loss_limit_price": str(SL_AMOUNT),
            "bracket_stop_loss_trail_value": str(TRAIL_VALUE), # Trailing SL Activated
            "bracket_take_profit_limit_price": str(TP_AMOUNT)
        }

        import json
        payload_str = json.dumps(payload)
        signature = generate_signature("POST", endpoint, payload_str, timestamp)

        headers = {
            "api-key": DELTA_API_KEY,
            "timestamp": timestamp,
            "signature": signature,
            "Content-Type": "application/json"
        }

        res = requests.post(url, data=payload_str, headers=headers)
        order_res = res.json()

        if res.status_code in [200, 201]:
            tg_text = (
                f"🔥 <b>DELTA TRAILING ORDER EXECUTED</b>\n\n"
                f"<b>Action:</b> {action.upper()}\n"
                f"<b>Symbol:</b> {symbol}\n"
                f"<b>Size:</b> {size} Lots (5x)\n"
                f"<b>Trailing SL:</b> Enabled (₹7.5)\n"
                f"<b>Target TP:</b> ₹15.0 ✅"
            )
            send_telegram_msg(tg_text)
            return jsonify({"status": "success", "order": order_res}), 200
        else:
            raise Exception(str(order_res))

    except Exception as e:
        error_msg = f"🔴 <b>ORDER FAILED</b>\n\n<b>Error:</b> {str(e)}"
        send_telegram_msg(error_msg)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
