import os
import time
import hmac
import hashlib
import json
import requests
import pandas as pd
import streamlit as st
from groq import Groq


# ============================================================
# GH ARCUSD REAL SCALPER
# DELTA EXCHANGE INDIA V2
# REAL DATA + REAL ORDER + REAL BRACKET SL/TP
# ============================================================

st.set_page_config(
    page_title="GH ARCUSD Real Scalper",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ GH ARCUSD REAL CRYPTO SCALPER")

# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://api.india.delta.exchange"

DEFAULT_SYMBOL = "ARCUSD"

TIMEFRAME = "1m"
CANDLE_LIMIT = 30

# REAL TRADING
DEFAULT_ORDER_SIZE = 1

# Risk
SL_PERCENT = 0.0050       # 0.50%
TP_PERCENT = 0.0100       # 1.00%

# Minimum gap between new trades
COOLDOWN_SECONDS = 60

# ============================================================
# ENVIRONMENT
# ============================================================

DELTA_API_KEY = os.getenv("DELTA_API_KEY", "").strip()
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()


# ============================================================
# DELTA SIGNATURE
# ============================================================

def generate_signature(secret, method, timestamp, path, query_string="", payload=""):
    message = (
        method.upper()
        + str(timestamp)
        + path
        + query_string
        + payload
    )

    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


# ============================================================
# AUTH HEADERS
# ============================================================

def delta_headers(method, path, query_string="", payload=""):
    if not DELTA_API_KEY or not DELTA_API_SECRET:
        raise Exception(
            "DELTA_API_KEY या DELTA_API_SECRET Render Environment Variables में missing है."
        )

    timestamp = str(int(time.time()))

    signature = generate_signature(
        DELTA_API_SECRET,
        method,
        timestamp,
        path,
        query_string,
        payload
    )

    return {
        "api-key": DELTA_API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "User-Agent": "GH-ARCUSD-Scalper",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


# ============================================================
# GENERIC DELTA REQUEST
# ============================================================

def delta_request(method, path, params=None, body=None, auth=False):

    url = BASE_URL + path

    params = params or {}

    query_string = ""

    if params:
        query_parts = []

        for key, value in params.items():
            query_parts.append(
                f"{key}={value}"
            )

        query_string = "?" + "&".join(query_parts)

    payload = ""

    if body is not None:
        payload = json.dumps(
            body,
            separators=(",", ":")
        )

    try:

        if auth:
            headers = delta_headers(
                method,
                path,
                query_string,
                payload
            )
        else:
            headers = {
                "Accept": "application/json"
            }

        response = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            data=payload if body is not None else None,
            headers=headers,
            timeout=20
        )

        try:
            data = response.json()
        except Exception:
            data = {
                "raw_response": response.text
            }

        return response.status_code, data

    except Exception as e:

        return 0, {
            "success": False,
            "error": str(e)
        }


# ============================================================
# GET ALL DELTA PRODUCTS
# ============================================================

@st.cache_data(ttl=60)
def get_all_products():

    products = []

    after = None

    for _ in range(20):

        params = {
            "page_size": 100
        }

        if after:
            params["after"] = after

        status, data = delta_request(
            "GET",
            "/v2/products",
            params=params,
            auth=False
        )

        if status != 200:
            break

        result = data.get("result", [])

        if not result:
            break

        products.extend(result)

        meta = data.get("meta", {})

        new_after = meta.get("after")

        if not new_after or new_after == after:
            break

        after = new_after

    # केवल live/tradable perpetual futures
    tradable = []

    for p in products:

        symbol = str(
            p.get("symbol", "")
        ).upper().strip()

        product_id = p.get("id")

        product_type = str(
            p.get("product_type", "")
        ).lower()

        state = str(
            p.get("state", "")
        ).lower()

        if not symbol or not product_id:
            continue

        if symbol.startswith("C-"):
            continue

        if symbol.startswith("P-"):
            continue

        if "perpetual" not in product_type:
            continue

        if state and state not in ["live", "active"]:
            continue

        tradable.append({
            "symbol": symbol,
            "id": int(product_id),
            "product_type": product_type
        })

    # remove duplicates
    unique = {}

    for p in tradable:
        unique[p["symbol"]] = p

    return sorted(
        unique.values(),
        key=lambda x: x["symbol"]
    )


# ============================================================
# FIND PRODUCT
# ============================================================

def find_product(symbol, products):

    symbol = symbol.upper().strip()

    for p in products:
        if p["symbol"] == symbol:
            return p

    return None


# ============================================================
# GET 1 MINUTE CANDLES
# ============================================================

def get_candles(symbol):

    end_time = int(time.time())

    start_time = end_time - (
        CANDLE_LIMIT * 60
    )

    params = {
        "resolution": TIMEFRAME,
        "symbol": symbol,
        "start": start_time,
        "end": end_time
    }

    status, data = delta_request(
        "GET",
        "/v2/history/candles",
        params=params,
        auth=False
    )

    if status != 200:

        return None, (
            f"HTTP {status}: "
            f"{json.dumps(data, ensure_ascii=False)}"
        )

    candles = data.get("result", [])

    if not candles:

        return None, "Delta ने कोई candle data नहीं दिया."

    rows = []

    for c in candles:

        rows.append({
            "Time": pd.to_datetime(
                c.get("time"),
                unit="s"
            ),
            "Open": float(c.get("open", 0)),
            "High": float(c.get("high", 0)),
            "Low": float(c.get("low", 0)),
            "Close": float(c.get("close", 0)),
            "Volume": float(c.get("volume", 0))
        })

    df = pd.DataFrame(rows)

    df = df.sort_values(
        "Time"
    ).reset_index(drop=True)

    return df, None


# ============================================================
# GET LIVE TICKER
# ============================================================

def get_ticker(symbol):

    status, data = delta_request(
        "GET",
        f"/v2/tickers/{symbol}",
        auth=False
    )

    if status != 200:
        return None, data

    result = data.get("result", {})

    price = (
        result.get("close")
        or result.get("last_price")
        or result.get("spot_price")
    )

    if price is None:
        return None, data

    return float(price), None


# ============================================================
# TEST API AUTHENTICATION
# ============================================================

def test_delta_auth(product_id):

    params = {
        "product_id": product_id
    }

    status, data = delta_request(
        "GET",
        "/v2/positions",
        params=params,
        auth=True
    )

    return status, data


# ============================================================
# GET CURRENT POSITION
# ============================================================

def get_position(product_id):

    params = {
        "product_id": product_id
    }

    status, data = delta_request(
        "GET",
        "/v2/positions",
        params=params,
        auth=True
    )

    if status != 200:

        return None, (
            f"HTTP {status}: "
            f"{json.dumps(data, ensure_ascii=False)}"
        )

    result = data.get("result")

    if not result:
        return 0, None

    size = result.get("size", 0)

    try:
        return float(size), None
    except Exception:
        return 0, None


# ============================================================
# GROQ AI
# ============================================================

def run_ai(df, symbol):

    if not GROQ_API_KEY:

        return None, "GROQ_API_KEY missing"

    client = Groq(
        api_key=GROQ_API_KEY
    )

    recent = df.tail(20).copy()

    recent["Return_%"] = (
        recent["Close"]
        .pct_change()
        * 100
    )

    recent["EMA9"] = (
        recent["Close"]
        .ewm(span=9, adjust=False)
        .mean()
    )

    recent["EMA21"] = (
        recent["Close"]
        .ewm(span=21, adjust=False)
        .mean()
    )

    data_text = recent.to_string(
        index=False
    )

    prompt = f"""
You are a crypto 1-minute scalping decision engine.

Symbol: {symbol}

Analyze the latest 1-minute OHLCV data.

Rules:

1. Determine short-term momentum.
2. Compare EMA9 and EMA21.
3. Examine recent candle structure.
4. Examine volume.
5. Do NOT invent data.
6. Do NOT give explanations.

Return EXACTLY one word:

BUY

or

SELL

or

NO_TRADE

Market data:

{data_text}
"""

    models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant"
    ]

    for model in models:

        try:

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0
            )

            text = (
                response
                .choices[0]
                .message
                .content
                .strip()
                .upper()
            )

            if "BUY" == text:
                return "BUY", None

            if "SELL" == text:
                return "SELL", None

            if "NO_TRADE" == text:
                return "NO_TRADE", None

        except Exception:
            continue

    return None, "Groq AI decision failed."


