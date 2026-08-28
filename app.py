import os
import time
import threading
from flask import Flask
import ccxt
import requests
from google import genai

# --- 1. CONFIGURATIONS ---
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"              
GEMINI_API_KEY = "AQ.Ab8RN6LRNq3mOnbnzB3T3Yny8Uskk7DRpOajm6ssmHXavzPYAg"

DELTA_API_KEY = "nHv2Al08t6Bd8O1KSGBXCHP2ZbpmP3"
DELTA_API_SECRET = "tCTPHxKcZxZ2wvk9oMyFrgDRkTK37ryjRNDM6Lhkt6neE2MfIkv9lL5vW8se"

SYMBOL = 'ARCUSD'         
AMOUNT = 1.0              
CHECK_INTERVAL = 60       

# Initialize Gemini Client safely
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# --- 2. FLASK APP (Render Web Service के लिए) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "⚡ BOSS Autonomous AI Trading Engine is Live & Running 24/7!"

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- 3. THE 24/7 BOSS TRADING LOOP ---
def boss_autonomous_trading_loop():
    print("🚀 BOSS Background Engine Started...")
    
    # Safe Exchange Initialization inside thread
    try:
        exchange = ccxt.delta({
            'apiKey': DELTA_API_KEY,
            'secret': DELTA_API_SECRET,
            'enableRateLimit': True,
        })
    except Exception as e:
        print(f"❌ Exchange Init Error: {e}")
        exchange = None

    while True:
        if exchange:
            try:
                print("[BOSS-AI] Scanning Market...")
                ticker = exchange.fetch_ticker(SYMBOL)
                current_price = ticker['last']
                
                ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe='1h', limit=20)
                
                prompt = (
                    f"You are BOSS, an elite autonomous crypto trading AI. Current market data for {SYMBOL}: "
                    f"Current Price is {current_price}. Recent candles (OHLCV): {ohlcv[-5:]}. "
                    "Analyze the market completely based on Smart Money Concepts, price action, and momentum. "
                    "Decide if we should take a trade right now. "
                    "If a trade is strictly necessary, output ONLY in this exact format at the end: "
                    "[ACTION: BUY] or [ACTION: SELL]. If no trade is safe, output [ACTION: HOLD]."
                )

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                decision_text = response.text
                print(f"AI Decision: {decision_text}")

                if "[ACTION: BUY]" in decision_text:
                    exchange.create_order(symbol=SYMBOL, type='market', side='buy', amount=AMOUNT)
                    send_telegram_message(f"✅ *BOSS ने खुद BUY ट्रेड लिया!*\n- Symbol: {SYMBOL}\n- Price: {current_price}")
                elif "[ACTION: SELL]" in decision_text:
                    exchange.create_order(symbol=SYMBOL, type='market', side='sell', amount=AMOUNT)
                    send_telegram_message(f"🚨 *BOSS ने खुद SELL ट्रेड लिया!*\n- Symbol: {SYMBOL}\n- Price: {current_price}")
                
            except Exception as e:
                print(f"❌ Loop Error / API issue: {e}")
                
        time.sleep(CHECK_INTERVAL)

# Start background thread automatically when app boots up
def start_background_thread():
    t = threading.Thread(target=boss_autonomous_trading_loop, daemon=True)
    t.start()

# Call the thread starter
start_background_thread()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
