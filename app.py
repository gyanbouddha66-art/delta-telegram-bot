हाँ Sir. नीचे पूरा updated app.py है। इसमें:
✅ GPT-OSS 120B
✅ JSON Schema + reasoning_effort=low fix
✅ Delta India API
✅ BUY / SELL / NO TRADE
✅ Market Order
✅ Bracket TP + SL
✅ AI Chat
✅ ARCUSD सहित symbol selection
✅ Exact error display
✅ Syntax-safe try/except
✅ Chat और Trading दोनों अलग-अलग काम करेंगे
पुरानी app.py पूरी हटाकर यह पूरा code paste करें।
# ============================================================
# ⚡ GYAN AI PRO
# Delta Exchange India + Groq GPT-OSS 120B
# AI SCALPING + MARKET ORDER + BRACKET TP/SL + CHAT
# ============================================================

import os
import json
import time
import hmac
import hashlib
from urllib.parse import urlencode

import requests
import streamlit as st


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="GYAN AI Pro",
    page_icon="⚡",
    layout="wide"
)


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://api.india.delta.exchange"

GROQ_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

GROQ_MODEL = "openai/gpt-oss-120b"

DELTA_API_KEY = os.getenv("DELTA_API_KEY", "").strip()
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

LOT_SIZE = 1

SL_PERCENT = 0.005
TP_PERCENT = 0.010

REQUEST_TIMEOUT = 20


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_signal" not in st.session_state:
    st.session_state.last_signal = None

if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = ""

if "last_order" not in st.session_state:
    st.session_state.last_order = None

if "last_bracket" not in st.session_state:
    st.session_state.last_bracket = None

if "last_error" not in st.session_state:
    st.session_state.last_error = ""


# ============================================================
# HEADER
# ============================================================

st.title("⚡ GYAN AI Pro")

st.caption(
    "Delta Exchange India • AI Scalping • TP/SL • GPT-OSS 120B"
)


# ============================================================
# STATUS
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:
    if DELTA_API_KEY and DELTA_API_SECRET:
        st.success("Delta API: READY")
    else:
        st.error("Delta API: NOT READY")

with col2:
    if GROQ_API_KEY:
        st.success("Groq AI: READY")
    else:
        st.error("Groq AI: NOT READY")

with col3:
    st.info(f"Model: {GROQ_MODEL}")


# ============================================================
# DELTA SIGNATURE
# ============================================================

def delta_signature(
    method,
    timestamp,
    path,
    query_string,
    body_string
):
    message = (
        method.upper()
        + str(timestamp)
        + path
        + query_string
        + body_string
    )

    return hmac.new(
        DELTA_API_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()


# ============================================================
# DELTA REQUEST
# ============================================================

def delta_request(
    method,
    path,
    params=None,
    body=None,
    auth=False
):

    method = method.upper()

    params = params or {}
    body = body or {}

    query_string = ""

    if params:
        query_string = "?" + urlencode(
            params,
            doseq=True
        )

    body_string = ""

    if body:
        body_string = json.dumps(
            body,
            separators=(",", ":")
        )

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "GYAN-AI-PRO"
    }

    if auth:

        if not DELTA_API_KEY:
            raise Exception(
                "DELTA_API_KEY missing"
            )

        if not DELTA_API_SECRET:
            raise Exception(
                "DELTA_API_SECRET missing"
            )

        timestamp = int(time.time())

        signature = delta_signature(
            method,
            timestamp,
            path,
            query_string,
            body_string
        )

        headers.update({
            "api-key": DELTA_API_KEY,
            "timestamp": str(timestamp),
            "signature": signature
        })

    url = BASE_URL + path + query_string

    try:

        response = requests.request(
            method,
            url,
            headers=headers,
            data=body_string if body else None,
            timeout=REQUEST_TIMEOUT
        )

    except requests.exceptions.Timeout:
        raise Exception(
            "Delta API timeout"
        )

    except requests.exceptions.ConnectionError as e:
        raise Exception(
            f"Delta connection error: {e}"
        )

    except Exception as e:
        raise Exception(
            f"Delta request error: {e}"
        )

    text = response.text

    try:
        data = response.json()
    except Exception:
        raise Exception(
            f"Delta HTTP {response.status_code}: "
            f"{text[:1000]}"
        )

    if response.status_code >= 400:
        raise Exception(
            f"Delta HTTP {response.status_code}: "
            f"{data}"
        )

    if isinstance(data, dict):

        if data.get("success") is False:
            raise Exception(
                f"Delta API Error: {data}"
            )

    return data


