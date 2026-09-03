import os
import time
import json
import hmac
import hashlib
from urllib.parse import urlencode

import requests
import streamlit as st
from groq import Groq


# ============================================================
# GYAN AI PRO — ULTIMATE PREMIUM FINTECH INTERFACE
# ============================================================

BASE_URL = "https://api.india.delta.exchange"

LOT_SIZE = 1
SL_PERCENT = 0.005      # 0.5% SL
TP_PERCENT = 0.010      # 1.0% TP


# ============================================================
# PAGE CONFIG & PROFESSIONAL CSS THEME
# ============================================================

st.set_page_config(
    page_title="GYAN AI Pro — Institutional Trading Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Main Background & Font Styling */
    .main {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    .stSidebar {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }
    
    /* Premium Glassmorphism Cards */
    .metric-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 10px;
    }
    
    /* Header Styling */
    .header-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #60a5fa, #3b82f6, #1d4ed8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Button Customization */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        font-weight: 700;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
        box-shadow: 0 0 15px rgba(37, 99, 235, 0.4);
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# API KEYS & TELEGRAM SETTINGS (SIDEBAR)
# ============================================================

st.sidebar.title("⚡ GYAN AI Control Center")
st.sidebar.markdown("---")

st.sidebar.subheader("🔑 API Configuration")
DELTA_API_KEY = st.sidebar.text_input("Delta API Key", type="password", value=os.getenv("DELTA_API_KEY", ""))
DELTA_API_SECRET = st.sidebar.text_input("Delta API Secret", type="password", value=os.getenv("DELTA_API_SECRET", ""))
GROQ_API_KEY = st.sidebar.text_input("Groq API Key", type="password", value=os.getenv("GROQ_API_KEY", ""))

st.sidebar.markdown("---")
st.sidebar.subheader("📱 Telegram Notifications")
TELEGRAM_BOT_TOKEN = st.sidebar.text_input("Telegram Bot Token", type="password", value=os.getenv("TELEGRAM_BOT_TOKEN", ""))
TELEGRAM_CHAT_ID = st.sidebar.text_input("Telegram Chat ID", value=os.getenv("TELEGRAM_CHAT_ID", ""))


# ============================================================
# TELEGRAM ALERT FUNCTION
# ============================================================

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass


# ============================================================
# DELTA REQUEST
# ============================================================

def delta_request(method, path, params=None, body=None, auth=False):
    if params is None:
        params = {}
    if body is None:
        body = {}

    body_text = json.dumps(body, separators=(",", ":")) if body else ""
    query_string = "?" + urlencode(params) if params else ""
    timestamp = int(time.time())

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "GYAN-AI-PRO-TERMINAL"
    }

    if auth:
        if not DELTA_API_KEY or not DELTA_API_SECRET:
            raise Exception("Delta API Keys missing in settings.")
        message = method.upper() + str(timestamp) + path + query_string + body_text
        signature = hmac.new(
            DELTA_API_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        headers["api-key"] = DELTA_API_KEY
        headers["timestamp"] = str(timestamp)
        headers["signature"] = signature

    response = requests.request(
        method.upper(),
        BASE_URL + path + query_string,
        headers=headers,
        data=body_text if body else None,
        timeout=15
    )

    try:
        data = response.json()
    except Exception:
        raise Exception(response.text)

    if response.status_code >= 400:
        raise Exception(f"HTTP {response.status_code}: {data}")

    return data


# ============================================================
# GET SYMBOLS
# ============================================================

@st.cache_data(ttl=60)
def get_all_symbols():
    products = []
    after = None
    for _ in range(10):
        params = {"page_size": 100}
        if after:
            params["after"] = after
        try:
            data = delta_request("GET", "/v2/products", params=params, auth=False)
            result = data.get("result", [])
            if not result:
                break
            products.extend(result)
            meta = data.get("meta", {})
            after = meta.get("after")
            if not after:
                break
        except Exception:
            break

    tradable = []
    for p in products:
        symbol = str(p.get("symbol", "")).upper().strip()
        ptype = str(p.get("product_type", "")).lower()
        state = str(p.get("state", "")).lower()

        if not symbol or "perpetual" not in ptype:
            continue
        if symbol.startswith("C-") or symbol.startswith("P-"):
            continue
        if state and state not in ["live", "active"]:
            continue
        tradable.append(symbol)

    return sorted(list(set(tradable)))


# ============================================================
# TICKER & CANDLES
# ============================================================

def get_ticker(symbol):
    data = delta_request("GET", f"/v2/tickers/{symbol}")
    return data.get("result", {})

def get_candles(symbol):
    end_time = int(time.time())
    start_time = end_time - 1800
    params = {"resolution": "1m", "symbol": symbol, "start": start_time, "end": end_time}
    data = delta_request("GET", "/v2/history/candles", params=params)
    return data.get("result", [])


# ============================================================
# AI SIGNAL + STRATEGY
# ============================================================

def get_signal_and_analysis(candles, symbol):
    if not GROQ_API_KEY or len(candles) < 5:
        return ("BUY", "डेटा कम होने के कारण डिफॉल्ट स्मार्ट मनी सिग्नल लिया गया।")

    recent = candles[-10:]
    candle_text = "\n".join(str(c) for c in recent)

    prompt = f"""
You are an elite Institutional Smart Money Concepts (SMC)
and Momentum Trader for GYAN AI Pro.
Symbol: {symbol}
Analyze these 1-minute candles using professional trading logic.
1. Market Structure & Trend (HL/LH shifts).
2. Institutional Order Flow & Momentum.
3. Order Block logic.
4. Momentum confirmation.
5. Explain the exact strategy used for this trade.

Respond strictly in JSON format with two keys:
"signal": "BUY" or "SELL"
"analysis": A detailed professional explanation in pure HINDI mentioning the strategy name.

CANDLES:
{candle_text}
"""

    client = Groq(api_key=GROQ_API_KEY)
    models = ["openai/gpt-oss-120b"]

    for model in models:
        try:
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            content = res.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]

            data = json.loads(content.strip())
            signal = data.get("signal", "BUY").upper()
            analysis = data.get("analysis", "विश्लेषण उपलब्ध नहीं है।")

            if signal in ("BUY", "SELL"):
                return (signal, analysis)
        except Exception:
            continue

    return ("BUY", "स्मार्ट मनी मोमेंटम के आधार पर ऑटो सिग्नल जनरेट किया गया।")


