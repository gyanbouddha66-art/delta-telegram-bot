import os
import time
import hmac
import hashlib
from urllib.parse import urlencode
from datetime import datetime, timezone

import requests
import pandas as pd
import streamlit as st
from groq import Groq


# ============================================================
# GH BOSS AI — DELTA AUTO SCALPER
# ARCUSD | 1 MIN | LOT SIZE 1
# ============================================================

BASE_URL = "https://api.india.delta.exchange"

DEFAULT_SYMBOL = "ARCUSD"
TIMEFRAME = "1m"

LOT_SIZE = 1

CANDLE_LIMIT = 50

# Risk
SL_PERCENT = 0.0050       # 0.50%
TP_PERCENT = 0.0100       # 1.00%

# Automatic scan
SCAN_SECONDS = 30
COOLDOWN_SECONDS = 60

REQUEST_TIMEOUT = 15


# ============================================================
# STREAMLIT
# ============================================================

st.set_page_config(
    page_title="GH Boss AI Auto Scalper",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ GH BOSS AI — DELTA AUTO SCALPER")
st.caption("Delta India • Direct REST API • ARCUSD • 1m • Lot Size 1")


# ============================================================
# ENVIRONMENT
# ============================================================

DELTA_API_KEY = os.getenv("DELTA_API_KEY", "").strip()
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()


# ============================================================
# SESSION STATE
# ============================================================

if "last_trade_time" not in st.session_state:
    st.session_state.last_trade_time = 0

if "last_signal" not in st.session_state:
    st.session_state.last_signal = "NONE"

if "last_order" not in st.session_state:
    st.session_state.last_order = None

if "running" not in st.session_state:
    st.session_state.running = False

if "logs" not in st.session_state:
    st.session_state.logs = []


# ============================================================
# LOG
# ============================================================

def log(message):
    now = datetime.now().strftime("%H:%M:%S")
    text = f"[{now}] {message}"

    st.session_state.logs.insert(0, text)

    # Keep only latest 100 logs
    st.session_state.logs = st.session_state.logs[:100]


# ============================================================
# DELTA SIGNATURE
# ============================================================

def make_signature(method, timestamp, path, query_string="", body=""):
    message = (
        method
        + str(timestamp)
        + path
        + query_string
        + body
    )

    signature = hmac.new(
        DELTA_API_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return signature


# ============================================================
# DELTA REQUEST
# ============================================================

def delta_request(method, path, params=None, body=None, auth=False):

    params = params or {}

    body = body or {}

    body_text = ""

    if body:
        import json
        body_text = json.dumps(
            body,
            separators=(",", ":")
        )

    query_string = ""

    if params:
        query_string = "?" + urlencode(
            params,
            doseq=True
        )

    url = BASE_URL + path + query_string

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "GH-BOSS-AI-AUTO-SCALPER/1.0"
    }

    if auth:

        if not DELTA_API_KEY or not DELTA_API_SECRET:
            raise Exception(
                "DELTA_API_KEY / DELTA_API_SECRET missing"
            )

        timestamp = int(time.time())

        signature = make_signature(
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
        timeout=REQUEST_TIMEOUT
    )

    try:
        data = response.json()
    except Exception:
        data = {
            "success": False,
            "http_status": response.status_code,
            "raw": response.text
        }

    if response.status_code >= 400:

        raise Exception(
            f"HTTP {response.status_code}: {data}"
        )

    return data


# ============================================================
# PRODUCT
# ============================================================

def get_product(symbol):

    data = delta_request(
        "GET",
        f"/v2/products/{symbol}"
    )

    if not data.get("success", False):
        raise Exception(
            f"Product error: {data}"
        )

    result = data.get("result")

    if not result:
        raise Exception(
            f"Product not found: {symbol}"
        )

    return result


# ============================================================
# ALL PRODUCTS
# ============================================================

def get_all_products():

    all_products = []

    after = None

    for _ in range(20):

        params = {
            "page_size": 100
        }

        if after:
            params["after"] = after

        data = delta_request(
            "GET",
            "/v2/products",
            params=params
        )

        if not data.get("success", False):
            break

        result = data.get("result", [])

        if not isinstance(result, list):
            break

        all_products.extend(result)

        meta = data.get("meta", {})

        next_cursor = meta.get("next_cursor")

        if not next_cursor:
            break

        after = next_cursor

    return all_products


# ============================================================
# CANDLES
# ============================================================

def get_candles(symbol):

    end = int(time.time())
    start = end - (CANDLE_LIMIT * 60)

    params = {
        "resolution": "1m",
        "symbol": symbol,
        "start": start,
        "end": end
    }

    data = delta_request(
        "GET",
        "/v2/history/candles",
        params=params
    )

    if not data.get("success", False):
        raise Exception(
            f"Candle error: {data}"
        )

    rows = data.get("result", [])

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Normalize possible timestamp field
    if "time" in df.columns:

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s",
            errors="coerce"
        )

    for col in ["open", "high", "low", "close", "volume"]:

        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    df = df.sort_values(
        "time"
    ).reset_index(drop=True)

    return df


