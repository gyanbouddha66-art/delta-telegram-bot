import os
import time
import threading
import streamlit as st
import ccxt
import requests
from google import genai
import streamlit.components.v1 as components

# --- 1. CONFIGURATIONS ---
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # अपना Telegram Bot Token डालें
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"              # अपनी Chat ID डालें
GEMINI_API_KEY = "AQ.Ab8RN6LRNq3mOnbnzB3T3Yny8Uskk7DRpOajm6ssmHXavzPYAg"

DELTA_API_KEY = "nHv2Al08t6Bd8O1KSGBXCHP2ZbpmP3"
DELTA_API_SECRET = "tCTPHxKcZxZ2wvk9oMyFrgDRkTK37ryjRNDM6Lhkt6neE2MfIkv9lL5vW8se"

SYMBOL = 'BTC/USDT:USDT'  # ट्रेडिंग पेयर
AMOUNT = 1.0              # ट्रेड साइज
CHECK_INTERVAL = 60       # हर 1 मिनट में BOSS मार्केट एनालाइज करेगा

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def send_telegram_message(message):
    """Telegram पर तुरंत अलर्ट भेजने के लिए"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def boss_autonomous_trading_loop():
    """यह बैकग्राउंड लूप बिना किसी फिक्स कंडीशन के खुद AI से पूछकर ट्रेड लेगा"""
    print(f"🚀 BOSS Autonomous AI Bot शुरू हो गया है... Symbol: {SYMBOL}")
    send_telegram_message("🚀 *BOSS AI* पूरी तरह एक्टिव हो गया है और अब खुद मार्केट एनालाइज करके ट्रेड लेगा!")

    try:
        exchange = ccxt.delta({
            'apiKey': DELTA_API_KEY,
            'secret': DELTA_API_SECRET,
            'enableRateLimit': True,
        })
    except Exception as e:
        print(f"❌ Exchange Init Error: {e}")
        return

    while True:
        try:
            # 1. लेटेस्ट प्राइस और कैंडल डेटा फेच करना
            ticker = exchange.fetch_ticker(SYMBOL)
            current_price = ticker['last']
            ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe='1h', limit=20)
            
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}] [BOSS-AI] Analyzing {SYMBOL} at Price: {current_price}...")

            # 2. BOSS (Gemini AI) से खुद डिसीजन मांगना
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
            print(f"🧠 BOSS Analysis: {decision_text}")

            # 3. AI के डिसीजन के आधार पर खुद एक्शन लेना
            if "[ACTION: BUY]" in decision_text:
                order = exchange.create_order(symbol=SYMBOL, type='market', side='buy', amount=AMOUNT)
                msg = f"✅ *BOSS ने खुद BUY ट्रेड ले लिया!*\n- Price: {current_price}\n- Analysis: {decision_text[:100]}"
                send_telegram_message(msg)
            elif "[ACTION: SELL]" in decision_text:
                order = exchange.create_order(symbol=SYMBOL, type='market', side='sell', amount=AMOUNT)
                msg = f"🚨 *BOSS ने खुद SELL ट्रेड ले लिया!*\n- Price: {current_price}\n- Analysis: {decision_text[:100]}"
                send_telegram_message(msg)
            else:
                # HOLD की स्थिति में सिर्फ लॉग रखेगा, फालतू ट्रेड नहीं लेगा
                print("⏳ BOSS says: Market safe nahi hai, HOLD kar rahe hain.")

        except Exception as e:
            print(f"❌ [BOSS-AI Error]: {e}")
            
        time.sleep(CHECK_INTERVAL)

# Background Thread शुरू करना
@st.cache_resource
def start_boss_background_thread():
    t = threading.Thread(target=boss_autonomous_trading_loop, daemon=True)
    t.start()
    return "Started"

start_boss_background_thread()


# --- 2. STREAMLIT WEB APP UI ---
st.set_page_config(page_title="BOSS AI - Autonomous Trader", page_icon="⚡", layout="wide")
st.title("⚡ BOSS Autonomous AI - Fully Self-Governed Crypto Bot")
st.success("✅ BOSS अब बिना किसी बंदिश के, खुद मार्केट देखकर अपने दम पर ट्रेड लेने की मोड में आ गया है!")
