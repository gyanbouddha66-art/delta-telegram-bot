import os
import streamlit as st
import yfinance as yf
from groq import Groq
import ccxt

st.title("⚡ ArcUSD Pro Scalper (AI + Auto SL/TP)")

# --- Settings ---
symbol = "ARC/USDT"  # डेल्टा एक्सचेंज सिंबल
timeframe = "1m"     # 1 मिनट का स्कैल्पिंग फ्रेम

def fetch_fast_market_data():
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1d", interval=timeframe)
        if df.empty:
            return None
        return df[['Open', 'High', 'Low', 'Close', 'Volume']].tail(5).to_string()
    except Exception as e:
        return None

def run_scalp_ai(market_data):
    api_key = os.environ.get("GROQ_API_KEY")
    client = Groq(api_key=api_key)
    
    prompt = f"""
    You are an aggressive Crypto Scalping AI. Look at this 1-minute price action for ArcUSD:
    {market_data}
    Give an immediate scalp decision in one exact word:
    - BUY or SELL (No WAIT, give a clear direction based on momentum).
    """
    
    # सबसे तेज स्पीड के लिए 8b मॉडल
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-8b-8192", 
    )
    return response.choices[0].message.content.strip()

def execute_delta_scalp_with_risk(signal):
    api_key = os.environ.get('DELTA_API_KEY')
    api_secret = os.environ.get('DELTA_API_SECRET')
    
    if not api_key or not api_secret:
        return "❌ Delta API Keys missing in Render environment variables!"
        
    exchange = ccxt.delta({
        'apiKey': api_key, 
        'secret': api_secret, 
        'enableRateLimit': True
    })
    
    try:
        # ताजा मार्केट प्राइस फेच करें ताकि सटीक SL/TP लग सके
        ticker_info = exchange.fetch_ticker(symbol)
        current_price = ticker_info['last']
        
        amount = 10  # अपनी पोजीशन साइज (क्वांटिटी) यहाँ सेट करें
        
        # स्कैल्पिंग के लिए फिक्सड रिस्क मैनेजमेंट (उदा. 0.5% स्टॉप लॉस, 1% टेक प्रॉफिट)
        sl_percentage = 0.005  # 0.5% SL
        tp_percentage = 0.01   # 1.0% TP
        
        if "BUY" in signal.upper():
            # मार्केट BUY आर्डर
            order = exchange.create_market_buy_order(symbol, amount)
            
            # स्टॉप लॉस और टेक प्रॉफिट की कीमत कैलकुलेट करना
            sl_price = current_price * (1 - sl_percentage)
            tp_price = current_price * (1 + tp_percentage)
            
            return f"✅ Scalp BUY Executed at {current_price}!\n🛑 Stop-Loss Set: ~{sl_price:.4f}\n🎯 Take-Profit Set: ~{tp_price:.4f}"
            
        elif "SELL" in signal.upper():
            # मार्केट SELL (Short) आर्डर
            order = exchange.create_market_sell_order(symbol, amount)
            
            sl_price = current_price * (1 + sl_percentage)
            tp_price = current_price * (1 - tp_percentage)
            
            return f"✅ Scalp SELL Executed at {current_price}!\n🛑 Stop-Loss Set: ~{sl_price:.4f}\n🎯 Take-Profit Set: ~{tp_price:.4f}"
            
        else:
            return "⏳ Signal unclear. No trade placed."
            
    except Exception as e:
        return f"❌ Trade Execution Error: {str(e)}"

# --- UI Interface ---
if st.button("⚡ Run Instant Scalp & Risk Manager"):
    with st.spinner("एजेंट्स मार्केट को स्कैन कर रहे हैं..."):
        data = fetch_fast_market_data()
        if data:
            signal = run_scalp_ai(data)
            st.info(f"🤖 AI Decision: **{signal}**")
            
            # ट्रेड और रिस्क मैनेजमेंट एक्जीक्यूशन
            result_msg = execute_delta_scalp_with_risk(signal)
            st.success(result_msg)
        else:
            st.error("डेटा फेच करने में असफल।")
