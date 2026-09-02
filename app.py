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
# GH BOSS AI - ULTIMATE MULTI-CRYPTO FAST SCALPER
# ============================================================

BASE_URL = "https://api.india.delta.exchange"

LOT_SIZE = 1
SL_PERCENT = 0.005   # 0.5%
TP_PERCENT = 0.010   # 1.0%


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="GH BOSS AI Fast Scalper",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ GH BOSS AI — AUTOMATED FAST SCALPER")
st.subheader("Delta Exchange India - Multi-Crypto Engine")


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
# GET ALL TRADABLE PRODUCTS (Pagination Supported)
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
# MARKET DATA & CANDLES
# ============================================================

def get_ticker(symbol):
    data = delta_request("GET", f"/v2/tickers/{symbol}")
    return data.get("result", {})


def get_candles(symbol):
    end_time = int(time.time())
    start_time = end_time - 3600  # last 1 hour

    params = {
        "resolution": "1m",
        "symbol": symbol,
        "start": start_time,
        "end": end_time
    }

    data = delta_request("GET", "/v2/history/candles", params=params)
    return data.get("result", [])


# ============================================================
# AI SIGNAL (Groq with Fallback)
# ============================================================

def get_signal(candles, symbol):
    if not GROQ_API_KEY or len(candles) < 10:
        return "NO_TRADE"

    recent = candles[-20:]
    candle_text = "\n".join(str(c) for c in recent)

    prompt = f"""
You are an ultra-fast 1-minute crypto scalping engine.
Symbol: {symbol}
Analyze these 1m candles. Return ONLY one word:
BUY
SELL
NO_TRADE

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
                temperature=0,
                max_tokens=5
            )
            ans = res.choices[0].message.content.strip().upper()
            if ans in ("BUY", "SELL", "NO_TRADE"):
                return ans
        except Exception:
            continue
    return "NO_TRADE"


# ============================================================
# POSITIONS & ORDERS
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
# UI & EXECUTION PANEL
# ============================================================

symbols_list = get_all_symbols()
if not symbols_list:
    symbols_list = ["ARCUSD", "BTCUSD", "ETHUSD"]

col1, col2 = st.columns(2)
with col1:
    selected_symbol = st.selectbox("🪙 Select Crypto Symbol", symbols_list, index=0 if "ARCUSD" in symbols_list else 0)

with col2:
    st.write("### Quick Status")
    st.write(f"Active Symbol: **{selected_symbol}**")

st.divider()

if st.button("⚡ FAST SCAN & EXECUTE TRADE"):
    with st.spinner(f"Analyzing {selected_symbol} & executing fast scalping..."):
        try:
            ticker = get_ticker(selected_symbol)
            product_id = ticker.get("product_id")
            mark_price = float(ticker.get("mark_price") or ticker.get("close") or 0)

            st.write(f"📊 Current Mark Price: `{mark_price}`")

            # Check position
            pos_size = get_position(product_id)
            if pos_size != 0:
                st.warning(f"⚠️ Already holding position (Size: {pos_size}). New entry skipped.")
            else:
                candles = get_candles(selected_symbol)
                signal = get_signal(candles, selected_symbol)

                st.info(f"🤖 AI Signal for {selected_symbol}: **{signal}**")

                if signal == "NO_TRADE":
                    st.warning("⏳ No trade opportunity found by AI right now.")
                else:
                    side = "buy" if signal == "BUY" else "sell"
                    st.success(f"🚀 Placing Fast Market {side.upper()} Order...")
                    
                    order_res = place_order(selected_symbol, side)
                    st.json(order_res)

                    fill_price = float(order_res.get("average_fill_price") or mark_price)
                    
                    st.success("🎯 Setting Bracket SL & TP...")
                    bracket_res = place_bracket(selected_symbol, side, fill_price)
                    st.json(bracket_res)
                    st.success("✅ Fast Trade & Bracket Successfully Placed!")

        except Exception as e:
            st.error(f"❌ Execution Error: {str(e)}")

st.divider()
if st.button("🔄 Refresh Market Data"):
    st.rerun()
