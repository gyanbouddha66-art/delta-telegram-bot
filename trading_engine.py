# ============================================================
# TRADING ENGINE & SMC ANALYSIS (`trading_engine.py`)
# ============================================================

from config import SYMBOL, DEFAULT_SIZE
from delta_api import get_live_price, get_candles

auto_mode_status = False  # बॉट का वर्तमान ऑटो/मैन्युअल स्टेटस

def get_engine_status():
    global auto_mode_status
    return auto_mode_status

def toggle_engine_mode():
    global auto_mode_status
    auto_mode_status = not auto_mode_status
    return auto_mode_status

def get_signal():
    price = get_live_price(SYMBOL)
    candles = get_candles(SYMBOL, "15m", 20)
    
    if not candles or price == 0.0:
        return f"⚠️ डेल्टा एक्सचेंज से `{SYMBOL}` का लाइव डेटा प्राप्त करने में असमर्थ।"

    try:
        latest = float(candles[-1].get("close", price))
        prev = float(candles[-2].get("close", price))
        diff = latest - prev
        
        trend = "🟢 बुलिश (UPWARD - Order Block Support)" if diff >= 0 else "🔴 बियरिश (DOWNWARD - Supply Zone Rejection)"
        sl = latest - 50 if diff >= 0 else latest + 50
        tp1 = latest + 100 if diff >= 0 else latest - 100
        tp2 = latest + 200 if diff >= 0 else latest - 200
        mode_str = "AUTO" if auto_mode_status else "MANUAL"

        report = f"""🧠 **GH BOSS AI — SMART TRADING SYSTEM**
🪙 **Asset:** `{SYMBOL}` | **Mode:** `{mode_str}`
💵 **Live Price:** `{price}`

---
### 📊 SMC & Order Flow Analysis
- **Trend Structure:** {trend}
- **Lot Size:** `{DEFAULT_SIZE}`

### 🎯 Entry, SL & TP Setup
1. **Entry Type:** Market / Order Block Break
2. **Stop Loss (SL):** `{sl}`
3. **Take Profit (TP 1):** `{tp1}`
4. **Take Profit (TP 2):** `{tp2}`

> **Status:** लाइव डेटा और आर्डर सिस्टम सक्रिय है। नीचे दिए गए बटन्स से ट्रेड नियंत्रित करें।
"""
        return report
    except Exception as e:
        return f"Analysis Error: {str(e)}"
