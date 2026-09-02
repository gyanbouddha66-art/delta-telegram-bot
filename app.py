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
# GH BOSS AI - ULTIMATE AUTO SCALPER (HINDI & FAST)
# ============================================================

BASE_URL = "https://api.india.delta.exchange"

LOT_SIZE = 1
SL_PERCENT = 0.005   # 0.5% SL
TP_PERCENT = 0.010   # 1.0% TP


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="GH BOSS AI Auto Scalper",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ GH BOSS AI — ऑटोमैटिक फास्ट स्केल्पर")
st.subheader("लाइव मार्केट एनालिसिस और ऑटो ट्रेड एक्जीक्यूशन")


# ============================================================
# API KEYS
# ============================================================

DELTA_API_KEY = os.getenv("DELTA_API_KEY", "")
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


# ============================================================
# DELTA REQUEST
# ============================================================

def delta_request(method, path, params=None, body=None, auth=False):
    if params is None:
        params = {}
    if body is None:
        body = {}

    body_text = ""
    if body:
        body_text = json.dumps(body, separators=(",", ":"))

    query_string = ""
    if params:
        query_string = "?" + urlencode(params)

    timestamp = int(time.time())

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "GH-BOSS-AI"
    }

    if auth:
        if not DELTA_API_KEY or not DELTA_API_SECRET:
            raise Exception("Delta API Keys missing")

        message = (
            method.upper()
            + str(timestamp)
            + path
            + query_string
            + body_text
        )

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


def get_ticker(symbol):
    data = delta_request("GET", f"/v2/tickers/{symbol}")
    return data.get("result", {})


def get_candles(symbol):
    end_time = int(time.time())
    start_time = end_time - 1800  # last 30 mins

    params = {
        "resolution": "1m",
        "symbol": symbol,
        "start": start_time,
        "end": end_time
    }

    data = delta_request("GET", "/v2/history/candles", params=params)
    return data.get("result", [])


# ============================================================
# AGGRESSIVE AI SIGNAL (FORCING BUY/SELL FOR SCALPING)
# ============================================================

def get_signal(candles, symbol):
    if not GROQ_API_KEY or len(candles) < 5:
        return "BUY"  # Default fallback to keep scalping fast

    recent = candles[-10:]
    candle_text = "\n".join(str(c) for c in recent)

    prompt = f"""
You are an aggressive 1-minute crypto scalping engine. Your job is to find quick momentum and make trades instantly.
Symbol: {symbol}
Analyze these 1m candles. You MUST choose ONLY one word (DO NOT output NO_TRADE unless market is dead):
BUY
SELL

CANDLES:
{candle_text}
"""

    client = Groq(api_key=GROQ_API_KEY)
    models = ["llama-3.1-8b-instant", "llama3-8b-8192", "llama-3.3-70b-versatile"]

    for model in models:
        try:
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=5
            )
            ans = res.choices[0].message.content.strip().upper()
            if ans in ("BUY", "SELL"):
                return ans
        except Exception:
            continue
    return "BUY"


# ============================================================
# TRADING FUNCTIONS
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


def place_order(symbol, side):
    body = {
        "product_symbol": symbol,
        "size": LOT_SIZE,
        "side": side,
        "order_type": "market_order",
        "time_in_force": "ioc"
    }
    data = delta_request("POST", "/v2/orders", body=body, auth=True)
    return data.get("result", {})


def place_bracket(symbol, side, entry):
    entry = float(entry)
    if side == "buy":
        stop = entry * (1 - SL_PERCENT)
        target = entry * (1 + TP_PERCENT)
    else:
        stop = entry * (1 + SL_PERCENT)
        target = entry * (1 - TP_PERCENT)

    body = {
        "product_symbol": symbol,
        "stop_loss_order": {
            "order_type": "market_order",
            "stop_price": str(round(stop, 8))
        },
        "take_profit_order": {
            "order_type": "limit_order",
            "limit_price": str(round(target, 8))
        },
        "bracket_stop_trigger_method": "mark_price"
    }
    data = delta_request("POST", "/v2/orders/bracket", body=body, auth=True)
    return data.get("result", {})


# ============================================================
# STREAMLIT UI & AUTO LOOP
# ============================================================

symbols_list = get_all_symbols()
if not symbols_list:
    symbols_list = ["ARCUSD", "BTCUSD", "ETHUSD"]

col1, col2, col3 = st.columns(3)
with col1:
    selected_symbol = st.selectbox("🪙 क्रिप्टो सिंबल चुनें", symbols_list)
with col2:
    auto_trade = st.checkbox("🔄 ऑटो-स्केल्पिंग मोड चालू करें (Auto Scalping Loop)", value=False)
with col3:
    refresh_rate = st.slider("⏱️ रिफ्रेश टाइम (सेकंड)", 5, 30, 5)

st.divider()

placeholder = st.empty()

def run_scalping():
    with placeholder.container():
        try:
            st.info(f"🔍 **{selected_symbol}** के लिए लाइव डेटा और AI सिग्नल चेक हो रहा है...")
            ticker = get_ticker(selected_symbol)
            product_id = ticker.get("product_id")
            mark_price = float(ticker.get("mark_price") or ticker.get("close") or 0)

            st.write(f"📊 **करेंट मार्क प्राइस:** `{mark_price}`")

            pos_size = get_position(product_id)
            if pos_size != 0:
                st.warning(f"⚠️ पहले से पोजीशन खुली हुई है (साइज: {pos_size})। नई एंट्री अभी नहीं ली जाएगी।")
            else:
                candles = get_candles(selected_symbol)
                signal = get_signal(candles, selected_symbol)

                st.success(f"🤖 **AI सिग्नल:** `{signal}`")

                side = "buy" if signal == "BUY" else "sell"
                st.write(f"🚀 **फास्ट मार्केट {side.upper()} ऑर्डर भेजा जा रहा है...**")
                
                order_res = place_order(selected_symbol, side)
                fill_price = float(order_res.get("average_fill_price") or mark_price)
                st.json(order_res)

                st.write("🎯 **ब्रैकेट SL और TP सेट किया जा रहा है...**")
                bracket_res = place_bracket(selected_symbol, side, fill_price)
                st.json(bracket_res)
                st.success("✅ **ट्रेड सफलतापूर्वक लग गया और TP/SL सेट हो गया!**")

        except Exception as e:
            st.error(f"❌ **एरर:** {str(e)}")

if auto_trade:
    while True:
        run_scalping()
        time.sleep(refresh_rate)
        st.rerun()
else:
    if st.button("⚡ अभी तुरंत एक ट्रेड लो (One-Click Scalp)"):
        run_scalping()
