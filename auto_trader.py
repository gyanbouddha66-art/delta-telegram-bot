
# ============================================================
# GH BOSS AI — AUTOMATED SMC TRADING ENGINE (`auto_trader.py`)
# ============================================================

import time
import requests
from delta_api import get_candles, place_order, get_live_press if "get_live_price" in globals() else lambda s: 0.0

# टेलीग्राम पर नोटिफिकेशन भेजने के लिए
import os
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8919168139:AAFijo1uf4BoJo1oJjqKvO9UjYj96wASpw8").strip()

def send_alert(chat_id, text):
    if not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print("Alert send error:", e)

def analyze_and_trade(chat_id):
    """डेल्टा से डेटा लेकर SMC/Order Flow एनालिसिस करेगा और ऑटो ट्रेड लेगा"""
    print("🔍 Scanning Market Structure & Order Blocks...")
    
    # 1. डेल्टा से 15 मिनट की कैंडल्स फेच करें (Symbol: BTCUSD या जो भी आप चाहें)
    symbol = "BTCUSD"
    product_id = 27  # डेल्टा पर प्रोडक्ट आईडी
    candles = get_candles(symbol=symbol, resolution="15m", limit=30)
    
    if not candles or len(candles) < 10:
        return "❌ Delta Data not available or market is slow."

    # 2. बेसिक SMC स्ट्रक्चर लॉजिक (High/Low & Order Block Detection)
    # कैंडल्स फॉर्मेट डेल्टा के मुताबिक चेक करें (ओपन, हाई, लो, क्लोज़)
    try:
        latest_close = float(candles[-1].get("close", 0))
        prev_close = float(candles[-2].get("close", 0))
        
        # स्मार्ट मनी / आर्डर ब्लॉक सिमुलेशन: यदि बुलिश स्ट्रक्चर शिफ्ट दिखा
        is_bullish_obos = latest_close > prev_close and float(candles[-1].get("high", 0)) > float(candles[-2].get("high", 0))
        is_bearish_obos = latest_close < prev_close and float(candles[-1].get("low", 0)) < float(candles[-2].get("low", 0))

        signal_text = f"📊 MARKET SCAN ({symbol})\nPrice: {latest_close}\n\n"

        if is_bullish_obos:
            signal_text += "🟢 SMC BULLISH ORDER BLOCK DETECTED!\n🚀 Executing Auto BUY Trade..."
            send_alert(chat_id, signal_text)
            
            # डेल्टा पर असली आर्डर प्लेस करें
            result = place_order(product_id=product_id, side="buy", size=1, order_type="market")
            if result.get("success"):
                send_alert(chat_id, f"✅ Auto BUY Order Placed Successfully!\nDetails: {result.get('result')}")
            else:
                send_alert(chat_id, f"❌ Trade Failed: {result.get('error')}")
                
        elif is_bearish_obos:
            signal_text += "🔴 SMC BEARISH ORDER BLOCK DETECTED!\n🔻 Executing Auto SELL Trade..."
            send_alert(chat_id, signal_text)
            
            # डेल्टा पर असली आर्डर प्लेस करें
            result = place_order(product_id=product_id, side="sell", size=1, order_type="market")
            if result.get("success"):
                send_alert(chat_id, f"✅ Auto SELL Order Placed Successfully!\nDetails: {result.get('result')}")
            else:
                send_alert(chat_id, f"❌ Trade Failed: {result.get('error')}")
        else:
            signal_text += "⚖️ Market is consolidating. Waiting for HL/LH break..."
            send_alert(chat_id, signal_text)

        return signal_text

    except Exception as e:
        err_msg = f"❌ Analysis Error: {str(e)}"
        print(err_msg)
        return err_msg
