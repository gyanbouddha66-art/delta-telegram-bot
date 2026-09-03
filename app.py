import os
import time
import json
import hmac
import hashlib
from urllib.parse import urlencode

import requests
import streamlit as st


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://api.india.delta.exchange"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"

LOT_SIZE = 1

SL_PERCENT = 0.005
TP_PERCENT = 0.010

REQUEST_TIMEOUT = 20


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="GYAN AI Pro",
    page_icon="⚡",
    layout="wide"
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

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_signal" not in st.session_state:
    st.session_state.last_signal = ""

if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = ""

if "last_order" not in st.session_state:
    st.session_state.last_order = None

if "last_bracket" not in st.session_state:
    st.session_state.last_bracket = None


# ============================================================
# DELTA REQUEST
# ============================================================

def delta_request(method, path, params=None, body=None, auth=False):

    params = params or {}
    body = body or {}

    method = method.upper()

    body_text = ""

    if body:
        body_text = json.dumps(
            body,
            separators=(",", ":")
        )

    query_string = ""

    if params:
        query_string = "?" + urlencode(params)

    timestamp = str(int(time.time()))

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "GYAN-AI-PRO"
    }

    if auth:

        if not DELTA_API_KEY or not DELTA_API_SECRET:
            raise Exception(
                "Delta API Key या Secret missing है।"
            )

        message = (
            method
            + timestamp
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
        headers["timestamp"] = timestamp
        headers["signature"] = signature

    try:

        response = requests.request(
            method,
            BASE_URL + path + query_string,
            headers=headers,
            data=body_text if body else None,
            timeout=REQUEST_TIMEOUT
        )

    except requests.exceptions.Timeout:

        raise Exception(
            "Delta API timeout हो गया।"
        )

    except requests.exceptions.ConnectionError:

        raise Exception(
            "Delta API connection error।"
        )

    except Exception as e:

        raise Exception(
            f"Delta request error: {e}"
        )

    try:

        data = response.json()

    except Exception:

        raise Exception(
            f"Delta HTTP {response.status_code}: "
            f"{response.text[:1500]}"
        )

    if response.status_code >= 400:

        raise Exception(
            f"HTTP {response.status_code}: {data}"
        )

    if isinstance(data, dict):

        if data.get("success") is False:

            raise Exception(
                str(data)
            )

    return data


# ============================================================
# PRODUCTS
# ============================================================

@st.cache_data(ttl=300)
def get_all_products():

    products = []
    after = None

    for _ in range(20):

        params = {
            "page_size": 100
        }

        if after:
            params["after"] = after

        try:

            data = delta_request(
                "GET",
                "/v2/products",
                params=params
            )

        except Exception:

            break

        result = data.get(
            "result",
            []
        )

        if not result:
            break

        products.extend(result)

        after = data.get(
            "meta",
            {}
        ).get(
            "after"
        )

        if not after:
            break

    return products


@st.cache_data(ttl=300)
def get_all_symbols():

    symbols = []

    for p in get_all_products():

        symbol = str(
            p.get("symbol", "")
        ).upper().strip()

        product_type = str(
            p.get("product_type", "")
        ).lower()

        state = str(
            p.get("state", "")
        ).lower()

        if not symbol:
            continue

        if "perpetual" not in product_type:
            continue

        if symbol.startswith("C-"):
            continue

        if symbol.startswith("P-"):
            continue

        if state and state not in (
            "live",
            "active"
        ):
            continue

        symbols.append(symbol)

    return sorted(set(symbols))


def get_product(symbol):

    symbol = symbol.upper().strip()

    for product in get_all_products():

        if (
            str(product.get("symbol", ""))
            .upper()
            .strip()
            == symbol
        ):
            return product

    return None


# ============================================================
# TICKER
# ============================================================

def get_ticker(symbol):

    data = delta_request(
        "GET",
        f"/v2/tickers/{symbol}"
    )

    return data.get(
        "result",
        {}
    )


# ============================================================
# CANDLES
# ============================================================

def get_candles(symbol):

    end_time = int(time.time())
    start_time = end_time - 1800

    data = delta_request(
        "GET",
        "/v2/history/candles",
        params={
            "resolution": "1m",
            "symbol": symbol,
            "start": start_time,
            "end": end_time
        }
    )

    return data.get(
        "result",
        []
    )


# ============================================================
# GROQ
# ============================================================

def groq_request(
    messages,
    max_tokens=1000,
    temperature=0.3,
    response_format=None
):

    if not GROQ_API_KEY:

        raise Exception(
            "GROQ_API_KEY missing है। "
            "Render → Environment में GROQ_API_KEY डालें।"
        )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    if response_format:

        payload["response_format"] = response_format

    try:

        response = requests.post(
            GROQ_URL,
            headers=headers,
            json=payload,
            timeout=45
        )

    except requests.exceptions.Timeout:

        raise Exception(
            "Groq API timeout।"
        )

    except requests.exceptions.ConnectionError:

        raise Exception(
            "Groq API connection error।"
        )

    except Exception as e:

        raise Exception(
            f"Groq connection error: {e}"
        )

    try:

        data = response.json()

    except Exception:

        raise Exception(
            f"Groq HTTP {response.status_code}: "
            f"{response.text[:1500]}"
        )

    if response.status_code >= 400:

        if isinstance(data, dict):

            error = data.get(
                "error",
                data
            )

        else:

            error = data

        raise Exception(
            f"Groq HTTP {response.status_code}: {error}"
        )

    choices = data.get(
        "choices",
        []
    )

    if not choices:

        raise Exception(
            f"Groq response खाली है: {data}"
        )

    content = choices[0].get(
        "message",
        {}
    ).get(
        "content",
        ""
    )

    return str(
        content or ""
    ).strip()


# ============================================================
# AI SIGNAL
# ============================================================

def get_signal_and_analysis(
    candles,
    symbol
):

    if len(candles) < 5:

        return (
            "BUY",
            "डेटा कम होने के कारण default BUY signal लिया गया।"
        )

    recent = candles[-10:]

    candle_text = "\n".join(
        str(c)
        for c in recent
    )

    system_prompt = """
You are GYAN AI Pro institutional SMC
and momentum trading analyst.

Analyze 1-minute crypto candles.

Consider:
Market Structure,
HH/HL,
LH/LL,
Momentum,
Order Flow,
Breakout,
Rejection,
Buying Pressure,
Selling Pressure.

Return ONLY valid JSON:

{
 "signal": "BUY" or "SELL",
 "analysis": "detailed explanation in Hindi"
}

No markdown.
No code fence.
No extra keys.
"""

    user_prompt = f"""
Symbol: {symbol}

Latest 1-minute candles:

{candle_text}

Choose BUY or SELL.
Explain the decision in Hindi.
"""

    content = groq_request(
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        max_tokens=500,
        temperature=0.2,
        response_format={
            "type": "json_object"
        }
    )

    try:

        data = json.loads(
            content
        )

    except Exception:

        raise Exception(
            "AI invalid JSON दे रहा है: "
            + content[:1000]
        )

    signal = str(
        data.get(
            "signal",
            ""
        )
    ).upper().strip()

    analysis = str(
        data.get(
            "analysis",
            "विश्लेषण उपलब्ध नहीं है।"
        )
    )

    if signal not in (
        "BUY",
        "SELL"
    ):

        raise Exception(
            f"Invalid AI signal: {signal}"
        )

    return signal, analysis


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

    result = data.get(
        "result",
        []
    )

    if isinstance(result, list):

        if not result:
            return 0.0

        return float(
            result[0].get(
                "size",
                0
            )
        )

    if isinstance(result, dict):

        return float(
            result.get(
                "size",
                0
            )
        )

    return 0.0


# ============================================================
# MARKET ORDER
# ============================================================

def place_market_order(
    symbol,
    side
):

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
        auth=True
    )

    return data.get(
        "result",
        {}
    )


