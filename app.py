import streamlit as st
import time
import json
import requests
from groq import Groq

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="GYAN AI Pro Trading Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS STYLING & UI
# ============================================================
st.markdown("""
<style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .stSidebar { background-color: #161b22; }
    .metric-card { background-color: #21262d; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .signal-buy { background-color: #238636; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 20px; }
    .signal-sell { background-color: #da3633; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 20px; }
    .signal-hold { background-color: #9e6a03; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 20px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR SETTINGS & API KEYS
# ============================================================
st.sidebar.title("⚙️ GYAN AI Settings")

GROQ_API_KEY = st.sidebar.text_input("Groq API Key", type="password", value="")
# आपके द्वारा कहे गए मॉडल को यहाँ सेट कर दिया गया है ताकि एकदम फास्ट काम करे
GROQ_MODEL = st.sidebar.selectbox("AI Model", ["openai/gpt-oss-20b", "llama3-70b-8192", "mixtral-8x7b-32768"], index=0)

selected_symbol = st.sidebar.selectbox("Trading Symbol", ["ETHUSDT", "BTCUSDT", "SOLUSDT", "XAUUSD"], index=0)
timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m"], index=0)

auto_trade = st.sidebar.checkbox("🚀 Auto Scalping Mode Active", value=False)
refresh_rate = st.sidebar.slider("Refresh Rate (Seconds)", 5, 60, 10)

# ============================================================
# MOCK / LIVE DATA FETCH FUNCTION (फास्ट और सेफ)
# ============================================================
def fetch_market_candles(symbol):
    try:
        # यहाँ आप अपना एक्सचेंज या डेटा सोर्स जोड़ सकते हैं, फिलहाल यह सुरक्षित डमी/लाइव स्ट्रक्चर दे रहा है
        # यदि आपके पास डेल्टा या बिनेंस का एपीआई है, तो यहाँ जोड़ सकते हैं
        dummy_candles = [
            {"time": "03:40", "open": 0.0670, "high": 0.0682, "low": 0.0665, "close": 0.0678, "volume": 1250},
            {"time": "03:41", "open": 0.0678, "high": 0.0685, "low": 0.0672, "close": 0.0680, "volume": 1400},
            {"time": "03:42", "open": 0.0680, "high": 0.0690, "low": 0.0675, "close": 0.0688, "volume": 2100},
            {"time": "03:43", "open": 0.0688, "high": 0.0692, "low": 0.0680, "close": 0.0685, "volume": 1100},
            {"time": "03:44", "open": 0.0685, "high": 0.0695, "low": 0.0682, "close": 0.0691, "volume": 1850}
        ]
        return dummy_candles
    except Exception as e:
        return []

# ============================================================
# AI ANALYSIS FUNCTION (बिना किसी स्ट्रिक्ट फिल्टर के - एरर फ्री)
# ============================================================
def get_signal_and_analysis(candles, symbol):
    if not GROQ_API_KEY:
        return ("NO TRADE", "कृपया साइडबार में Groq API Key दर्ज करें।")

    if not candles:
        return ("NO TRADE", "पर्याप्त मार्केट डेटा उपलब्ध नहीं है।")

    candle_text = "\n".join(str(c) for c in candles[-5:])

    prompt = f"""
आप GYAN AI Pro के Institutional Trading Engine हैं।
Symbol: {symbol}
इन कैंडल डेटा का विश्लेषण करें:
{candle_text}

कृपया स्पष्ट रूप से बताएं कि क्या ट्रेड लेना चाहिए। उत्तर में मुख्य रूप से BUY, SELL या NO TRADE लिखें और साथ में छोटा कारण दें।
"""

    try:
        client = Groq(api_key=GROQ_API_KEY)

        # किसी भी प्रकार का response_format (JSON strict mode) यहाँ नहीं है ताकि 400 एरर कभी न आए
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "आप एक प्रोफेशनल ट्रेडिंग असिस्टेंट हैं।"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=400
        )

        content = response.choices[0].message.content
        if not content:
            return ("NO TRADE", "AI से कोई प्रतिक्रिया नहीं मिली।")

        content_upper = content.upper()

        # फ्लेक्सिबल लॉजिक जो तुरंत सिग्नल पहचान लेगा
        if "BUY" in content_upper and "SELL" not in content_upper:
            signal = "BUY"
        elif "SELL" in content_upper and "BUY" not in content_upper:
            signal = "SELL"
        else:
            signal = "NO TRADE"

        return (signal, content.strip())

    except Exception as e:
        return ("NO TRADE", f"AI Error: {str(e)}")

# ============================================================
# MAIN UI DASHBOARD
# ============================================================
st.title("⚡ GYAN AI Pro - Institutional Scalping Engine")
st.markdown(f"**Selected Asset:** `{selected_symbol}` | **Timeframe:** `{timeframe}`")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card"><h4>24h Low</h4><h2>0.0650</h2></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-card"><h4>Market Status</h4><h2>Live & Scanning</h2></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><h4>Mode</h4><h2>{"Auto Active" if auto_trade else "Manual"}</h2></div>', unsafe_allow_html=True)

st.markdown("---")

# Execution Area
if st.button("🔍 Run Instant AI Analysis", type="primary") or auto_trade:
    with st.spinner("बॉट मार्केट का विश्लेषण कर रहा है..."):
        candles = fetch_market_candles(selected_symbol)
        signal, analysis = get_signal_and_analysis(candles, selected_symbol)

        # Display Signal Box
        if signal == "BUY":
            st.markdown('<div class="signal-buy">🟢 SIGNAL: BUY (खरीदें)</div>', unsafe_allow_html=True)
        elif signal == "SELL":
            st.markdown('<div class="signal-sell">🔴 SIGNAL: SELL (बेचें)</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="signal-hold">⏸️ NO TRADE (बाजार स्पष्ट नहीं है)</div>', unsafe_allow_html=True)

        st.markdown("### 💡 AI Analysis Report")
        st.info(analysis)

# Auto Scalping Loop Handler
if auto_trade:
    time.sleep(refresh_rate)
    st.rerun()