# ============================================================
# REAL MARKET ORDER
# ============================================================

def place_market_order(
    product,
    side,
    size
):

    product_id = product["id"]
    symbol = product["symbol"]

    body = {
        "product_id": product_id,
        "size": int(size),
        "side": side,
        "order_type": "market_order",
        "time_in_force": "ioc",
        "reduce_only": False,
        "post_only": False,
        "client_order_id":
            f"GH_{symbol}_{side}_{int(time.time())}"
    }

    status, data = delta_request(
        "POST",
        "/v2/orders",
        body=body,
        auth=True
    )

    return status, data


# ============================================================
# BRACKET SL + TP
# ============================================================

def place_bracket(
    product,
    side,
    entry_price
):

    symbol = product["symbol"]
    product_id = product["id"]

    if side == "buy":

        sl_price = (
            entry_price
            * (1 - SL_PERCENT)
        )

        tp_price = (
            entry_price
            * (1 + TP_PERCENT)
        )

    else:

        sl_price = (
            entry_price
            * (1 + SL_PERCENT)
        )

        tp_price = (
            entry_price
            * (1 - TP_PERCENT)
        )

    # Delta bracket closes the open position.
    body = {

        "product_id": product_id,

        "stop_loss_order": {
            "order_type": "market_order",
            "stop_price": str(
                round(sl_price, 8)
            )
        },

        "take_profit_order": {
            "order_type": "market_order",
            "stop_price": str(
                round(tp_price, 8)
            )
        },

        "bracket_stop_trigger_method":
            "last_traded_price"
    }

    status, data = delta_request(
        "POST",
        "/v2/orders/bracket",
        body=body,
        auth=True
    )

    return status, data, sl_price, tp_price


