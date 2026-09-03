import os
import time
import json
import hmac
import hashlib
from urllib.parse import urlencode

import requests
import streamlit as st


# ============================================================
# GYAN AI PRO
# DELTA EXCHANGE INDIA + GROQ GPT-OSS 120B
# TP + SL BRACKET + CHAT
# ============================================================

BASE_URL = "https://api.india.delta.exchange"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"

LOT_SIZE = 1

# Original risk settings
SL_PERCENT = 0.005       # 0.50%
TP_PERCENT = 0.010       # 1.00%

REQUEST_TIMEOUT = 20


# ============================================================
# STREAMLIT
# ============================================================

st.set_page_config(
    page_title="GYAN AI Pro",
    page_icon="⚡",
    layout="wide"
)


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

DELTA_API_KEY = os.getenv("DELTA_API_KEY", "").strip()
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()


# ============================================================
# SESSION STATE
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
# DELTA API SIGNATURE
# ============================================================

def delta_request(method, path, params=None, body=None, auth=False):

    if params is None:
        params = {}

    if body is None:
        body = {}

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

    timestamp = int(time.time())

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
            f"{response.text[:1000]}"
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
# DELTA PRODUCTS
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
                params=params,
                auth=False
            )

        except Exception:

            break

        result = data.get("result", [])

        if not result:
            break

        products.extend(result)

        meta = data.get("meta", {})

        after = meta.get("after")

        if not after:
            break

    return products


@st.cache_data(ttl=300)
def get_all_symbols():

    products = get_all_products()

    tradable = []

    for p in products:

        symbol = str(
            p.get("symbol", "")
        ).upper().strip()

        ptype = str(
            p.get("product_type", "")
        ).lower()

        state = str(
            p.get("state", "")
        ).lower()

        if not symbol:
            continue

        if "perpetual" not in ptype:
            continue

        if symbol.startswith("C-"):
            continue

        if symbol.startswith("P-"):
            continue

        if state and state not in [
            "live",
            "active"
        ]:
            continue

        tradable.append(symbol)

    return sorted(
        list(set(tradable))
    )


def get_product(symbol):

    symbol = symbol.upper().strip()

    products = get_all_products()

    for p in products:

        if str(
            p.get("symbol", "")
        ).upper().strip() == symbol:

            return p

    return None


# ============================================================
# TICKER
# ============================================================