# ============================================================
# GET ALL PRODUCTS
# ============================================================

@st.cache_data(ttl=60)
def get_all_products():

    products = []

    page = 1

    while True:

        data = delta_request(
            "GET",
            "/v2/products",
            params={
                "page_size": 100,
                "page": page
            },
            auth=False
        )

        result = data.get(
            "result",
            []
        )

        if not result:
            break

        products.extend(result)

        if len(result) < 100:
            break

        page += 1

        if page > 50:
            break

    return products


# ============================================================
# SYMBOLS
# ============================================================

def get_all_symbols():

    products = get_all_products()

    symbols = []

    for p in products:

        symbol = p.get("symbol", "")

        contract_type = str(
            p.get("contract_type", "")
        ).lower()

        product_type = str(
            p.get("product_type", "")
        ).lower()

        if not symbol:
            continue

        # Exclude options
        if "option" in contract_type:
            continue

        if "option" in product_type:
            continue

        # Prefer perpetuals
        if (
            "perpetual" in contract_type
            or "perpetual" in product_type
            or p.get("settling_asset_symbol")
        ):
            symbols.append(symbol)

    # fallback
    if not symbols:

        for p in products:

            symbol = p.get("symbol")

            if symbol:
                symbols.append(symbol)

    return sorted(
        list(set(symbols))
    )


# ============================================================
# PRODUCT
# ============================================================

def get_product(symbol):

    products = get_all_products()

    for p in products:

        if str(
            p.get("symbol", "")
        ).upper() == str(symbol).upper():

            return p

    raise Exception(
        f"Product not found: {symbol}"
    )


# ============================================================
# TICKER
# ============================================================

def get_ticker(symbol):

    data = delta_request(
        "GET",
        "/v2/tickers",
        params={
            "symbol": symbol
        },
        auth=False
    )

    result = data.get(
        "result",
        []
    )

    if isinstance(result, list):

        if not result:
            raise Exception(
                f"No ticker data for {symbol}"
            )

        return result[0]

    if isinstance(result, dict):
        return result

    raise Exception(
        f"Invalid ticker response: {data}"
    )


# ============================================================
# CANDLES
# ============================================================

def get_candles(
    symbol,
    resolution="1m",
    limit=100
):

    data = delta_request(
        "GET",
        "/v2/history/candles",
        params={
            "symbol": symbol,
            "resolution": resolution,
            "limit": limit
        },
        auth=False
    )

    result = data.get(
        "result",
        []
    )

    if not result:
        return []

    return result


# ============================================================
# POSITION
# ============================================================

def get_position(symbol):

    data = delta_request(
        "GET",
        "/v2/positions",
        params={
            "product_symbol": symbol
        },
        auth=True
    )

    result = data.get(
        "result",
        []
    )

    if isinstance(result, list):

        for p in result:

            ps = str(
                p.get(
                    "product_symbol",
                    ""
                )
            ).upper()

            if ps == symbol.upper():

                size = p.get(
                    "size",
                    0
                )

                try:
                    if abs(float(size)) > 0:
                        return p
                except Exception:
                    pass

        return None

    if isinstance(result, dict):

        size = result.get(
            "size",
            0
        )

        try:
            if abs(float(size)) > 0:
                return result
        except Exception:
            pass

    return None


# ============================================================
# PRICE PRECISION
# ============================================================

def format_price(
    price,
    product
):

    try:

        tick_size = float(
            product.get(
                "tick_size",
                0.0001
            )
        )

        if tick_size <= 0:
            return str(price)

        decimals = 0

        value = tick_size

        while value < 1 and decimals < 12:
            value *= 10
            decimals += 1

        rounded = round(
            float(price),
            decimals
        )

        return f"{rounded:.{decimals}f}"

    except Exception:
        return str(price)


# ============================================================
# GROQ REQUEST
# ============================================================