# ============================================================
# ENTRY PRICE
# ============================================================

def get_entry_price(
    order_result,
    symbol
):

    fields = [
        "average_fill_price",
        "avg_fill_price",
        "fill_price",
        "price",
        "limit_price"
    ]

    for field in fields:

        value = order_result.get(
            field
        )

        if value not in (
            None,
            "",
            0,
            "0"
        ):

            try:
                return float(value)
            except Exception:
                pass

    ticker = get_ticker(
        symbol
    )

    fields = [
        "mark_price",
        "close",
        "last_price",
        "spot_price"
    ]

    for field in fields:

        value = ticker.get(
            field
        )

        if value not in (
            None,
            "",
            0,
            "0"
        ):

            try:
                return float(value)
            except Exception:
                pass

    raise Exception(
        "Entry price नहीं मिला।"
    )


# ============================================================
# PRICE PRECISION
# ============================================================

def get_price_precision(symbol):

    product = get_product(
        symbol
    )

    if not product:
        return 4

    tick_size = product.get(
        "tick_size"
    )

    try:

        tick = float(
            tick_size
        )

        if tick > 0:

            text = (
                f"{tick:.10f}"
                .rstrip("0")
            )

            if "." in text:

                return min(
                    len(
                        text.split(".")[1]
                    ),
                    10
                )

    except Exception:

        pass

    return 4