# ============================================================
# TICKER
# ============================================================

def get_ticker(symbol):

    data = delta_request(
        "GET",
        f"/v2/tickers/{symbol}"
    )

    if not data.get("success", False):
        raise Exception(
            f"Ticker error: {data}"
        )

    return data.get("result", {})


# ============================================================
# POSITION
# ============================================================

def get_position(product_id):

    data = delta_request(
        "GET",
        "/v2/positions",
        params={
            "product_id": product_id
        },
        auth=True
    )

    if not data.get("success", False):
        raise Exception(
            f"Position error: {data}"
        )

    result = data.get("result")

    if isinstance(result, list):

        if not result:
            return None

        return result[0]

    return result


# ============================================================
# POSITION SIZE
# ============================================================

def get_position_size(position):

    if not position:
        return 0

    value = position.get("size", 0)

    try:
        return float(value)
    except Exception:
        return 0


# ============================================================
# AI SIGNAL
# ============================================================

def get_ai_signal(df):

    if not GROQ_API_KEY:
        raise Exception(
            "GROQ_API_KEY missing"
        )

    if len(df) < 20:
        return "NO_TRADE"

    recent = df.tail(20).copy()

    candle_text = ""

    for _, row in recent.iterrows():

        candle_text += (
            f"O={row.get('open')} "
            f"H={row.get('high')} "
            f"L={row.get('low')} "
            f"C={row.get('close')} "
            f"V={row.get('volume')}\n"
        )

    prompt = f"""
You are a strict crypto scalping decision engine.

Symbol: ARCUSD
Timeframe: 1 minute.

Analyze the last 20 candles.

Look for:
- bullish/bearish price structure
- momentum
- consecutive candle direction
- rejection
- breakout/breakdown
- volume confirmation
- short-term trend

You MUST choose exactly one:

BUY
SELL
NO_TRADE

Do not write anything else.

Candles:
{candle_text}
"""

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
        max_tokens=10
    )

    answer = (
        response.choices[0]
        .message
        .content
        .strip()
        .upper()
    )

    if "BUY" in answer:
        return "BUY"

    if "SELL" in answer:
        return "SELL"

    return "NO_TRADE"


# ============================================================
# MARKET ORDER
# ============================================================

def place_market_order(
    product_symbol,
    side
):

    body = {
        "product_symbol": product_symbol,
        "size": LOT_SIZE,
        "side": side,
        "order_type": "market_order",
        "time_in_force": "ioc",
        "reduce_only": False,
        "post_only": False,
        "mmp": "disabled"
    }

    data = delta_request(
        "POST",
        "/v2/orders",
        body=body,
        auth=True
    )

    if not data.get("success", False):
        raise Exception(
            f"Order failed: {data}"
        )

    return data.get("result", {})


# ============================================================
# BRACKET ORDER
# ============================================================