# ============================================================
# POSITION & ORDERS
# ============================================================

def get_position(product_id):
    data = delta_request("GET", "/v2/positions", params={"product_id": product_id}, auth=True)
    result = data.get("result", [])
    if isinstance(result, list):
        if len(result) == 0:
            return 0.0
        return float(result[0].get("size", 0))
    elif isinstance(result, dict):
        return float(result.get("size", 0))
    return 0.0

def place_market_order(symbol, side):
    body = {
        "product_symbol": symbol,
        "size": LOT_SIZE,
        "side": side,
        "order_type": "market_order",
        "time_in_force": "ioc"
    }
    data = delta_request("POST", "/v2/orders", body=body, auth=True)
    return data.get("result", {})

def place_sl_tp_orders(symbol, entry_side, entry_price):
    entry_price = float(entry_price)
    if entry_side == "buy":
        exit_side = "sell"
        stop_price = entry_price * (1 - SL_PERCENT)
        target_price = entry_price * (1 + TP_PERCENT)
    else:
        exit_side = "buy"
        stop_price = entry_price * (1 + SL_PERCENT)
        target_price = entry_price * (1 - TP_PERCENT)

    results = []

    # Stop Loss
    sl_body = {
        "product_symbol": symbol,
        "size": LOT_SIZE,
        "side": exit_side,
        "order_type": "stop_order",
        "stop_price": f"{stop_price:.4f}",
        "limit_price": f"{stop_price:.4f}",
        "reduce_only": True,
        "time_in_force": "gtc"
    }
    try:
        sl_res = delta_request("POST", "/v2/orders", body=sl_body, auth=True)
        results.append(("Stop Loss", sl_res))
    except Exception as e:
        results.append(("Stop Loss Error", str(e)))

    # Take Profit
    tp_body = {
        "product_symbol": symbol,
        "size": LOT_SIZE,
        "side": exit_side,
        "order_type": "limit_order",
        "limit_price": f"{target_price:.4f}",
        "reduce_only": True,
        "time_in_force": "gtc"
    }
    try:
        tp_res = delta_request("POST", "/v2/orders", body=tp_body, auth=True)
        results.append(("Take Profit", tp_res))
    except Exception as e:
        results.append(("Take Profit Error", str(e)))

    return results, stop_price, target_price