def groq_request(
    messages,
    response_format=None,
    max_completion_tokens=512,
    reasoning_effort="low"
):

    if not GROQ_API_KEY:
        raise Exception(
            "GROQ_API_KEY missing"
        )

    headers = {
        "Authorization":
            f"Bearer {GROQ_API_KEY}",
        "Content-Type":
            "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,

        "reasoning_effort":
            reasoning_effort,

        "max_completion_tokens":
            max_completion_tokens,

        "temperature": 0
    }

    if response_format is not None:

        payload[
            "response_format"
        ] = response_format

    try:

        response = requests.post(
            GROQ_URL,
            headers=headers,
            json=payload,
            timeout=45
        )

    except requests.exceptions.Timeout:
        raise Exception(
            "Groq timeout"
        )

    except requests.exceptions.ConnectionError as e:
        raise Exception(
            f"Groq connection error: {e}"
        )

    except Exception as e:
        raise Exception(
            f"Groq request error: {e}"
        )

    if response.status_code != 200:

        raise Exception(
            f"Groq HTTP {response.status_code}: "
            f"{response.text[:2000]}"
        )

    try:

        data = response.json()

    except Exception:

        raise Exception(
            "Groq returned invalid JSON response: "
            + response.text[:2000]
        )

    if not data.get("choices"):

        raise Exception(
            f"Groq returned no choices: {data}"
        )

    message = data[
        "choices"
    ][0].get(
        "message",
        {}
    )

    content = message.get(
        "content",
        ""
    )

    if not content:

        raise Exception(
            f"Groq returned empty content: {data}"
        )

    return content


# ============================================================
# AI SIGNAL
# ============================================================

def get_ai_signal(
    symbol,
    ticker,
    candles
):

    price = ticker.get(
        "close",
        ticker.get(
            "last_price",
            ticker.get(
                "mark_price",
                0
            )
        )
    )

    mark_price = ticker.get(
        "mark_price",
        price
    )

    volume = ticker.get(
        "volume",
        ticker.get(
            "turnover",
            0
        )
    )

    # Keep only recent candles.
    # This prevents unnecessary huge prompts.
    recent = candles[-30:]

    compact_candles = []

    for c in recent:

        try:

            if isinstance(c, dict):

                compact_candles.append({
                    "time": c.get("time"),
                    "open": c.get("open"),
                    "high": c.get("high"),
                    "low": c.get("low"),
                    "close": c.get("close"),
                    "volume": c.get("volume")
                })

            elif isinstance(c, list):

                compact_candles.append(c)

        except Exception:
            continue

    market_data = {
        "symbol": symbol,
        "price": price,
        "mark_price": mark_price,
        "volume": volume,
        "recent_candles": compact_candles
    }

    messages = [

        {
            "role": "system",

            "content": (
                "You are a FAST crypto scalping "
                "signal engine. "
                "Analyze market data carefully. "
                "Return ONLY the required JSON. "
                "Keep analysis short. "
                "Never output markdown."
            )
        },

        {
            "role": "user",

            "content": f"""
Symbol: {symbol}

LIVE MARKET DATA:
{json.dumps(
    market_data,
    ensure_ascii=False
)}

Return exactly one signal.

Allowed values:
BUY
SELL
NO TRADE

Return ONLY this JSON structure:
{{
  "signal": "BUY",
  "analysis": "short reason"
}}

The analysis must be short.
"""
        }
    ]

    response_format = {

        "type": "json_schema",

        "json_schema": {

            "name": "trading_signal",

            "strict": True,

            "schema": {

                "type": "object",

                "properties": {

                    "signal": {
                        "type": "string",
                        "enum": [
                            "BUY",
                            "SELL",
                            "NO TRADE"
                        ]
                    },

                    "analysis": {
                        "type": "string"
                    }
                },

                "required": [
                    "signal",
                    "analysis"
                ],

                "additionalProperties": False
            }
        }
    }

    content = groq_request(
        messages=messages,
        response_format=response_format,
        max_completion_tokens=512,
        reasoning_effort="low"
    )

    try:

        data = json.loads(content)

    except json.JSONDecodeError as e:

        raise Exception(
            f"AI JSON Parse Error: {e}\n"
            f"Raw AI response:\n{content}"
        )

    signal = str(
        data.get(
            "signal",
            "NO TRADE"
        )
    ).upper().strip()

    analysis = str(
        data.get(
            "analysis",
            ""
        )
    ).strip()

    if signal not in [
        "BUY",
        "SELL",
        "NO TRADE"
    ]:

        signal = "NO TRADE"

    return {
        "signal": signal,
        "analysis": analysis
    }