# ============================================================
# TP + SL BRACKET
# ============================================================

def place_sl_tp_orders(
    symbol,
    entry_side,
    entry_price
):

    entry_price = float(
        entry_price
    )

    if entry_side == "buy":

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

    precision = get_price_precision(
        symbol
    )

    stop_text = (
        f"{stop_price:.{precision}f}"
    )

    target_text = (
        f"{target_price:.{precision}f}"
    )

    # Delta bracket order:
    # SL = market order triggered at stop_price
    # TP = limit order triggered at stop_price
    # Bracket closes the open position.

    body = {
        "product_symbol": symbol,

        "stop_loss_order": {
            "order_type": "market_order",
            "stop_price": stop_text
        },

        "take_profit_order": {
            "order_type": "limit_order",
            "stop_price": target_text,
            "limit_price": target_text
        },

        "bracket_stop_trigger_method": "last_traded_price"
    }

    try:

        data = delta_request(
            "POST",
            "/v2/orders/bracket",
            body=body,
            auth=True
        )

        return {
            "success": True,
            "entry_price": entry_price,
            "stop_loss": stop_text,
            "take_profit": target_text,
            "response": data
        }

    except Exception as e:

        return {
            "success": False,
            "entry_price": entry_price,
            "stop_loss": stop_text,
            "take_profit": target_text,
            "error": str(e)
        }


# ============================================================
# CHAT
# ============================================================

