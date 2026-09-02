import os
import time
import json
import hmac
import hashlib
from urllib.parse import urlencode

import requests
import pandas as pd
import streamlit as st
from groq import Groq


# ============================================================
# GH BOSS AI - DELTA AUTO SCALPER
# ============================================================

BASE_URL = "https://api.india.delta.exchange"

SYMBOL = "ARCUSD"
TIMEFRAME = "1m"

LOT_SIZE = 1

SL_PERCENT = 0.005
TP_PERCENT = 0.010

SCAN_SECONDS = 30
COOLDOWN_SECONDS = 60

TIMEOUT = 15


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="GH BOSS AI",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ GH BOSS AI - DELTA AUTO SCALPER")

st.write(
    "ARCUSD | 1 Minute | Lot Size 1 | Delta India"
)


# ============================================================
# ENV
# ============================================================

DELTA_API_KEY = os.getenv("DELTA_API_KEY", "").strip()
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()


# ============================================================
# SESSION
# ============================================================

if "last_signal" not in st.session_state:
    st.session_state.last_signal = "NONE"

if "last_trade_time" not in st.session_state:
    st.session_state.last_trade_time = 0

if "logs" not in st.session_state:
    st.session_state.logs = []


# ============================================================
# LOG
# ============================================================

def add_log(text):
    current_time = time.strftime("%H:%M:%S")
    message = "[" + current_time + "] " + text

    st.session_state.logs.insert(0, message)

    st.session_state.logs = st.session_state.logs[:50]


# ============================================================
# SIGNATURE
# ============================================================

def create_signature(method, timestamp, path, query_string, body):

    message = (
        method
        + str(timestamp)
        + path
        + query_string
        + body
    )

    signature = hmac.new(
        DELTA_API_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return signature


# ============================================================
# DELTA REQUEST
# ============================================================

def delta_request(
    method,
    path,
    params=None,
    body=None,
    authenticated=False
):

    if params is None:
        params = {}

    if body is None:
        body = {}

    body_text = ""

    if body:
        body_text = json.dumps(
            body,
            separators=(",", ":")
        )

    query_string = ""

    if params:
        query_string = "?" + urlencode(params)

    url = BASE_URL + path + query_string

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "GH-BOSS-AI"
    }

    if authenticated:

        if not DELTA_API_KEY:
            raise Exception("DELTA_API_KEY missing")

        if not DELTA_API_SECRET:
            raise Exception("DELTA_API_SECRET missing")

        timestamp = int(time.time())

        signature = create_signature(
            method.upper(),
            timestamp,
            path,
            query_string,
            body_text
        )

        headers["api-key"] = DELTA_API_KEY
        headers["timestamp"] = str(timestamp)
        headers["signature"] = signature

    response = requests.request(
        method=method.upper(),
        url=url,
        headers=headers,
        data=body_text if body else None,
        timeout=TIMEOUT
    )

    try:
        data = response.json()
    except Exception:
        raise Exception(
            "Delta returned invalid response: "
            + response.text[:500]
        )

    if response.status_code >= 400:

        raise Exception(
            "HTTP "
            + str(response.status_code)
            + ": "
            + str(data)
        )

    return data


# ============================================================
# GET PRODUCT
# ============================================================

def get_product(symbol):

    data = delta_request(
        "GET",
        "/v2/products/" + symbol
    )

    if not data.get("success"):
        raise Exception(
            "Product error: " + str(data)
        )

    return data.get("result")


# ============================================================
# GET TICKER
# ============================================================

def get_ticker(symbol):

    data = delta_request(
        "GET",
        "/v2/tickers/" + symbol
    )

    if not data.get("success"):
        raise Exception(
            "Ticker error: " + str(data)
        )

    return data.get("result", {})


# ============================================================
# GET CANDLES
# ============================================================

def get_candles(symbol):

    end_time = int(time.time())

    start_time = end_time - (60 * 60)

    params = {
        "resolution": "1m",
        "symbol": symbol,
        "start": start_time,
        "end": end_time
    }

    data = delta_request(
        "GET",
        "/v2/history/candles",
        params=params
    )

    if not data.get("success"):
        raise Exception(
            "Candle error: " + str(data)
        )

    candles = data.get("result", [])

    if not candles:
        return pd.DataFrame()

    df = pd.DataFrame(candles)

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    if "time" in df.columns:

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s",
            errors="coerce"
        )

    df = df.sort_values(
        "time"
    ).reset_index(drop=True)

    return df