def place_bracket(
    product_symbol,
    side,
    entry_price
):

    entry_price = float(entry_price)

    if side == "buy":

        stop_price = entry_price * (
            1 - SL_PERCENT
        )

        take_price = entry_price * (
            1 + TP_PERCENT
        )

    else:

        stop_price = entry_price * (
            1 + SL_PERCENT
        )

        take_price = entry_price * (
            1 - TP_PERCENT
        )

    stop_loss_order = {
        "order_type": "market_order",
        "stop_price": str(
            round(stop_price, 8)
        )
    }

    take_profit_order = {
        "order_type": "limit_order",
        "limit_price": str(
            round(take_price, 8)
        )
    }

    body = {
        "product_symbol": product_symbol,

        "stop_loss_order": stop_loss_order,

        "take_profit_order": take_profit_order,

        "bracket_stop_trigger_method": "mark_price"
    }

    data = delta_request(
        "POST",
        "/v2/orders/bracket",
        body=body,
        auth=True
    )

    if not data.get("success", False):

        raise Exception(
            f"Bracket failed: {data}"
        )

    return data.get("result", {})


# ============================================================
# ORDER EXECUTION
# ============================================================

def execute_trade(symbol, signal):

    product = get_product(symbol)

    product_id = product.get("id")

    if not product_id:
        raise Exception(
            "Product ID missing"
        )

    # Check existing position
    position = get_position(
        product_id
    )

    current_size = get_position_size(
        position
    )

    if abs(current_size) > 0:

        log(
            f"POSITION ACTIVE: {current_size}. "
            f"New trade blocked."
        )

        return {
            "status": "blocked",
            "reason": "existing_position"
        }

    if signal not in ["BUY", "SELL"]:

        return {
            "status": "no_trade"
        }

    # Cooldown
    now = time.time()

    if (
        now - st.session_state.last_trade_time
        < COOLDOWN_SECONDS
    ):

        remaining = int(
            COOLDOWN_SECONDS
            - (
                now
                - st.session_state.last_trade_time
            )
        )

        log(
            f"COOLDOWN active: {remaining}s"
        )

        return {
            "status": "cooldown"
        }

    side = (
        "buy"
        if signal == "BUY"
        else "sell"
    )

    log(
        f"🚀 REAL ORDER: {signal} | "
        f"{symbol} | SIZE={LOT_SIZE}"
    )

    # Market order
    order = place_market_order(
        symbol,
        side
    )

    st.session_state.last_trade_time = time.time()
    st.session_state.last_order = order

    log(
        f"MARKET ORDER SUCCESS: {order}"
    )

    # Give exchange a moment
    time.sleep(1)

    # Get ticker after order
    ticker = get_ticker(symbol)

    entry_price = (
        ticker.get("mark_price")
        or ticker.get("close")
        or ticker.get("last_price")
    )

    if entry_price:

        try:

            bracket = place_bracket(
                symbol,
                side,
                float(entry_price)
            )

            log(
                f"🛡 SL/TP BRACKET SUCCESS: "
                f"{bracket}"
            )

        except Exception as e:

            log(
                f"⚠ MARKET ORDER FILLED BUT "
                f"BRACKET ERROR: {e}"
            )

    else:

        log(
            "⚠ Entry price unavailable; "
            "bracket was not created."
        )

    return {
        "status": "executed",
        "order": order
    }


# ============================================================
# API TEST
# ============================================================

def test_api():

    data = delta_request(
        "GET",
        "/v2/orders",
        params={
            "page_size": 1
        },
        auth=True
    )

    return data


# ============================================================
# AUTO SCAN
# ============================================================