# ============================================================
# MARKET ORDER
# ============================================================

def place_market_order(
    symbol,
    side,
    size
):

    side = side.lower()

    if side not in [
        "buy",
        "sell"
    ]:
        raise Exception(
            f"Invalid order side: {side}"
        )

    body = {

        "product_symbol": symbol,

        "order_type": "market_order",

        "size": int(size),

        "side": side
    }

    return delta_request(
        "POST",
        "/v2/orders",
        body=body,
        auth=True
    )


# ============================================================
# ENTRY PRICE
# ============================================================

def get_entry_price(
    symbol,
    order_result,
    fallback_price
):

    # Try common response locations.

    candidates = []

    if isinstance(order_result, dict):

        result = order_result.get(
            "result",
            {}
        )

        if isinstance(result, dict):

            candidates.extend([
                result.get("average_fill_price"),
                result.get("avg_fill_price"),
                result.get("fill_price"),
                result.get("price"),
                result.get("limit_price")
            ])

    for value in candidates:

        try:

            if value is not None:

                price = float(value)

                if price > 0:
                    return price

        except Exception:
            pass

    # Position fallback
    try:

        position = get_position(
            symbol
        )

        if position:

            for key in [
                "entry_price",
                "average_entry_price",
                "avg_entry_price"
            ]:

                try:

                    value = position.get(
                        key
                    )

                    if value is not None:

                        price = float(value)

                        if price > 0:
                            return price

                except Exception:
                    pass

    except Exception:
        pass

    return float(fallback_price)


# ============================================================
# BRACKET TP + SL
# ============================================================

def place_sl_tp_orders(
    symbol,
    entry_side,
    entry_price
):

    product = get_product(
        symbol
    )

    entry_price = float(
        entry_price
    )

    if entry_side.lower() == "buy":

        stop_price = (
            entry_price
            * (1 - SL_PERCENT)
        )

        target_price = (
            entry_price
            * (1 + TP_PERCENT)
        )

    else:

        stop_price = (
            entry_price
            * (1 + SL_PERCENT)
        )

        target_price = (
            entry_price
            * (1 - TP_PERCENT)
        )

    stop_text = format_price(
        stop_price,
        product
    )

    target_text = format_price(
        target_price,
        product
    )

    body = {

        "product_symbol": symbol,

        "stop_loss_order": {

            "order_type":
                "market_order",

            "stop_price":
                stop_text
        },

        "take_profit_order": {

            "order_type":
                "limit_order",

            "stop_price":
                target_text,

            "limit_price":
                target_text
        },

        "bracket_stop_trigger_method":
            "last_traded_price"
    }

    data = delta_request(
        "POST",
        "/v2/orders/bracket",
        body=body,
        auth=True
    )

    return {
        "response": data,
        "entry_price": entry_price,
        "stop_price": stop_text,
        "target_price": target_text
    }


# ============================================================
# CHAT
# ============================================================

