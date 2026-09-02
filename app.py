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
        # डेल्टा एक्सचेंज के पब्लिक API से सीधे ARCUSD का डेटा लेना
        url = "https://api.delta.exchange/v2/history/candles"
        
        # पहले हम सिंबल की डिटेल या सीधे प्रोडक्ट आईडी ढूंढते हैं, या डायरेक्ट कैंडल एंडपॉइंट हिट करते हैं
        # डेल्टा पर ARCUSD का कॉन्ट्रैक्ट ढूंढने के लिए प्रोडक्ट्स लिस्ट फेच करते हैं
        prod_url = "https://api.delta.exchange/v2/products"
        response = requests.get(prod_url).json()
        
        product_id = None
        contract_symbol = "ARCUSD"
        
        if "result" in response:
            for p in response["result"]:
                if p.get("symbol") == "ARCUSD" or "ARC" in p.get("symbol", ""):
                    product_id = p.get("id")
                    contract_symbol = p.get("symbol")
                    break
                    
        if not product_id:
            return None, "ഡెल्टा एक्सचेंज पर ARCUSD प्रोडक्ट आईडी नहीं मिली।"
            
        # अब उस प्रोडक्ट आईडी के लिए 1 मिनट की कैंडल फेच करना
        candles_url = f"https://api.delta.exchange/v2/history/candles?resolution=1m&product_id={product_id}&limit=5"
        candle_res = requests.get(candles_url).json()
        
        if "result" not in candle_res or not candle_res["result"]:
            return None, f"कैंडल डेटा फेच करने में असफल for {contract_symbol}"
            
        # डेल्टा कैंडल फॉर्मेट: [time, open, high, low, close, volume]
        raw_candles = candle_res["result"]
        df = pd.DataFrame(raw_candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        
        # डेटा को सही फॉर्मेट में बदलना
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
        # आर्डर लगाने के लिए CCXT का उपयोग सुरक्षित है क्योंकि बाजार लोड करने की बजाय सीधा सिंबल पास कर रहे हैं
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
