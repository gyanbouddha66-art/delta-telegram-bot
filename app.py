import os
import streamlit as st
from groq import Groq
import requests
import pandas as pd
import ccxt

st.title("⚡ One-Click AI Crypto Scalper (All Coins + Live Data Fix + Auto SL/TP)")

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
            # डेल्टा के सभी ट्रेडिंग सिम्बल्स (ARCUSD, BTC, ETH आदि) को शामिल करें
            if sym and p_id and not sym.startswith("C-") and not sym.startswith("P-"):
                symbols.append(sym)
                product_map[sym] = p_id
                
        return sorted(list(set(symbols))), product_map
    except Exception as e:
        return ["ARCUSD", "BTCUSD", "ETH_USDT"], {}

# डेल्टा के सभी कॉइन लोड करना
all_symbols, product_map = get_all_delta_symbols()

selected_coin = st.selectbox(
    "🪙 डेल्टा एक्सचेंज के सभी कॉइन (ARCUSD सहित) में से चुनें:",
    all_symbols if all_symbols else ["ARCUSD", "BTCUSD", "ETH_USDT"]
)

def fetch_delta_market_data(target_symbol, p_map):
    try:
        product_id = p_map.get(target_symbol)
        
        # 1. पहले डेल्टा REST API से कैंडल फेच करें
        if product_id:
            candles_url = f"https://api.delta.exchange/v2/history/candles?resolution=1m&product_id={product_id}&limit=15"
            candle_res = requests.get(candles_url).json()
            raw_candles = candle_res.get("result", [])
            if raw_candles:
                df = pd.DataFrame(raw_candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
                # यदि डेटा फ्लैट (समान) है तो सीसीXT का उपयोग करें
                if df['Close'].nunique() > 1:
                    return df, target_symbol

        # 2. CCXT के ज़रिए लाइव ओएचएलसीवी (OHLCV) डेटा फेच करें
        exchange = ccxt.delta({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})
        exchange.load_markets()
        
        ccxt_sym = target_symbol
        if ccxt_sym not in exchange.symbols:
            for s in exchange.symbols:
                if target_symbol.replace("_", "").upper() in s.replace("/", "").upper():
                    ccxt_sym = s
                    break
                    
        ohlcv = exchange.fetch_ohlcv(ccxt_sym, timeframe='1m', limit=15)
        if ohlcv:
            df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
            return df, ccxt_sym
            
        return None, f"कैंडल डेटा खाली है for {target_symbol}"
        
    except Exception as e:
        return None, str(e)

def run_scalp_ai(market_data_str, symbol):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "BUY"
    
    client = Groq(api_key=api_key)
    prompt = f"""
    You are an aggressive Crypto Scalping AI. Look at this 1-minute price action for {symbol}:
    {market_data_str}
    Give an immediate scalp decision in one exact word:
    - BUY or SELL (No WAIT, give a clear direction based on momentum).
    """
    
    models_to_try = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-70b-8192"
    ]
    
    for model_name in models_to_try:
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            continue
            
    return "BUY"

def execute_delta_scalp(signal, target_symbol):
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
                if target_symbol.replace("_", "").replace("USD", "").upper() in s.replace("/", "").upper():
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
    with st.spinner(f"{selected_coin} का लाइव डेटा और एनालिसिस लोड हो रहा है..."):
        df_data, active_symbol = fetch_delta_market_data(selected_coin, product_map)
        
        if df_data is not None and isinstance(df_data, pd.DataFrame):
            st.write(f"🔍 Active Symbol: `{active_symbol}`")
            
            st.subheader("📊 Live Market Data & Price Action Analysis")
            st.dataframe(df_data)
            
            market_data_str = df_data.to_string()
            signal = run_scalp_ai(market_data_str, active_symbol)
            st.info(f"🤖 Groq AI Decision: **{signal}**")
            
            result_msg = execute_delta_scalp(signal, active_symbol)
            if "invalid_api_key" in result_msg:
                st.error("🚨 आपकी Delta API Key गलत है! कृपया Render Dashboard में जाकर सही Delta API Key और Secret डालें।")
            else:
                st.success(result_msg)
        else:
            st.error(f"डेटा फेच करने में असफल। विवरण: {active_symbol}")