def ai_chat(
    symbol,
    user_message,
    ticker
):

    price = ticker.get(
        "close",
        ticker.get(
            "last_price",
            0
        )
    )

    mark = ticker.get(
        "mark_price",
        0
    )

    volume = ticker.get(
        "volume",
        0
    )

    system_prompt = f"""
You are GYAN AI Pro.

You are assisting with crypto market analysis.

Current symbol:
{symbol}

Current price:
{price}

Mark price:
{mark}

Volume:
{volume}

Answer the user's question clearly in Hindi/Hinglish
unless the user asks for another language.

Do not claim certainty about future prices.

Give practical market-analysis information.
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # Last 10 messages only.
    for msg in st.session_state.messages[-10:]:

        role = msg.get(
            "role",
            "user"
        )

        content = msg.get(
            "content",
            ""
        )

        if role in [
            "user",
            "assistant"
        ]:

            messages.append({
                "role": role,
                "content": content
            })

    messages.append({
        "role": "user",
        "content": user_message
    })

    return groq_request(
        messages=messages,
        response_format=None,
        max_completion_tokens=700,
        reasoning_effort="low"
    )


# ============================================================
# MAIN TABS
# ============================================================

tab1, tab2 = st.tabs([
    "⚡ Scalping Terminal",
    "🤖 AI Chat"
])


# ============================================================
# TAB 1
# ============================================================

with tab1:

    st.subheader(
        "### ⚡ AI Scalping Terminal"
    )

    # --------------------------------------------------------
    # CONTROLS
    # --------------------------------------------------------

    try:

        symbols = get_all_symbols()

    except Exception as e:

        symbols = [
            "ARCUSD"
        ]

        st.warning(
            f"Symbol list load failed: {e}"
        )

    if "ARCUSD" in symbols:

        default_index = symbols.index(
            "ARCUSD"
        )

    else:

        default_index = 0

    col1, col2, col3 = st.columns(3)

    with col1:

        symbol = st.selectbox(
            "Trading Symbol",
            symbols,
            index=default_index
        )

    with col2:

        auto_trade = st.checkbox(
            "Auto Trade",
            value=False
        )

    with col3:

        refresh_seconds = st.number_input(
            "Refresh Interval (seconds)",
            min_value=5,
            max_value=60,
            value=6,
            step=1
        )

    # --------------------------------------------------------
    # LIVE MARKET
    # --------------------------------------------------------

    try:

        ticker = get_ticker(
            symbol
        )

        price = ticker.get(
            "close",
            ticker.get(
                "last_price",
                0
            )
        )

        mark_price = ticker.get(
            "mark_price",
            price
        )

        volume = ticker.get(
            "volume",
            ticker.get(
                "turnover",
                0
            )
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Price",
                str(price)
            )

        with c2:
            st.metric(
                "Mark Price",
                str(mark_price)
            )

        with c3:
            st.metric(
                "Volume",
                str(volume)
            )

        # ----------------------------------------------------
        # POSITION
        # ----------------------------------------------------

        position = None

        if DELTA_API_KEY and DELTA_API_SECRET:

            try:

                position = get_position(
                    symbol
                )

            except Exception as e:

                st.warning(
                    f"Position check failed: {e}"
                )

        if position:

            st.warning(
                "⚠️ Existing position detected"
            )

            pside = position.get(
                "side",
                ""
            )

            psize = position.get(
                "size",
                0
            )

            pentry = position.get(
                "entry_price",
                position.get(
                    "average_entry_price",
                    ""
                )
            )

            pc1, pc2, pc3 = st.columns(3)

            with pc1:
                st.write(
                    f"Side: **{pside}**"
                )

            with pc2:
                st.write(
                    f"Size: **{psize}**"
                )

            with pc3:
                st.write(
                    f"Entry: **{pentry}**"
                )

        # ----------------------------------------------------
        # SIGNAL BUTTON
        # ----------------------------------------------------

        signal_button = st.button(
            "⚡ GET AI SIGNAL",
            type="primary",
            use_container_width=True
        )

        if signal_button:

            if not GROQ_API_KEY:

                st.error(
                    "GROQ_API_KEY missing"
                )

            elif not DELTA_API_KEY:

                st.error(
                    "DELTA_API_KEY missing"
                )

            else:

                try:

                    # ------------------------------------------------
                    # CANDLES
                    # ------------------------------------------------

                    candles = get_candles(
                        symbol,
                        resolution="1m",
                        limit=100
                    )

                    if len(candles) < 5:

                        raise Exception(
                            "Not enough candle data"
                        )

                    # ------------------------------------------------
                    # AI
                    # ------------------------------------------------

                    with st.spinner(
                        "🤖 GPT-OSS 120B analysing..."
                    ):

                        ai_result = get_ai_signal(
                            symbol,
                            ticker,
                            candles
                        )

                    signal = ai_result[
                        "signal"
                    ]

                    analysis = ai_result[
                        "analysis"
                    ]

                    st.session_state.last_signal = signal
                    st.session_state.last_analysis = analysis

                    # ------------------------------------------------
                    # SIGNAL DISPLAY
                    # ------------------------------------------------

                    if signal == "BUY":

                        st.success(
                            "🟢 AI SIGNAL: BUY"
                        )

                    elif signal == "SELL":

                        st.error(
                            "🔴 AI SIGNAL: SELL"
                        )

                    else:

                        st.warning(
                            "⚪ AI SIGNAL: NO TRADE"
                        )

                    st.info(
                        f"AI Analysis: {analysis}"
                    )

                    # ------------------------------------------------
                    # NO TRADE
                    # ------------------------------------------------

                    if signal == "NO TRADE":

                        st.info(
                            "No order placed."
                        )

                    # ------------------------------------------------
                    # TRADE
                    # ------------------------------------------------

                    else:

                        if position:

                            st.warning(
                                "Existing position detected. "
                                "New order skipped."
                            )

                        elif not auto_trade:

                            st.info(
                                "Auto Trade OFF — "
                                "signal generated only."
                            )

                            st.warning(
                                "Order लगाने के लिए "
                                "Auto Trade ON करके फिर "
                                "GET AI SIGNAL दबाएँ."
                            )

                        else:

                            order_side = (
                                "buy"
                                if signal == "BUY"
                                else "sell"
                            )

                            # ----------------------------------------
                            # MARKET ORDER
                            # ----------------------------------------

                            with st.spinner(
                                "📡 Placing market order..."
                            ):

                                order_result = (
                                    place_market_order(
                                        symbol,
                                        order_side,
                                        LOT_SIZE
                                    )
                                )

                            st.session_state.last_order = (
                                order_result
                            )

                            st.success(
                                "✅ MARKET ORDER PLACED"
                            )

                            st.json(
                                order_result
                            )

                            # ----------------------------------------
                            # ENTRY PRICE
                            # ----------------------------------------

                            entry_price = (
                                get_entry_price(
                                    symbol,
                                    order_result,
                                    price
                                )
                            )

                            st.write(
                                f"Entry Price: "
                                f"**{entry_price}**"
                            )

                            # ----------------------------------------
                            # WAIT FOR POSITION
                            # ----------------------------------------

                            time.sleep(1)

                            # ----------------------------------------
                            # BRACKET TP/SL
                            # ----------------------------------------

                            try:

                                with st.spinner(
                                    "🎯 Attaching TP + SL..."
                                ):

                                    bracket = (
                                        place_sl_tp_orders(
                                            symbol,
                                            order_side,
                                            entry_price
                                        )
                                    )

                                st.session_state.last_bracket = (
                                    bracket
                                )

                                st.success(
                                    "🎯 TP + 🛑 SL ATTACHED"
                                )

                                bc1, bc2 = st.columns(2)

                                with bc1:

                                    st.success(
                                        "🛑 Stop Loss\n\n"
                                        + str(
                                            bracket[
                                                "stop_price"
                                            ]
                                        )
                                    )

                                with bc2:

                                    st.success(
                                        "🎯 Take Profit\n\n"
                                        + str(
                                            bracket[
                                                "target_price"
                                            ]
                                        )
                                    )

                                st.json(
                                    bracket[
                                        "response"
                                    ]
                                )

                            except Exception as e:

                                st.error(
                                    "⚠️ MARKET ORDER "
                                    "PLACED BUT TP/SL FAILED"
                                )

                                st.code(
                                    f"{type(e).__name__}: {e}"
                                )

                except Exception as e:

                    st.error(
                        "❌ Trading / AI Error"
                    )

                    st.code(
                        f"{type(e).__name__}: {e}"
                    )

                    st.session_state.last_error = str(
                        e
                    )

        # --------------------------------------------------------
        # LAST SIGNAL
        # --------------------------------------------------------

        if st.session_state.last_signal:

            st.divider()

            st.subheader(
                "Last AI Signal"
            )

            lc1, lc2 = st.columns(2)

            with lc1:

                st.write(
                    f"Signal: "
                    f"**{st.session_state.last_signal}**"
                )

            with lc2:

                st.write(
                    "Analysis:"
                )

                st.write(
                    st.session_state.last_analysis
                )

        # --------------------------------------------------------
        # LAST ORDER
        # --------------------------------------------------------

        if st.session_state.last_order:

            with st.expander(
                "📦 Last Market Order"
            ):

                st.json(
                    st.session_state.last_order
                )

        # --------------------------------------------------------
        # LAST BRACKET
        # --------------------------------------------------------

        if st.session_state.last_bracket:

            with st.expander(
                "🎯 Last TP / SL"
            ):

                st.write(
                    "Entry:",
                    st.session_state.last_bracket.get(
                        "entry_price"
                    )
                )

                st.write(
                    "Stop Loss:",
                    st.session_state.last_bracket.get(
                        "stop_price"
                    )
                )

                st.write(
                    "Take Profit:",
                    st.session_state.last_bracket.get(
                        "target_price"
                    )
                )

    except Exception as e:

        st.error(
            "❌ Trading / AI Error"
        )

        st.code(
            f"{type(e).__name__}: {e}"
        )

    # ------------------------------------------------------------
    # AUTO REFRESH
    # ------------------------------------------------------------

    if auto_trade:

        st.warning(
            "⚠️ Auto Trade ON — "
            "real orders can be placed."
        )

        time.sleep(
            int(refresh_seconds)
        )

        st.rerun()


# ============================================================
# TAB 2 — AI CHAT
# ============================================================

with tab2:

    st.subheader(
        "🤖 AI Chat"
    )

    try:

        chat_symbols = get_all_symbols()

    except Exception:

        chat_symbols = [
            "ARCUSD"
        ]

    if "ARCUSD" in chat_symbols:

        chat_default = chat_symbols.index(
            "ARCUSD"
        )

    else:

        chat_default = 0

    chat_symbol = st.selectbox(
        "Chat Symbol",
        chat_symbols,
        index=chat_default,
        key="chat_symbol"
    )

    # --------------------------------------------------------
    # DISPLAY HISTORY
    # --------------------------------------------------------

    for message in st.session_state.messages:

        role = message.get(
            "role",
            "assistant"
        )

        content = message.get(
            "content",
            ""
        )

        with st.chat_message(role):

            st.markdown(
                content
            )

    # --------------------------------------------------------
    # CHAT INPUT
    # --------------------------------------------------------

    user_prompt = st.chat_input(
        f"{chat_symbol} के बारे में पूछें..."
    )

    if user_prompt:

        st.session_state.messages.append({
            "role": "user",
            "content": user_prompt
        })

        with st.chat_message(
            "user"
        ):

            st.markdown(
                user_prompt
            )

        try:

            chat_ticker = get_ticker(
                chat_symbol
            )

            with st.chat_message(
                "assistant"
            ):

                with st.spinner(
                    "🤖 AI सोच रहा है..."
                ):

                    answer = ai_chat(
                        chat_symbol,
                        user_prompt,
                        chat_ticker
                    )

                st.markdown(
                    answer
                )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

        except Exception as e:

            error_text = (
                "❌ Chat Error\n\n"
                f"`{type(e).__name__}: {e}`"
            )

            with st.chat_message(
                "assistant"
            ):

                st.error(
                    error_text
                )

            st.session_state.messages.append({
                "role": "assistant",
                "content": error_text
            })


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "GYAN AI Pro • Delta Exchange India • "
    "Groq GPT-OSS 120B"
)
Render में Environment Variables
ये तीनों मौजूद होने चाहिए:
DELTA_API_KEY
DELTA_API_SECRET
GROQ_API_KEY
और कोई पुराना llama-3.1-8b-instant नहीं रखना है।
सबसे जरूरी बदलाव
इस version में Signal के लिए:
"reasoning_effort": "low"
और:
"max_completion_tokens": 512
तथा strict JSON schema है। इससे तुम्हारा आया हुआ:
max completion tokens reached before generating
a valid document
वाला error target किया गया है।
पहले Auto Trade OFF रखकर GET AI SIGNAL दबाना। Signal सही BUY/SELL/NO TRADE आने लगे तभी Auto Trade ON करना—क्योंकि ON होने पर वास्तविक Delta market order लगाया जा सकता है।