# ============================================================
# EXECUTE REAL TRADE
# ============================================================

def execute_trade(
    product,
    signal,
    size
):

    symbol = product["symbol"]

    # ------------------------------------
    # Check existing position
    # ------------------------------------

    current_position, position_error = get_position(
        product["id"]
    )

    if position_error:

        return (
            False,
            f"Position check failed:\n{position_error}"
        )

    if current_position != 0:

        return (
            False,
            f"Existing position detected: "
            f"{current_position}. "
            f"New trade blocked."
        )

    # ------------------------------------
    # Direction
    # ------------------------------------

    if signal == "BUY":

        side = "buy"

    elif signal == "SELL":

        side = "sell"

    else:

        return (
            False,
            "NO_TRADE"
        )

    # ------------------------------------
    # Get latest price
    # ------------------------------------

    price, ticker_error = get_ticker(
        symbol
    )

    if price is None:

        return (
            False,
            f"Ticker error: {ticker_error}"
        )

    # ------------------------------------
    # Market order
    # ------------------------------------

    status, order_data = place_market_order(
        product,
        side,
        size
    )

    if status < 200 or status >= 300:

        return (
            False,
            "❌ MARKET ORDER FAILED\n\n"
            + json.dumps(
                order_data,
                indent=2,
                ensure_ascii=False
            )
        )

    # ------------------------------------
    # Bracket
    # ------------------------------------

    time.sleep(1)

    bracket_status, bracket_data, sl, tp = (
        place_bracket(
            product,
            side,
            price
        )
    )

    if bracket_status < 200 or bracket_status >= 300:

        return (
            True,
            "⚠️ MARKET ORDER SUCCESSFUL\n"
            "लेकिन BRACKET SL/TP लगाने में समस्या हुई.\n\n"
            + json.dumps(
                bracket_data,
                indent=2,
                ensure_ascii=False
            )
        )

    return (
        True,
        f"""
✅ REAL {signal} EXECUTED

🪙 Symbol: {symbol}
📌 Side: {side.upper()}
💰 Approx Entry: {price}
📦 Size: {size}

🛑 SL: {sl:.8f}
🎯 TP: {tp:.8f}

✅ Delta Bracket SL/TP submitted.
"""
    )


# ============================================================
# SESSION STATE
# ============================================================

if "last_trade_time" not in st.session_state:
    st.session_state.last_trade_time = 0


# ============================================================
# LOAD PRODUCTS
# ============================================================

with st.spinner("Delta की पूरी product list लोड हो रही है..."):

    products = get_all_products()


if not products:

    st.error(
        "❌ Delta से tradable perpetual products नहीं मिले."
    )

    st.stop()


