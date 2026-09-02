import os
import streamlit as st
from groq import Groq
import requests
import pandas as pd
import ccxt

st.title("⚡ ArcUSD Pro Scalper (Direct API + Auto SL/TP)")

timeframe = "1m"

def fetch_delta_market_data():
    try:
        prod_url = "https://api.delta.exchange/v2/products"
        response = requests.get(prod_url).json()
        
        product_id = None
        contract_symbol = "ARCUSD"
        
        products = response.get("result", [])
        if not products and isinstance(response, list):
            products = response
            
        # सभी प्रोडक्ट्स में 'ARC' को सिंबल, बेस एसेट या डिसक्रिप्शन में खोजना
        for p in products:
            sym = str(p.get("symbol", "")).upper()
            base = str(p.get("base_asset", "")).upper()
            desc = str(p.get("description", "")).upper()
            
            if "ARC" in sym or "ARC" in base or "ARC" in desc:
                product_id = p.get("id")
                contract_symbol = p.get("symbol", "ARCUSD")
                break
                
        if not product_id:
            return None, f"डेल्टा पर ARC आधारित प्रोडक्ट नहीं मिला। (कुल प्रोडक्ट्स: {len(products)})"
            
        candles_url = f"https://api.delta.exchange/v2/history/candles?resolution=1m&product_id={product_id}&limit=5"
        candle_res = requests.get(candles_url).json()
        
        raw_candles = candle_res.get("result", [])
        if not raw_candles:
            return None, f"कैंडल डेटा खाली है for product_id: {product_id}"
            
        df = pd.DataFrame(raw_candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
        return df.to_string(), contract_symbol
        
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

def execute_delta_scalp_with_ccxt(signal, target_symbol):
    api_key = os.environ.get('DELTA_API_KEY')
    api_secret = os.environ.get('DELTA_API_SECRET')
    
    if not api_key or not api_secret:
        return "❌ Delta API Keys missing in Render environment variables!"
        
    try:
        exchange = ccxt.delta({
            'apiKey': api_key, 
            'secret': api_secret, 
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })
        exchange.load_markets()
        
        ticker_info = exchange.fetch_ticker(target_symbol)
        current_price = ticker_info['last']
        
        amount = 10  # पोजीशन साइज
        sl_percentage = 0.005  # 0.5% SL
        tp_percentage = 0.01   # 1.0% TP
        
        if "BUY" in signal.upper():
            exchange.create_market_buy_order(target_symbol, amount)
            sl_price = current_price * (1 - sl_percentage)
            tp_price = current_price * (1 + tp_percentage)
            return f"✅ Scalp BUY Executed on {target_symbol} at {current_price}!\n🛑 Stop-Loss: ~{sl_price:.4f}\n🎯 Take-Profit: ~{tp_price:.4f}"
            
        elif "SELL" in signal.upper():
            exchange.create_market_sell_order(target_symbol, amount)
            sl_price = current_price * (1 + sl_percentage)
            tp_price = current_price * (1 - tp_percentage)
            return f"✅ Scalp SELL Executed on {target_symbol} at {current_price}!\n🛑 Stop-Loss: ~{sl_price:.4f}\n🎯 Take-Profit: ~{tp_price:.4f}"
            
        else:
            return "⏳ Signal unclear. No trade placed."
            
    except Exception as e:
        return f"❌ Trade Execution Error: {str(e)}"

# --- UI Interface ---
if st.button("⚡ Run Instant Scalp & Risk Manager"):
    with st.spinner("डेल्टा एक्सचेंज डायरेक्ट API से लाइव डेटा फेच हो रहा है..."):
        data, active_symbol = fetch_delta_market_data()
        if data:
            st.write(f"🔍 Active Symbol: `{active_symbol}`")
            signal = run_scalp_ai(data)
            st.info(f"🤖 AI Decision: **{signal}**")
            
            result_msg = execute_delta_scalp_with_ccxt(signal, active_symbol)
            st.success(result_msg)
        else:
            st.error(f"डेटा फेच करने में असफल। विवरण: {active_symbol}")