def run_one_scan(symbol):

    log(
        f"🔎 Scanning {symbol}..."
    )

    # Product
    product = get_product(symbol)

    log(
        f"PRODUCT OK: {symbol} "
        f"(ID={product.get('id')})"
    )

    # Candles
    df = get_candles(symbol)

    if df.empty:

        log(
            "No candle data."
        )

        return

    last_close = df.iloc[-1]["close"]

    log(
        f"PRICE: {last_close}"
    )

    # AI
    signal = get_ai_signal(df)

    st.session_state.last_signal = signal

    log(
        f"🤖 AI SIGNAL: {signal}"
    )

    if signal == "NO_TRADE":

        log(
            "No trade."
        )

        return

    # Execute
    result = execute_trade(
        symbol,
        signal
    )

    log(
        f"EXECUTION RESULT: {result.get('status')}"
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙ SETTINGS")

symbol = st.sidebar.text_input(
    "Symbol",
    value=DEFAULT_SYMBOL
).upper().strip()

st.sidebar.write(
    f"**Timeframe:** {TIMEFRAME}"
)

st.sidebar.write(
    f"**Lot Size:** {LOT_SIZE}"
)

st.sidebar.write(
    f"**SL:** {SL_PERCENT * 100:.2f}%"
)

st.sidebar.write(
    f"**TP:** {TP_PERCENT * 100:.2f}%"
)

st.sidebar.write(
    f"**Scan:** {SCAN_SECONDS}s"
)

st.sidebar.write(
    f"**Cooldown:** {COOLDOWN_SECONDS}s"
)


# ============================================================
# STATUS
# ============================================================

col1, col2, col3, col4 = st.columns(4)

with col1:

    if DELTA_API_KEY and DELTA_API_SECRET:
        st.success("Delta API: READY")
    else:
        st.error("Delta API: MISSING")


with col2:

    if GROQ_API_KEY:
        st.success("Groq AI: READY")
    else:
        st.error("Groq AI: MISSING")


with col3:

    st.metric(
        "Last Signal",
        st.session_state.last_signal
    )


with col4:

    st.metric(
        "Lot Size",
        LOT_SIZE
    )


# ============================================================
# BUTTONS
# ============================================================

st.subheader("🎮 Control")

c1, c2, c3 = st.columns(3)

with c1:

    test_button = st.button(
        "🔐 Test Delta API",
        use_container_width=True
    )

with c2:

    scan_button = st.button(
        "⚡ Scan + Trade Now",
        use_container_width=True
    )

with c3:

    if st.button(
        "🛑 STOP AUTO",
        use_container_width=True
    ):

        st.session_state.running = False

        log(
            "🛑 AUTO SCALPER STOPPED"
        )


# ============================================================
# TEST API
# ============================================================

if test_button:

    try:

        result = test_api()

        st.success(
            "✅ Delta authenticated API working"
        )

        st.json(result)

        log(
            "Delta API authentication SUCCESS"
        )

    except Exception as e:

        st.error(
            f"❌ Delta API ERROR: {e}"
        )

        log(
            f"Delta API ERROR: {e}"
        )


# ============================================================
# MANUAL SCAN
# ============================================================

if scan_button:

    try:

        run_one_scan(symbol)

        st.success(
            "Scan completed."
        )

    except Exception as e:

        st.error(
            f"Scan error: {e}"
        )

        log(
            f"SCAN ERROR: {e}"
        )


# ============================================================
# AUTO START
# ============================================================

st.subheader("🤖 Automatic Scalping")

auto_start = st.checkbox(
    "START AUTOMATIC SCALPING",
    value=st.session_state.running
)

if auto_start:

    st.session_state.running = True

else:

    st.session_state.running = False


if st.session_state.running:

    st.warning(
        "⚠ AUTO MODE ACTIVE — REAL ORDERS CAN BE PLACED"
    )

    placeholder = st.empty()

    while st.session_state.running:

        cycle_start = time.time()

        try:

            run_one_scan(symbol)

        except Exception as e:

            log(
                f"AUTO ERROR: {e}"
            )

        # Show logs
        with placeholder.container():

            st.write(
                f"### 🔄 AUTO SCANNER — {symbol}"
            )

            st.write(
                f"Next scan in approximately "
                f"{SCAN_SECONDS} seconds"
            )

            if st.session_state.logs:

                st.code(
                    "\n".join(
                        st.session_state.logs[:30]
                    )
                )

        elapsed = (
            time.time()
            - cycle_start
        )

        sleep_time = max(
            1,
            SCAN_SECONDS - elapsed
        )

        time.sleep(
            sleep_time
        )

        st.rerun()


# ============================================================
# MARKET DATA
# ============================================================

st.subheader("📊 Live Market Data")

try:

    ticker = get_ticker(symbol)

    t1, t2, t3, t4 = st.columns(4)

    with t1:
        st.metric(
            "Symbol",
            symbol
        )

    with t2:
        st.metric(
            "Last Price",
            ticker.get(
                "close",
                "N/A"
            )
        )

    with t3:
        st.metric(
            "Mark Price",
            ticker.get(
                "mark_price",
                "N/A"
            )
        )

    with t4:
        st.metric(
            "Volume",
            ticker.get(
                "volume",
                "N/A"
            )
        )

except Exception as e:

    st.error(
        f"Ticker error: {e}"
   
