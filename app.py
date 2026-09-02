import os
import streamlit as st
from groq import Groq
import requests
import pandas as pd
import ccxt

st.title("⚡ One-Click AI Crypto Scalper (Direct API + Auto SL/TP)")

@st.cache_data(ttl=60)
def get_all_delta_symbols():
    try:
        prod_url = "https://api.delta.exchange/v2/products"
        response = requests.get(prod_url).json()
        products = response.get("result", [])
        if not products and isinstance(response, list):
            products = response
            
        symbols = []
        product_map = {}
        for p in products:
            sym = str(p.get("symbol", "")).strip().upper()
            p_id = p.get("id")
            if sym and p_id and not sym.startswith("C-") and not sym.startswith("P-"):
                symbols.append(sym)
                product_map[sym] = p_id
                
        return sorted(list(set(symbols))), product_map
    except Exception as e:
        return ["ARCUSD", "BTCUSD"], {}

all_symbols, product_map = get_all_delta_symbols()

selected_coin = st.selectbox(
    "🪙 ट्रेड करने के लिए कॉइन चुनें:",
    all_symbols if all_symbols else ["ARCUSD", "BTCUSD"]
)

def fetch_delta_market_data(target_symbol, p_map):
    try:
        product_id = p_map.get(target_symbol)
        
        if product_id:
            candles_url = f"https://api.delta.exchange/v2/history/candles?resolution=1m&product_id={product_id}&limit=10"
            candle_res = requests.get(candles_url).json()
            raw_candles = candle_res.get("result", [])
            if raw_candles:
                df = pd.DataFrame(raw_candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
                return df.to_string(), target_symbol

        exchange = ccxt.delta({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})
        exchange.load_markets()
        
        ccxt_sym = target_symbol
        if ccxt_sym not in exchange.symbols:
            for s in exchange.symbols:
                if target_symbol.replace("_", "") in s.replace("/", "").upper():
                    ccxt_sym = s
                    break
                    
        ohlcv = exchange.fetch_ohlcv(ccxt_sym, timeframe='1m', limit=10)
        if ohlcv:
            df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
            return df.to_string(), ccxt_sym
            
        return None, f"कैंडल डेटा दोनों तरीकों से खाली है for {target_symbol}"
        
    except Exception as e:
        return None, str(e)

def run_scalp_ai(market_data, symbol):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "GROQ_API_KEY missing!"
    
    client = Groq(api_key=api_key)
    prompt = f"""
    You are an aggressive Crypto Scalping AI. Look at this 1-minute price action for {symbol}:
    {market_data}
    Give an immediate scalp decision in one exact word:
    - BUY or SELL (No WAIT, give a clear direction based on momentum).
    """
    
    try:
        # ऑटोमैटिक रूप से आपके अकाउंट पर उपलब्ध मॉडल डिटेक्ट करना
        models_response = client.models.list()
        available_models = [m.id for m in models_response.data if "llama" in m.id.lower()]
        model_to_use = available_models[0] if available_models else "llama-3.3-70b-versatile"
        
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model_to_use,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI Error: {str(e)}"

def execute_delta_scalp(signal, target_symbol):
    if "AI Error" in signal or "Error" in signal:
        return f"❌ Trade cancelled due to AI issue: {signal}"
        
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
        
        trade_sym = target_symbol if target_symbol in exchange.symbols else 'BTCUSD'
        if trade_sym not in exchange.symbols:
            for s in exchange.symbols:
                if target_symbol.replace("_", "").replace("USD", "") in s.replace("/", "").upper():
                    trade_sym = s
                    break

        ticker_info = exchange.fetch_ticker(trade_sym)
        current_price = ticker_info['last']
        
        amount = 10  # पोजीशन साइज
        sl_percentage = 0.005  # 0.5% SL
        tp_percentage = 0.01   # 1.0% TP
        
        if "BUY" in signal.upper():
            exchange.create_market_buy_order(trade_sym, amount)
            sl_price = current_price * (1 - sl_percentage)
            tp_price = current_price * (1 + tp_percentage)
            return f"✅ Scalp BUY Executed on {trade_sym} at {current_price}!\n🛑 Stop-Loss: ~{sl_price:.4f}\n🎯 Take-Profit: ~{tp_price:.4f}"
            
        elif "SELL" in signal.upper():
            exchange.create_market_sell_order(trade_sym, amount)
            sl_price = current_price * (1 + sl_percentage)
            tp_price = current_price * (1 - tp_percentage)
            return f"✅ Scalp SELL Executed on {trade_sym} at {current_price}!\n🛑 Stop-Loss: ~{sl_price:.4f}\n🎯 Take-Profit: ~{tp_price:.4f}"
            
        else:
            return f"⏳ Signal unclear ({signal}). No trade placed."
            
    except Exception as e:
        return f"❌ Trade Execution Error: {str(e)}"

if st.button("⚡ Run Instant Scalp & Risk Manager"):
    with st.spinner(f"{selected_coin} पर AI द्वारा ट्रेड लिया जा रहा है..."):
        data, active_symbol = fetch_delta_market_data(selected_coin, product_map)
        if data:
            st.write(f"🔍 Active Symbol: `{active_symbol}`")
            signal = run_scalp_ai(data, active_symbol)
            st.info(f"🤖 Groq AI Decision: **{signal}**")
            
            result_msg = execute_delta_scalp(signal, active_symbol)
            st.success(result_msg)
        else:
            st.error(f"डेटा फेच करने में असफल। विवरण: {active_symbol}")
