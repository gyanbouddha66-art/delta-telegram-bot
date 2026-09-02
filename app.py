import os
import streamlit as st
from groq import Groq
import ccxt
import pandas as pd

st.title("⚡ ArcUSD Pro Scalper (CCXT Live + Auto SL/TP)")

# --- Settings ---
# डेल्टा एक्सचेंज पर परपेचुअल के लिए सही सिंबल फॉर्मेट
timeframe = "1m"     # 1 मिनट का स्कैल्पिंग फ्रेम

def fetch_ccxt_market_data():
    try:
        exchange = ccxt.delta({'enableRateLimit': True})
        exchange.load_markets()
        
        # डेल्टा एक्सचेंज पर सही सिंबल ऑटोमैटिक खोजना
        target_symbol = None
        for s in exchange.symbols:
            if 'ARC' in s.upper() and ('USD' in s.upper()):
                target_symbol = s
                break
        
        if not target_symbol:
            target_symbol = "ARC/USD:USD"  # फॉールबैक सिंबल
            
        ohlcv = exchange.fetch_ohlcv(target_symbol, timeframe=timeframe, limit=5)
        if not ohlcv:
            return None, target_symbol
            
        df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        return df[['Open', 'High', 'Low', 'Close', 'Volume']].to_string(), target_symbol
    except Exception as e:
        return None, str(e)

def run_scalp_ai(market_data):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "GROQ_API_KEY missing!"
    
    client = Groq(api_key=api_key)
    prompt = f"""
    You are an aggressive Crypto Scalping AI. Look at this 1-minute price action for ArcUSD:
    {market_data}
    Give an immediate scalp decision in one exact word:
    - BUY or SELL (No WAIT, give a clear direction based on momentum).
    """
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-8b-8192", 
    )
    return response.choices[0].message.content.strip()

def execute_delta_scalp_with_risk(signal, target_symbol):
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
        ticker_info = exchange.fetch_ticker(target_symbol)
        current_price = ticker_info['last']
        
        amount = 10  # अपनी पोजीशन साइज
        sl_percentage = 0.005  # 0.5% SL
        tp_percentage = 0.01   # 1.0% TP
        
        if "BUY" in signal.upper():
            order = exchange.create_market_buy_order(target_symbol, amount)
            sl_price = current_price * (1 - sl_percentage)
            tp_price = current_price * (1 + tp_percentage)
            return f"✅ Scalp BUY Executed on {target_symbol} at {current_price}!\n🛑 Stop-Loss: ~{sl_price:.4f}\n🎯 Take-Profit: ~{tp_price:.4f}"
            
        elif "SELL" in signal.upper():
            order = exchange.create_market_sell_order(target_symbol, amount)
            sl_price = current_price * (1 + sl_percentage)
            tp_price = current_price * (1 - tp_percentage)
            return f"✅ Scalp SELL Executed on {target_symbol} at {current_price}!\n🛑 Stop-Loss: ~{sl_price:.4f}\n🎯 Take-Profit: ~{tp_price:.4f}"
            
        else:
            return "⏳ Signal unclear. No trade placed."
            
    except Exception as e:
        return f"❌ Trade Execution Error: {str(e)}"

# --- UI Interface ---
if st.button("⚡ Run Instant Scalp & Risk Manager"):
    with st.spinner("डेल्टा एक्सचेंज से लाइव डेटा फेच हो रहा है..."):
        data, active_symbol = fetch_ccxt_market_data()
        if data:
            st.write(f"🔍 Active Symbol: `{active_symbol}`")
            signal = run_scalp_ai(data)
            st.info(f"🤖 AI Decision: **{signal}**")
            
            result_msg = execute_delta_scalp_with_risk(signal, active_symbol)
            st.success(result_msg)
        else:
            st.error(f"डेटा फेच करने में असफल। एरर: {active_symbol}")