# ============================================================
# SYMBOL SELECT
# ARCUSD DEFAULT
# ============================================================

symbols = [
    p["symbol"]
    for p in products
]

if DEFAULT_SYMBOL in symbols:

    default_index = symbols.index(
        DEFAULT_SYMBOL
    )

else:

    default_index = 0


selected_symbol = st.selectbox(
    "🪙 Crypto",
    symbols,
    index=default_index
)


product = find_product(
    selected_symbol,
    products
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ Scalper Settings")

order_size = st.sidebar.number_input(
    "Order Size",
    min_value=1,
    value=DEFAULT_ORDER_SIZE,
    step=1
)

st.sidebar.write(
    f"SL: {SL_PERCENT * 100:.2f}%"
)

st.sidebar.write(
    f"TP: {TP_PERCENT * 100:.2f}%"
)

st.sidebar.write(
    f"Cooldown: {COOLDOWN_SECONDS} sec"
)

st.sidebar.warning(
    "⚠️ LIVE TRADING ENABLED"
)


# ============================================================
# PRODUCT INFO
# ============================================================

col1, col2, col3 = st.columns(3)

col1.metric(
    "Symbol",
    selected_symbol
)

col2.metric(
    "Product ID",
    product["id"]
)

col3.metric(
    "Products",
    len(products)
)


# ============================================================
# API STATUS
# ============================================================

st.subheader("🔐 Delta API")

if DELTA_API_KEY and DELTA_API_SECRET:

    st.success(
        "DELTA_API_KEY और DELTA_API_SECRET मिले."
    )

else:

    st.error(
        "❌ Render Environment Variables missing."
    )

    st.stop()


# ============================================================
# AUTH TEST
# ============================================================

if st.button("🔐 Test Delta Authentication"):

    with st.spinner("Delta authentication test..."):

        status, result = test_delta_auth(
            product["id"]
        )

    if status == 200:

        st.success(
            "✅ Delta API Authentication सफल है."
        )

        st.json(result)

    else:

        st.error(
            f"❌ Delta Authentication Failed — HTTP {status}"
        )

        st.code(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )

        st.stop()


# ============================================================
# FETCH DATA
# ============================================================

st.subheader(
    f"📊 {selected_symbol} — 1 Minute Real Market Data"
)

df, candle_error = get_candles(
    selected_symbol
)

if df is None:

    st.error(
        f"❌ Candle error: {candle_error}"
    )

    st.stop()


st.dataframe(
    df,
    use_container_width=True
)


# ============================================================
# LIVE PRICE
# ============================================================

live_price, ticker_error = get_ticker(
    selected_symbol
)

if live_price:

    st.metric(
        "Live Price",
        live_price
    )


# ============================================================
# AI ANALYSIS
# ============================================================

st.subheader("🤖 Groq Scalping AI")

if st.button(
    "⚡ ANALYZE + REAL TRADE"
):

    now = time.time()

    # cooldown
    if (
        now
        - st.session_state.last_trade_time
        < COOLDOWN_SECONDS
    ):

        remaining = int(
            COOLDOWN_SECONDS
            - (
                now
                - st.session_state.last_trade_time
            )
        )

        st.warning(
            f"⏳ Cooldown active: "
            f"{remaining} seconds"
        )

        st.stop()

    with st.spinner(
        f"{selected_symbol} का 1m scalp analysis..."
    ):

        signal, ai_error = run_ai(
            df,
            selected_symbol
        )

    if ai_error:

        st.error(
            f"❌ AI Error: {ai_error}"
        )

        st.stop()

    st.info(
        f"🤖 AI SIGNAL: **{signal}**"
    )

    if signal == "NO_TRADE":

        st.warning(
            "⏳ AI ने NO_TRADE दिया."
        )

        st.stop()

    # ----------------------------------------
    # REAL TRADE
    # ----------------------------------------

    with st.spinner(
        "🚨 REAL DELTA ORDER भेजा जा रहा है..."
    ):

        success, message = execute_trade(
            product,
            signal,
            order_size
        )

    if success:

        st.success(
            message
        )

        st.session_state.last_trade_time = (
            time.time()
        )

    else:

        st.error(
            message
        )


# ============================================================
# REFRESH
# ============================================================

st.divider()

if st.button("🔄 Refresh Market Data"):

    st.cache_data.clear()
    st.rerun()