def ask_chat(
    symbol,
    user_message
):

    ticker_text = ""

    try:

        ticker = get_ticker(
            symbol
        )

        ticker_text = json.dumps(
            ticker,
            ensure_ascii=False
        )[:5000]

    except Exception as e:

        ticker_text = (
            "Ticker unavailable: "
            + str(e)
        )

    system_prompt = f"""
आप GYAN AI Pro के professional
crypto trading mentor हैं।

Current Symbol:
{symbol}

आप Hindi में जवाब दें।

Topics:
Price Action
Market Structure
Momentum
Support Resistance
Trend
Scalping
Intraday
Risk Management

Live ticker:

{ticker_text}

Guaranteed profit का दावा न करें।
"""

    history = (
        st.session_state.messages[-10:]
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(
        history
    )

    messages.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    return groq_request(
        messages=messages,
        max_tokens=1400,
        temperature=0.3
    )


# ============================================================
# HEADER
# ============================================================

st.title(
    "⚡ GYAN AI Pro"
)

st.caption(
    "Delta Exchange India • "
    "AI Scalping • TP/SL • GPT-OSS 120B"
)


# ============================================================
# STATUS
# ============================================================

c1, c2, c3 = st.columns(3)

with c1:

    if (
        DELTA_API_KEY
        and DELTA_API_SECRET
    ):

        st.success(
            "Delta API: READY"
        )

    else:

        st.error(
            "Delta API: KEY MISSING"
        )

with c2:

    if GROQ_API_KEY:

        st.success(
            "Groq AI: READY"
        )

    else:

        st.error(
            "Groq API: KEY MISSING"
        )

with c3:

    st.info(
        f"Model: {GROQ_MODEL}"
    )


# ============================================================
# SYMBOLS
# ============================================================

try:

    symbols = get_all_symbols()

except Exception:

    symbols = []

if not symbols:

    symbols = [
        "ARCUSD",
        "BTCUSD",
        "ETHUSD"
    ]

if "ARCUSD" in symbols:

    default_index = symbols.index(
        "ARCUSD"
    )

else:

    default_index = 0


# ============================================================
# TABS
# ============================================================

tab1, tab2 = st.tabs(
    [
        "⚡ Scalping Terminal",
        "🤖 AI Chat"
    ]
)


# ============================================================
# SCALPING TERMINAL
# ============================================================

with tab1:

    st.subheader(
        "⚡ AI Scalping Terminal"
    )

    col1, col2 = st.columns(
        [2, 1]
    )

    with col1:

        symbol = st.selectbox(
            "Trading Symbol",
            symbols,
            index=default_index,
            key="trade_symbol"
        )

    with col2:

        auto_trade = st.checkbox(
            "Auto Trade",
            value=False
        )

    refresh_seconds = st.slider(
        "Refresh Interval (seconds)",
        5,
        60,
        10
    )

    ticker = {}

    try:

        ticker = get_ticker(
            symbol
        )

    except Exception as e:

        st.warning(
            f"Ticker Error: {e}"
        )

    price = (
        ticker.get("close")
        or ticker.get("mark_price")
        or ticker.get("last_price")
        or 0
    )

    mark_price = (
        ticker.get("mark_price")
        or price
        or 0
    )

    volume = (
        ticker.get("volume")
        or ticker.get("turnover")
        or 0
    )

    a, b, c = st.columns(3)

    with a:

        st.metric(
            "Price",
            str(price)
        )

    with b:

        st.metric(
            "Mark Price",
            str(mark_price)
        )

    with c:

        st.metric(
            "Volume",
            str(volume)
        )

    st.divider()

    run_signal = st.button(
        "🚀 RUN AI SIGNAL",
        use_container_width=True
    )

    if run_signal:

        if (
            not DELTA_API_KEY
            or not DELTA_API_SECRET
        ):

            st.error(
                "Delta API Key और Secret missing हैं।"
            )

        else:

            try:

                # --------------------------------------------
                # PRODUCT
                # --------------------------------------------

                product = get_product(
                    symbol
                )

                if not product:

                    raise Exception(
                        f"{symbol} का product नहीं मिला।"
                    )

                product_id = product.get(
                    "id"
                )

                if not product_id:

                    raise Exception(
                        f"{symbol} का product_id नहीं मिला।"
                    )

                # --------------------------------------------
                # POSITION CHECK
                # --------------------------------------------

                current_position = get_position(
                    product_id
                )

                if abs(current_position) > 0:

                    st.warning(
                        f"Existing position: "
                        f"{current_position}. "
                        "नई trade नहीं लगाई गई।"
                    )

                else:

                    # ----------------------------------------
                    # CANDLES
                    # ----------------------------------------

                    with st.spinner(
                        "Market data पढ़ रहा हूँ..."
                    ):

                        candles = get_candles(
                            symbol
                        )

                    if len(candles) < 5:

                        st.error(
                            "पर्याप्त candle data नहीं मिला।"
                        )

                    else:

                        # ------------------------------------
                        # AI
                        # ------------------------------------

                        with st.spinner(
                            "GPT-OSS 120B analyze कर रहा है..."
                        ):

                            signal, analysis = (
                                get_signal_and_analysis(
                                    candles,
                                    symbol
                                )
                            )

                        st.session_state.last_signal = (
                            signal
                        )

                        st.session_state.last_analysis = (
                            analysis
                        )

                        if signal == "BUY":

                            st.success(
                                "🟢 BUY SIGNAL"
                            )

                        else:

                            st.error(
                                "🔴 SELL SIGNAL"
                            )

                        st.info(
                            analysis
                        )

                        # ------------------------------------
                        # SIDE
                        # ------------------------------------

                        side = (
                            "buy"
                            if signal == "BUY"
                            else "sell"
                        )

                        # ------------------------------------
                        # ENTRY
                        # ------------------------------------

                        with st.spinner(
                            f"{side.upper()} order लगाया जा रहा है..."
                        ):

                            order_result = (
                                place_market_order(
                                    symbol,
                                    side
                                )
                            )

                        st.session_state.last_order = (
                            order_result
                        )

                        st.success(
                            "✅ Market order placed."
                        )

                        st.json(
                            order_result
                        )

                        # ------------------------------------
                        # ENTRY PRICE
                        # ------------------------------------

                        entry_price = get_entry_price(
                            order_result,
                            symbol
                        )

                        st.write(
                            f"**Entry Price:** `{entry_price}`"
                        )

                        # ------------------------------------
                        # TP + SL
                        # ------------------------------------

                        with st.spinner(
                            "TP + SL bracket लगा रहा हूँ..."
                        ):

                            bracket_result = (
                                place_sl_tp_orders(
                                    symbol,
                                    side,
                                    entry_price
                                )
                            )

                        st.session_state.last_bracket = (
                            bracket_result
                        )

                        # ------------------------------------
                        # RESULT
                        # ------------------------------------

                        if bracket_result.get(
                            "success"
                        ):

                            st.success(
                                "✅ TP + SL दोनों लग गए।"
                            )

                            x, y = st.columns(2)

                            with x:

                                st.metric(
                                    "Stop Loss",
                                    bracket_result[
                                        "stop_loss"
                                    ]
                                )

                            with y:

                                st.metric(
                                    "Take Profit",
                                    bracket_result[
                                        "take_profit"
                                    ]
                                )

                            with st.expander(
                                "Bracket API Response"
                            ):

                                st.json(
                                    bracket_result.get(
                                        "response"
                                    )
                                )

                        else:

                            st.error(
                                "❌ TP/SL लगाने में error आया।"
                            )

                            st.code(
                                str(
                                    bracket_result.get(
                                        "error"
                                    )
                                )
                            )

            # =================================================
            # THIS WAS MISSING IN YOUR CODE
            # =================================================

            except Exception as e:

                st.error(
                    "❌ Trading / AI Error"
                )

                st.code(
                    f"{type(e).__name__}: {e}"
                )

    # ========================================================
    # LAST SIGNAL
    # ========================================================

    if st.session_state.last_signal:

        st.divider()

        st.subheader(
            "Last AI Decision"
        )

        st.write(
            "Signal: "
            + str(
                st.session_state.last_signal
            )
        )

        st.write(
            st.session_state.last_analysis
        )

    # ========================================================
    # AUTO REFRESH
    # ========================================================

    if auto_trade:

        st.warning(
            f"Auto Trade ON — "
            f"हर {refresh_seconds} sec refresh होगा।"
        )

        time.sleep(
            refresh_seconds
        )

        st.rerun()


# ============================================================
# AI CHAT
# ============================================================

with tab2:

    st.subheader(
        "🤖 GYAN AI Trading Chat"
    )

    chat_symbol = st.selectbox(
        "चैट के लिए Symbol चुनें",
        symbols,
        index=(
            symbols.index("ARCUSD")
            if "ARCUSD" in symbols
            else 0
        ),
        key="chat_symbol"
    )

    st.caption(
        f"Current Symbol: {chat_symbol}"
    )

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

    # --------------------------------------------------------
    # INPUT
    # --------------------------------------------------------

    user_message = st.chat_input(
        f"{chat_symbol} के बारे में पूछें..."
    )

    if user_message:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_message
            }
        )

        with st.chat_message(
            "user"
        ):

            st.markdown(
                user_message
            )

        with st.chat_message(
            "assistant"
        ):

            with st.spinner(
                "GYAN AI सोच रहा है..."
            ):

                try:

                    reply = ask_chat(
                        chat_symbol,
                        user_message
                    )

                    if not reply:

                        reply = (
                            "AI ने खाली response दिया।"
                        )

                    st.markdown(
                        reply
                    )

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": reply
                        }
                    )

                except Exception as e:

                    error_message = (
                        "❌ Chat API Error\n\n"
                        f"`{type(e).__name__}: {e}`"
                    )

                    st.error(
                        error_message
                    )

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": error_message
                        }
                    )

    # --------------------------------------------------------
    # CLEAR
    # --------------------------------------------------------

    if st.button(
        "🗑️ Clear Chat"
    ):

        st.session_state.messages = []

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "GYAN AI Pro • Delta Exchange India • "
    "Groq GPT-OSS 120B"
)