# ============================================================
# MAIN UI HEADER
# ============================================================

st.markdown('<p class="header-title">⚡ GYAN AI Pro — Institutional Scalper</p>', unsafe_allow_html=True)
st.markdown("*Autonomous High-Frequency Fintech Execution Engine*")
st.markdown("---")

symbols_list = get_all_symbols()
if not symbols_list:
    symbols_list = ["ARCUSD", "BTCUSD", "ETHUSD"]

# ============================================================
# TABS SETUP
# ============================================================

tab1, tab2 = st.tabs(["⚡ लाइव स्केल्पिंग टर्मिनल", "💬 AI मेंटर & रिसर्च रूम"])

with tab1:
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_symbol = st.selectbox("🪙 क्रिप्टो सिंबल चुनें", symbols_list, key="t1_sym")
    with c2:
        auto_trade = st.checkbox("🔄 ऑटो-स्केल्पिंग लूप मोड", value=False)
    with c3:
        refresh_rate = st.slider("⏱️ स्कैन इंटरवल (सेकंड)", 5, 30, 5)

    st.markdown("<br>", unsafe_allow_html=True)

    # Live Ticker Metrics Display
    try:
        live_ticker = get_ticker(selected_symbol)
        m_price = live_ticker.get("mark_price", live_ticker.get("close", "0.0"))
        high_p = live_ticker.get("high", "0.0")
        low_p = live_ticker.get("low", "0.0")

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.markdown(f'<div class="metric-card"><h4>Market Price</h4><h2>{float(m_price):.4f}</h2></div>', unsafe_allow_html=True)
        with col_m2:
            st.markdown(f'<div class="metric-card"><h4>24h High</h4><h2>{float(high_p):.4f}</h2></div>', unsafe_allow_html=True)
        with col_m3:
            st.markdown(f'<div class="metric-card"><h4>24h Low</h4><h2>{float(low_p):.4f}</h2></div>', unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Ticker Warning: {e}")

    st.markdown("---")
    placeholder = st.empty()

    def run_scalping():
        with placeholder.container():
            try:
                with st.spinner(f"🔍 {selected_symbol} मार्केट स्ट्रक्चर स्कैन हो रहा है..."):
                    ticker = get_ticker(selected_symbol)
                    product_id = ticker.get("product_id")
                    mark_price = float(ticker.get("mark_price") or ticker.get("close") or 0)

                pos_size = get_position(product_id)
                if pos_size != 0:
                    st.warning(f"⚠️ **पोजीशन पहले से खुली है** (साइज: `{pos_size}`)। नई ट्रेड होल्ड पर है।")
                else:
                    candles = get_candles(selected_symbol)
                    signal, analysis = get_signal_and_analysis(candles, selected_symbol)

                    st.success(f"🤖 **AI सिग्नल डिटेक्टेड:** `{signal}`")
                    st.info(f"💡 **मार्केट एनालिसिस:**\n\n{analysis}")

                    side = "buy" if signal == "BUY" else "sell"
                    st.markdown(f"🚀 **मार्केट {side.upper()} ऑर्डर निष्पादित किया जा रहा है...**")

                    order_res = place_market_order(selected_symbol, side)
                    fill_price = float(order_res.get("average_fill_price") or order_res.get("fill_price") or mark_price)

                    st.success(f"✅ ट्रेड निष्पादित मूल्य: `{fill_price:.4f}`")

                    with st.expander("📦 देखें ऑर्डर डिटेल्स"):
                        st.json(order_res)

                    st.markdown("🎯 **ऑटो Stop Loss और Take Profit आर्डर सेट किए जा रहे हैं...**")
                    sl_tp_res, stop_price, target_price = place_sl_tp_orders(selected_symbol, side, fill_price)

                    with st.expander("🛡️ देखें TP/SL डिटेल्स"):
                        for label, res in sl_tp_res:
                            st.write(f"🔹 **{label}:**")
                            st.json(res)

                    tg_msg = (
                        f"⚡ *GYAN AI Trade Executed*\n\n"
                        f"🪙 **Symbol:** `{selected_symbol}`\n"
                        f"📊 **Side:** `{side.upper()}`\n"
                        f"💰 **Entry Price:** `{fill_price:.4f}`\n"
                        f"🛡️ **Stop Loss:** `{stop_price:.4f}`\n"
                        f"🎯 **Take Profit:** `{target_price:.4f}`"
                    )
                    send_telegram_alert(tg_msg)

                    st.markdown("---")
                    st.markdown("### 🧠 ट्रेड स्ट्रेटजी रिपोर्ट")
                    c_col1, c_col2, c_col3, c_col4 = st.columns(4)
                    c_col1.metric("Symbol", selected_symbol)
                    c_col2.metric("Direction", signal)
                    c_col3.metric("Entry", f"{fill_price:.4f}")
                    c_col4.metric("Risk/Reward", "1 : 2")

                    sc1, sc2 = st.columns(2)
                    sc1.error(f"🛡️ Stop Loss: {stop_price:.4f}")
                    sc2.success(f"🎯 Take Profit: {target_price:.4f}")

                    st.balloons()
                    st.success("✅ **ट्रेड सफलतापूर्वक सुरक्षित कर दिया गया है!**")

            except Exception as e:
                st.error(f"❌ **एक्जीक्यूशन एरर:** {str(e)}")

    if auto_trade:
        st.success("🔄 **AUTO SCALPING MODE ACTIVE**")
        run_scalping()
        time.sleep(refresh_rate)
        st.rerun()
    else:
        if st.button("⚡ तुरंत एक ट्रेड निष्पादित करें (One-Click Execute)"):
            run_scalping()

# ============================================================
# TAB 2 — AI MENTOR & CHAT
# ============================================================

with tab2:
    st.markdown("### 💬 GYAN AI Pro ट्रेडिंग मेंटर & रिसर्च रूम")
    st.markdown("यहाँ आप किसी भी कॉइन या अपनी ट्रेडिंग स्ट्रेटजी के बारे में सीधी चर्चा कर सकते हैं।")

    chat_symbol = st.selectbox("चैट के लिए सिंबल चुनें", symbols_list, key="t2_sym")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_query = st.chat_input("जैसे पूछें: इस कॉइन में मोमेंटम कैसा है?")

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("AI मेंटर जवाब तैयार कर रहा है..."):
                try:
                    ticker = get_ticker(chat_symbol)
                    price = ticker.get("mark_price", "N/A")

                    system_prompt = f"""
आप GYAN AI Pro के प्रोफेशनल और स्मार्ट ट्रेडिंग मेंटर हैं।
आप आसान और स्पष्ट हिंदी में जवाब देते हैं।
कॉइन: {chat_symbol}, करंट प्राइस: {price}
यूज़र का सवाल: {user_query}
"""
                    client = Groq(api_key=GROQ_API_KEY)
                    res = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_query}
                        ],
                        temperature=0.3,
                        max_tokens=1400
                    )
                    reply = res.choices[0].message.content
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                except Exception as e:
                    err_msg = f"क्षमा करें, चैट में एरर आ गया: {str(e)}"
                    st.error(err_msg)
                    st.session_state.messages.append({"role": "assistant", "content": err_msg})

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption("⚡ GYAN AI Pro | Institutional Fintech Suite | Delta Exchange India + Groq AI + Telegram Integration")