# ============================================================
# GET POSITION
# ============================================================

def get_position(product_id):

    params = {
        "product_id": product_id
    }

    data = delta_request(
        "GET",
        "/v2/positions",
        params=params,
        authenticated=True
    )

    if not data.get("success"):
        raise Exception(
            "Position error: " + str(data)
        )

    result = data.get("result")

    if isinstance(result, list):

        if len(result) == 0:
            return None

        return result[0]

    return result


# ============================================================
# POSITION SIZE
# ============================================================

def position_size(position):

    if not position:
        return 0

    value = position.get("size", 0)

    try:
        return float(value)
    except Exception:
        return 0


# ============================================================
# GROQ AI
# ============================================================

def get_ai_signal(df):

    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY missing")

    if len(df) < 20:
        return "NO_TRADE"

    recent = df.tail(20)

    text = ""

    for _, row in recent.iterrows():

        text += (
            "O="
            + str(row["open"])
            + " H="
            + str(row["high"])
            + " L="
            + str(row["low"])
            + " C="
            + str(row["close"])
            + " V="
            + str(row["volume"])
            + "\n"
        )

    prompt = """
You are a strict 1-minute crypto scalping signal engine.

Analyze the candle data.

Consider:
1. Short-term trend
2. Momentum
3. Candle structure
4. Breakout or breakdown
5. Volume
6. Recent price direction

Return ONLY one of these:

BUY
SELL
NO_TRADE

Do not return any explanation.

Candle data:
""" + text

    client = Groq(
        api_key=GROQ_API_KEY
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=5
    )

    answer = (
        response.choices[0]
        .message
        .content
        .strip()
        .upper()
    )

    if answer == "BUY":
        return "BUY"

    if answer == "SELL":
        return "SELL"

    return "NO_TRADE"


# ============================================================
# MARKET ORDER
# ============================================================

def market_order(symbol, side):

    body = {
        "product_symbol": symbol,
        "size": LOT_SIZE,
        "side": side,
        "order_type": "market_order",
        "time_in_force": "ioc"
    }

    data = delta_request(
        "POST",
        "/v2/orders",
        body=body,
        authenticated=True
    )

    if not data.get("success"):
        raise Exception(
            "Order failed: " + str(data)
        )

    return data.get("result", {})


# ============================================================
# BRACKET
# ============================================================

def create_bracket(symbol, side, entry):

    entry = float(entry)

    if side == "buy":

        stop_price = entry * (
            1 - SL_PERCENT
        )

        take_price = entry * (
            1 + TP_PERCENT
        )

    else:

        stop_price = entry * (
            1 + SL_PERCENT
        )

        take_price = entry * (
            1 - TP_PERCENT
        )

    body = {
        "product_symbol": symbol,

        "stop_loss_order": {
            "order_type": "market_order",
            "stop_price": str(
                round(stop_price, 8)
            )
        },

        "take_profit_order": {
            "order_type": "limit_order",
            "limit_price": str(
                round(take_price, 8)
            )
        },

        "bracket_stop_trigger_method": "mark_price"
    }

    data = delta_request(
        "POST",
        "/v2/orders/bracket",
        body=body,
        authenticated=True
    )

    if not data.get("success"):
        raise Exception(
            "Bracket failed: " + str(data)
        )

    return data.get("result", {})


# ============================================================
# TRADE
# ============================================================

def execute_trade(symbol, signal):

    product = get_product(symbol)

    product_id = product.get("id")

    if not product_id:
        raise Exception(
            "Product ID not found"
        )

    position = get_position(product_id)

    size = position_size(position)

    if abs(size) > 0:

        add_log(
            "Existing position detected. "
            "New trade blocked."
        )

        return

    current_time = time.time()

    if (
        current_time
        - st.session_state.last_trade_time
        < COOLDOWN_SECONDS
    ):

        add_log("Cooldown active.")

        return

    if signal == "BUY":

        side = "buy"

    elif signal == "SELL":

        side = "sell"

    else:

        add_log("NO_TRADE")

        return

    add_log(
        "REAL ORDER: "
        + signal
        + " | "
        + symbol
        + " | SIZE="
        + str(LOT_SIZE)
    )

    order = market_order(
        symbol,
        side
    )

    st.session_state.last_trade_time = time.time()

    add_log(
        "MARKET ORDER SUCCESS"
    )

    st.write("Order result:")
    st.json(order)

    time.sleep(1)

    ticker = get_ticker(symbol)

    entry = ticker.get("mark_price")

    if not entry:
        entry = ticker.get("close")

    if entry:

        try:

            bracket = create_bracket(
                symbol,
                side,
                entry
            )

            add_log(
                "SL/TP BRACKET SUCCESS"
            )

            st.write("Bracket result:")
            st.json(bracket)

        except Exception as error:

            add_log(
                "BRACKET ERROR: "
                + str(error)
            )

            st.error(
                "Market order placed, "
                "but bracket failed: "
                + str(error)
            )