def get_ticker(symbol):

    data = delta_request(
        "GET",
        f"/v2/tickers/{symbol}",
        auth=False
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

    params = {
        "resolution": "1m",
        "symbol": symbol,
        "start": start_time,
        "end": end_time
    }

    data = delta_request(
        "GET",
        "/v2/history/candles",
        params=params,
        auth=False
    )

    result = data.get(
        "result",
        []
    )

    return result


# ============================================================
# GROQ RAW REQUEST
# ============================================================

def groq_request(messages, max_tokens=1000, temperature=0.3,
                 response_format=None):

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

    if response_format is not None:

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
            "Groq API connection error। "
            "Render server से Groq तक connection नहीं बन रहा।"
        )

    except Exception as e:

        raise Exception(
            f"Groq request error: {type(e).__name__}: {e}"
        )

    try:

        data = response.json()

    except Exception:

        raise Exception(
            f"Groq HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )

    if response.status_code >= 400:

        error_text = data

        if isinstance(data, dict):

            error_text = data.get(
                "error",
                data
            )

        raise Exception(
            f"Groq HTTP {response.status_code}: "
            f"{error_text}"
        )

    choices = data.get(
        "choices",
        []
    )

    if not choices:

        raise Exception(
            f"Groq ने कोई response नहीं दिया: {data}"
        )

    message = choices[0].get(
        "message",
        {}
    )

    content = message.get(
        "content",
        ""
    )

    if content is None:

        content = ""

    return content.strip()


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
You are an elite Institutional Smart Money Concepts (SMC)
and Momentum Trader for GYAN AI Pro.

Analyze 1-minute cryptocurrency candles.

Use:
1. Market Structure
2. Higher High / Higher Low
3. Lower High / Lower Low
4. Momentum
5. Order Flow
6. Breakout / rejection
7. Institutional buying or selling pressure

Return ONLY valid JSON.

The JSON must contain exactly:

{
  "signal": "BUY" or "SELL",
  "analysis": "detailed explanation in pure Hindi"
}

Do not add markdown.
Do not add ```json.
Do not add extra keys.
"""

    user_prompt = f"""
Symbol: {symbol}

Analyze these latest 1-minute candles:

{candle_text}

Choose the strongest directional signal:
BUY or SELL.

Explain the reasoning in Hindi.
"""

    try:

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

        data = json.loads(content)

        signal = str(
            data.get(
                "signal",
                "BUY"
            )
        ).upper().strip()

        analysis = str(
            data.get(
                "analysis",
                "विश्लेषण उपलब्ध नहीं है।"
            )
        )

        if signal not in [
            "BUY",
            "SELL"
        ]:

            signal = "BUY"

        return signal, analysis

    except Exception as e:

        raise Exception(
            f"AI Signal Error: {e}"
        )


# ============================================================
# DELTA POSITION
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
# GET ENTRY PRICE
# ============================================================

def get_entry_price(
    order_result,
    symbol
):

    possible_fields = [
        "average_fill_price",
        "avg_fill_price",
        "fill_price",
        "price",
        "limit_price"
    ]

    for field in possible_fields:

        value = order_result.get(
            field
        )

        if value not in [
            None,
            "",
            0,
            "0"
        ]:

            try:

                return float(value)

            except Exception:

                pass

    # Fallback to ticker
    ticker = get_ticker(symbol)

    possible_ticker_fields = [
        "mark_price",
        "close",
        "last_price",
        "spot_price"
    ]

    for field in possible_ticker_fields:

        value = ticker.get(
            field
        )

        if value not in [
            None,
            "",
            0,
            "0"
        ]:

            try:

                return float(value)

            except Exception:

                pass

    raise Exception(
        "Entry price नहीं मिला।"
    )


# ============================================================
# TP + SL BRACKET ORDER
# ============================================================
#
# IMPORTANT:
# Delta API does NOT use:
# order_type = "stop_order"
#
# Instead:
# order_type = "market_order" / "limit_order"
# stop_price = trigger price
#
# Bracket endpoint handles TP + SL together.
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

        exit_side = "sell"

        stop_price = (
            entry_price *
            (1 - SL_PERCENT)
        )

        target_price = (
            entry_price *
            (1 + TP_PERCENT)
        )

    else:

        exit_side = "buy"

        stop_price = (
            entry_price *
            (1 + SL_PERCENT)
        )

        target_price = (
            entry_price *
            (1 - TP_PERCENT)
        )

    # --------------------------------------------------------
    # Product info for price precision
    # --------------------------------------------------------

    product = get_product(
        symbol
    )

    # Default precision
    price_precision = 4

    if product:

        tick_size = product.get(
            "tick_size"
        )

        if tick_size:

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

                        decimals = len(
                            text.split(".")[1]
                        )

                        price_precision = min(
                            max(
                                decimals,
                                0
                            ),
                            10
                        )

            except Exception:

                pass

    stop_text = f"{stop_price:.{price_precision}f}"

    target_text = f"{target_price:.{price_precision}f}"

    # --------------------------------------------------------
    # BRACKET ORDER
    # --------------------------------------------------------

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
# CHAT SYSTEM
# ============================================================

def ask_chat(
    symbol,
    user_message
):

    system_prompt = f"""
आप GYAN AI Pro के professional crypto trading mentor हैं।

Current Symbol:
{symbol}

आपको:
- Market structure
- Price action
- Momentum
- Support / Resistance
- Trend
- Scalping
- Intraday
- Risk management

के बारे में सरल लेकिन professional Hindi में जवाब देना है।

यदि user किसी coin की current trading स्थिति पूछता है,
तो उपलब्ध market data के आधार पर जवाब दें।

बिना data के guaranteed profit का दावा न करें।

User का सवाल:
{user_message}
"""

    # Get live ticker for chat context
    ticker_text = ""

    try:

        ticker = get_ticker(
            symbol
        )

        ticker_text = (
            "\n\nLIVE TICKER DATA:\n"
            + json.dumps(
                ticker,
                ensure_ascii=False
            )[:5000]
        )

    except Exception as e:

        ticker_text = (
            "\n\nTicker unavailable: "
            + str(e)
        )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": (
                user_message
                + ticker_text
            )
        }
    ]

    return groq_request(
        messages=messages,
        max_tokens=1400,
        temperature=0.3
    )


# ============================================================
# HEADER
# ============================================================

st.title("⚡ GYAN AI Pro")

st.caption(
    "Delta Exchange India • AI Scalping • TP/SL Bracket • GPT-OSS 120B"
)


# ============================================================
# API STATUS
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:

    if DELTA_API_KEY and DELTA_API_SECRET:
        st.success("Delta API: READY")
    else:
        st.error("Delta API: KEY MISSING")

with col2:

    if GROQ_API_KEY:
        st.success("Groq AI: READY")
    else:
        st.error("Groq API: KEY MISSING")

with col3:

    st.info(
        f"AI Model: {GROQ_MODEL}"
    )


# ============================================================
# SYMBOL LIST
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

default_symbol = "ARCUSD"

if default_symbol in symbols:

    default_index = symbols.index(
        default_symbol
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
# TAB 1
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
            index=default_index
        )

    with col2:

        auto_trade = st.checkbox(
            "Auto Trade",
            value=False
        )

    refresh_seconds = st.slider(
        "Refresh Interval (seconds)",
        min_value=5,
        max_value=60,
        value=10
    )

    # --------------------------------------------------------
    # TICKER
    # --------------------------------------------------------

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

    st.divider()

    # --------------------------------------------------------
    # RUN SCALPING
    # --------------------------------------------------------

    if st.button(
        "🚀 RUN AI SIGNAL",
        use_container_width=True
    ):

        if not DELTA_API_KEY or not DELTA_API_SECRET:

            st.error(
                "पहले Delta API Key और Secret सेट करें।"
            )

        else:

            try:

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

                # ------------------------------------------------
                # EXISTING POSITION CHECK
                # ------------------------------------------------

                current_position = get_position(
                    product_id
                )

                if abs(current_position) > 0:

                    st.warning(
                        f"Existing position detected: "
                        f"{current_position}. "
                        f"नई trade नहीं लगाई गई।"
                    )

                else:

                    # ------------------------------------------------
                    # CANDLES
                    # ------------------------------------------------

                    with st.spinner(
                        "1-minute market data पढ़ रहा हूँ..."
                    ):

                        candles = get_candles(
                            symbol
                        )

                    if len(candles) < 5:

                        st.error(
                            "पर्याप्त candle data नहीं मिला।"
                        )

                    else:

                        # ------------------------------------------------
                        # AI SIGNAL
                        # ------------------------------------------------

                        with st.spinner(
                            "GPT-OSS 120B market analyze कर रहा है..."
                        ):

                            signal, analysis = (
                                get_signal_and_analysis(
                                    candles,
                                    symbol
                                )
                            )

                        st.session_state.last_signal = signal

                        st.session_state.last_analysis = analysis

                        # ------------------------------------------------
                        # SIGNAL DISPLAY
                        # ------------------------------------------------

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

                        # ------------------------------------------------
                        # ORDER SIDE
                        # ------------------------------------------------

                        side = (
                            "buy"
                            if signal == "BUY"
                            else "sell"
                        )

                        # ------------------------------------------------
                        # MARKET ENTRY
                        # ------------------------------------------------

                        with st.spinner(
                            f"{side.upper()} market order लगाया जा रहा है..."
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
                            "Market order successfully placed."
                        )

                        st.json(
                            order_result
                        )

                        # ------------------------------------------------
                        # ENTRY PRICE
                        # ------------------------------------------------

                        entry_price = get_entry_price(
                            order_result,
                            symbol
                        )

                        st.write(
                            f"**Entry Price:** `{entry_price}`"
                        )

                        # ------------------------------------------------
                        # TP + SL
                        # ------------------------------------------------

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

                        # ------------------------------------------------
                        # BRACKET RESULT
                        # ------------------------------------------------

                        if bracket_result.get(
                            "success"
                        ):

                            st.success(
                                "✅ TP + SL दोनों successfully लग गए।"
                            )

                            b1, b2 = st.columns(2)

                            with b1:

                                st.metric(
                                    "Stop Loss",
                                    bracket_result.get(
                                        "stop_loss"
                                    )
                                )

                            with b2:

                                st.metric(
                                    "Take Profit",
                                    bracket_result.get(
                                        "take_profit"
                                    )
                                )

                            with st.expander(
                                "Bracket API Response"
                            ):

                                st.json(
                                    bracket_result.get(
                                        "response"
                                    )
                                )

                            st.balloons()

                        else:

                            st.error(
                                "❌ TP/SL bracket लगाने में error आया।"
                            )

                            st.code(
                                str(
                                    bracket_result.get(
                                        "error"
                                    )
                                )
                            )

    # --------------------------------------------------------
    # LAST SIGNAL
    # --------------------------------------------------------

    if st.session_state.last_signal:

        st.divider()

        st.subheader(
            "Last AI Decision"
        )

        st.write(
            f"Signal: **{st.session_state.last_signal}**"
        )

        st.write(
            st.session_state.last_analysis
        )

    # --------------------------------------------------------
    # AUTO TRADE
    # --------------------------------------------------------

    if auto_trade:

        st.warning(
            f"Auto Trade ON — हर {refresh_seconds} sec में scan होगा।"
        )

        time.sleep(
            refresh_seconds
        )

        st.rerun()


# ============================================================
# TAB 2 — AI CHAT
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
        f"Current Chat Symbol: {chat_symbol}"
    )

    # --------------------------------------------------------
    # CHAT HISTORY
    # --------------------------------------------------------

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

    # --------------------------------------------------------
    # CHAT INPUT
    # --------------------------------------------------------

    user_message = st.chat_input(
        f"{chat_symbol} के बारे में पूछें..."
    )

    if user_message:

        # User message
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

        # AI response
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
                        f"❌ Chat API Error\n\n"
                        f"`{type(e).__name__}: {str(e)}`"
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
    # CLEAR CHAT
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
