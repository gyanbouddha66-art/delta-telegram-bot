import os
import json
import requests
import ccxt
from flask import Flask, request
import google.generativeai as genai

# ============================================================
# CONFIG & API KEYS
# ============================================================

TELEGRAM_BOT_TOKEN = "8919168139:AAFijo1uf4BoJo1oJjqKvO9UjYj96wASpw8"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

GEMINI_API_KEY = "AQ.Ab8RN6LBu4eJ5cIdWMqexsllbvZ2Wc3aKnMlclgM-wuoOF2mFg"

DELTA_API_KEY = "nHv2Al08t6Bd8O1KSGBXCHP2ZbpmP3"
DELTA_API_SECRET = "tCTPHxKcZxZ2wvk9oMyFrgDRkTK37ryjRNDM6Lhkt6neE2MfIkv9lL5vW8se"

SYMBOL = "ARCUSD"

# ============================================================
# FLASK & GEMINI INIT
# ============================================================

app = Flask(__name__)

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-1.5-flash"

# ============================================================
# DELTA EXCHANGE SETUP
# ============================================================

def create_exchange():
    if not DELTA_API_KEY or not DELTA_API_SECRET:
        return None
    return ccxt.delta({
        "apiKey": DELTA_API_KEY,
        "secret": DELTA_API_SECRET,
        "enableRateLimit": True
    })

# ============================================================
# TRADING & EXECUTION FUNCTIONS
# ============================================================

def execute_trade(symbol, side, amount):
    exchange = create_exchange()
    if not exchange:
        return "⚠️ Delta Exchange API Keys missing!"
    try:
        exchange.load_markets()
        order = exchange.create_order(symbol=symbol, type='market', side=side.lower(), amount=amount)
        price = float(order.get('price') or exchange.fetch_ticker(symbol)['last'])
        return f"✅ **BOSS Trade Executed!**\n- Side: {side.upper()}\n- Symbol: {symbol}\n- Price: {price}"
    except Exception as e:
        return f"❌ Execution Error: {e}"

def close_all_positions():
    exchange = create_exchange()
    if not exchange:
        return "⚠️ Exchange not connected!"
    try:
        exchange.load_markets()
        positions = exchange.fetch_positions()
        closed = 0
        for p in positions:
            contracts = float(p.get('contracts', 0))
            if contracts > 0:
                sym = p['symbol']
                side = 'sell' if p['side'].lower() in ['long', 'buy'] else 'buy'
                exchange.create_order(symbol=sym, type='market', side=side, amount=contracts)
                closed += 1
        return f"🚨 **Emergency Close!** Closed {closed} positions."
    except Exception as e:
        return f"❌ Close Error: {e}"

# ============================================================
# TELEGRAM SENDER
# ============================================================

def telegram_send(text, chat_id=None):
    try:
        target = chat_id if chat_id else TELEGRAM_CHAT_ID
        if not TELEGRAM_BOT_TOKEN or not target:
            return False
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": target, "text": text}, timeout=15)
        return response.ok
    except Exception as e:
        print("Telegram error:", e)
        return False

# ============================================================
# BOSS AI AGENT CORE (Fixed Authentication)
# ============================================================

def run_boss_agent(user_input):
    system_prompt = (
        "Your name is BOSS. You are an ultra-intelligent AI trading companion with elite expertise in crypto SMC and Order Flow. "
        "Speak exclusively in natural, powerful Hindi / Hinglish. "
        "If a trade action is required, output your thought process and strictly include the trigger at the very end in this format:\n"
        "[ACTION: BUY, SYMBOL: ARCUSD, AMOUNT: 1.0]\n"
        "Or: [ACTION: SELL, SYMBOL: ARCUSD, AMOUNT: 1.0]\n"
        "Or: [ACTION: CLOSE_ALL]"
    )
    
    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_prompt
        )
        response = model.generate_content(user_input)
        return response.text.strip()
    except Exception as e:
        return f"AI Error: {e}"

# ============================================================
# WEBHOOK ROUTE FOR TELEGRAM
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return "⚡ BOSS AI Backend is Running Successfully!"

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json()
        if not update or "message" not in update:
            return "OK", 200

        message = update["message"]
        chat_id = str(message["chat"]["id"])
        text = message.get("text", "").strip()

        if not text:
            return "OK", 200

        print(f"🔥 Message from {chat_id}: {text}")

        if text.lower() == "/start":
            telegram_send(f"🟢 BOSS AI Online!\nYour Chat ID: {chat_id}", chat_id)
            return "OK", 200

        if text.lower() == "/closeall":
            result = close_all_positions()
            telegram_send(result, chat_id)
            return "OK", 200

        # Run AI Agent
        ai_reply = run_boss_agent(text)
        
        # Check for actions
        if "[ACTION:" in ai_reply:
            action_part = ai_reply.split("[ACTION:")[1].split("]")[0]
            clean_reply = ai_reply.split("[ACTION:")[0].strip()
            telegram_send(clean_reply, chat_id)
            
            # Parse actions
            if "CLOSE_ALL" in action_part:
                res = close_all_positions()
                telegram_send(res, chat_id)
            else:
                items = action_part.split(",")
                parts = {}
                for item in items:
                    if ":" in item:
                        k, v = item.split(":", 1)
                        parts[k.strip().upper()] = v.strip()
                
                action = parts.get("ACTION", "").upper()
                symbol = parts.get("SYMBOL", SYMBOL).upper()
                amount = float(parts.get("AMOUNT", 1.0))
                
                if action in ["BUY", "SELL"]:
                    res = execute_trade(symbol, action, amount)
                    telegram_send(res, chat_id)
        else:
            telegram_send(ai_reply, chat_id)

    except Exception as e:
        print("Webhook error:", e)

    return "OK", 200

# ============================================================
# MAIN RUNNER
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