# ============================================================
# SCAN
# ============================================================

def scan_market():

    add_log(
        "Scanning " + SYMBOL
    )

    product = get_product(SYMBOL)

    if not product:
        raise Exception(
            "ARCUSD product not found"
        )

    df = get_candles(SYMBOL)

    if df.empty:
        raise Exception(
            "No candle data"
        )

    last_price = df.iloc[-1]["close"]

    st.metric(
        "ARCUSD Price",
        str(last_price)
    )

    signal = get_ai_signal(df)

    st.session_state.last_signal = signal

    add_log(
        "AI SIGNAL = " + signal
    )

    if signal == "NO_TRADE":

        add_log(
            "No trade."
        )

        return

    execute_trade(
        SYMBOL,
        signal
    )


# ============================================================
# API TEST
# ============================================================

def test_delta():

    return delta_request(
        "GET",
        "/v2/orders",
        params={
            "page_size": 1
        },
        authenticated=True
    )


# ============================================================
# STATUS
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:

    if DELTA_API_KEY and DELTA_API_SECRET:
        st.success("Delta API READY")
    else:
        st.error("Delta API MISSING")

with col2:

    if GROQ_API_KEY:
        st.success("Groq READY")
    else:
        st.error("Groq API MISSING")

with col3:

    st.info(
        "LOT SIZE = " + str(LOT_SIZE)
    )


# ============================================================
# CONTROL
# ============================================================

st.subheader("Control Panel")

col1, col2 = st.columns(2)

with col1:

    if st.button(
        "🔐 TEST DELTA API",
        use_container_width=True
    ):

        try:

            result = test_delta()

            st.success(
                "Delta API authentication OK"
            )

            st.json(result)

            add_log(
                "Delta API TEST SUCCESS"
            )

        except Exception as error:

            st.error(
                "Delta API ERROR: "
                + str(error)
            )

            add_log(
                "Delta API ERROR: "
                + str(error)
            )


with col2:

    if st.button(
        "⚡ SCAN + REAL TRADE",
        use_container_width=True
    ):

        try:

            scan_market()

            st.success(
                "Scan completed"
            )

        except Exception as error:

            st.error(
                "Scan ERROR: "
                + str(error)
            )

            add_log(
                "SCAN ERROR: "
                + str(error)
            )


# ============================================================
# AUTO MODE
# ============================================================

st.subheader("🤖 AUTO SCALPING")

auto_mode = st.checkbox(
    "START AUTO SCALPING"
)

if auto_mode:

    st.warning(
        "REAL TRADING ACTIVE"
    )

    st.write(
        "Scanner runs every "
        + str(SCAN_SECONDS)
        + " seconds."
    )

    while True:

        try:

            scan_market()

        except Exception as error:

            add_log(
                "AUTO ERROR: "
                + str(error)
            )

            st.error(
                "AUTO ERROR: "
                + str(error)
            )

        time.sleep(
            SCAN_SECONDS
        )

        st.rerun()


# ============================================================
# LIVE DATA
# ============================================================

st.subheader("📊 Live Market")

try:

    ticker = get_ticker(SYMBOL)

    col1, col2, col3 = st.columns(3)

    with col1:

        st.write("Symbol")
        st.write(SYMBOL)

    with col2:

        st.write("Last Price")
        st.write(
            ticker.get(
                "close",
                "N/A"
            )
        )

    with col3:

        st.write("Mark Price")
        st.write(
            ticker.get(
                "mark_price",
                "N/A"
            )
        )

except Exception as error:

    st.error(
        "Ticker ERROR: "
        + str
