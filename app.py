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

SL_PERCENT = 0.005       # 0.5% Stop Loss
TP_PERCENT = 0.010       # 1.0% Take Profit


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="GYAN AI Pro — Profitable Trading",
    page_icon="⚡",
    layout="wide"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

.stApp {
    background-color: #0b0f19;
    color: #f3f4f6;
}

h1, h2, h3 {
    color: #ffffff;
    font-family: 'Inter', sans-serif;
}

div.stMetric {
    background: linear-gradient(
        135deg,
        #1f2937 0%,
        #111827 100%
    );
    border: 1px solid #374151;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
}

div.stMetric label {
    color: #9ca3af !important;
    font-weight: 600;
}

div.stMetric div[data-testid="stMetricValue"] {
    color: #10b981 !important;
    font-size: 1.8rem !important;
}

.stButton > button {
    background: linear-gradient(
        135deg,
        #3b82f6 0%,
        #1d4ed8 100%
    );
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    font-weight: 600;
    width: 100%;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    transition: all 0.3s ease;
}

.stButton > button:hover {
    background: linear-gradient(
        135deg,
        #2563eb 0%,
        #1e40af 100%
    );
    box-shadow: 0 6px 16px rgba(59, 130, 246, 0.5);
    transform: translateY(-1px);
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: #111827;
    padding: 6px;
    border-radius: 10px;
    border: 1px solid #374151;
}

.stTabs [data-baseweb="tab"] {
    height: 45px;
    color: #9ca3af;
    border-radius: 6px;
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    background-color: #3b82f6 !important;
    color: white !important;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# API KEYS & MODEL CONFIG
# ============================================================

DELTA_API_KEY = os.getenv("DELTA_API_KEY", "")
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GROQ_MODEL = "openai/gpt-oss-20b"


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
                "Delta API Keys missing"
            )

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
        raise Exception(
            f"HTTP {response.status_code}: {data}"
        )

    return data


# ============================================================
# GET ALL SYMBOLS
# ============================================================

@st.cache_data(ttl=60)
def get_all_symbols():

    products = []
    after = None

    for _ in range(10):

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

            result = data.get(
                "result",
                []
            )

            if not result:
                break

            products.extend(result)

            meta = data.get(
                "meta",
                {}
            )

            after = meta.get("after")

            if not after:
                break

        except Exception:
            break

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


# ============================================================
# GET TICKER
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
# GET CANDLES
# ============================================================

def get_candles(symbol):

    end_time = int(
        time.time()
    )

    start_time = (
        end_time - 1800
    )

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

    return data.get(
        "result",
        []
    )


# ============================================================
# GROQ AI SIGNAL ENGINE (STRICT JSON SCHEMA)
# ============================================================

def get_signal_and_analysis(
    candles,
    symbol
):

    if not GROQ_API_KEY:
        return (
            "NO TRADE",
            "Groq API Key उपलब्ध नहीं है।"
        )

    if len(candles) < 5:
        return (
            "NO TRADE",
            "पर्याप्त candle data उपलब्ध नहीं है।"
        )

    recent = candles[-10:]

    candle_text = "\n".join(
        str(c)
        for c in recent
    )

    prompt = f"""
आप GYAN AI Pro के Institutional Trading Decision Engine हैं।
Symbol: {symbol}
इन 1-minute candles का विश्लेषण करें और केवल निम्नलिखित structure में उत्तर दें।

CANDLES:
{candle_text}
"""

    try:

        client = Groq(
            api_key=GROQ_API_KEY
        )

        response = client.chat.completions.create(

            model=GROQ_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": (
                        "आप GYAN AI Pro trading analysis engine हैं। "
                        "केवल requested structured JSON output दें।"
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            response_format={
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
            },

            temperature=0.2,

            max_tokens=500
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            return (
                "NO TRADE",
                "AI ने कोई valid response नहीं दिया।"
            )

        data = json.loads(content)

        signal = str(
            data.get(
                "signal",
                "NO TRADE"
            )
        ).upper().strip()

        analysis = str(
            data.get(
                "analysis",
                "AI analysis उपलब्ध नहीं है।"
            )
        ).strip()

        if signal not in [
            "BUY",
            "SELL",
            "NO TRADE"
        ]:
            return (
                "NO TRADE",
                "AI ने invalid signal दिया।"
            )

        return (
            signal,
            analysis
        )

    except json.JSONDecodeError as e:
        return (
            "NO TRADE",
            f"AI JSON Error: {str(e)}"
        )

    except Exception as e:
        return (
            "NO TRADE",
            f"AI Analysis Error: {str(e)}"
        )


# ============================================================
# GET POSITION
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

    if isinstance(
        result,
        list
    ):

        if len(result) == 0:
            return 0.0

        return float(
            result[0].get(
                "size",
                0
            )
        )

    elif isinstance(
        result,
        dict
    ):

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
# STOP LOSS + TAKE PROFIT
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
            entry_price
            * (1 - SL_PERCENT)
        )

        target_price = (
            entry_price
            * (1 + TP_PERCENT)
        )

    else:

        exit_side = "buy"

        stop_price = (
            entry_price
            * (1 + SL_PERCENT)
        )

        target_price = (
            entry_price
            * (1 - TP_PERCENT)
        )

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
        sl_res = delta_request(
            "POST",
            "/v2/orders",
            body=sl_body,
            auth=True
        )
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
        tp_res = delta_request(
            "POST",
            "/v2/orders",
            body=tp_body,
            auth=True
        )
        results.append(("Take Profit", tp_res))
    except Exception as e:
        results.append(("Take Profit Error", str(e)))

    return results


# ============================================================
# MAIN HEADER
# ============================================================

st.markdown(
    "# ⚡ GYAN AI Pro — PROFITABLE TRADING"
)

st.markdown(
    "### *Universal Trading Institute & Institutional Smart Scalper*"
)

st.divider()


# ============================================================
# SYMBOLS
# ============================================================

symbols_list = get_all_symbols()

if not symbols_list:
    symbols_list = [
        "ARCUSD",
        "BTCUSD",
        "ETHUSD"
    ]


# ============================================================
# SESSION STATE INITIALIZATION (For Cooldown & Tracking)
# ============================================================

if "last_trade_time" not in st.session_state:
    st.session_state.last_trade_time = 0

COOLDOWN_SECONDS = 60


# ============================================================
# TABS
# ============================================================

tab1, tab2 = st.tabs(
    [
        "⚡ लाइव स्केल्पर टर्मिनल",
        "💬 AI मेंटर & चैट रूम"
    ]
)


# ============================================================
# TAB 1 — LIVE SCALPER
# ============================================================

with tab1:

    c1, c2, c3 = st.columns(3)

    with c1:
        selected_symbol = st.selectbox(
            "🪙 क्रिप्टो सिंबल चुनें",
            symbols_list,
            key="t1_sym"
        )

    with c2:
        auto_trade = st.checkbox(
            "🔄 ऑटो-स्केल्पिंग लूप मोड",
            value=False
        )

    with c3:
        refresh_rate = st.slider(
            "⏱️ रिफ्रेश इंटरवल (सेकंड)",
            5,
            30,
            5
        )

    st.markdown(
        "<br>",
        unsafe_allow_html=True
    )

    try:
        live_ticker = get_ticker(
            selected_symbol
        )

        m_price = live_ticker.get(
            "mark_price",
            live_ticker.get(
                "close",
                "0.0"
            )
        )

        high_p = live_ticker.get(
            "high",
            "0.0"
        )

        low_p = live_ticker.get(
            "low",
            "0.0"
        )

        m1, m2, m3 = st.columns(3)

        m1.metric(
            "Current Mark Price",
            f"{float(m_price):.4f}"
        )

        m2.metric(
            "24h High",
            f"{float(high_p):.4f}"
        )

        m3.metric(
            "24h Low",
            f"{float(low_p):.4f}"
        )

    except Exception as e:
        st.warning(
            f"Ticker Error: {str(e)}"
        )

    st.divider()

    placeholder = st.empty()


    def run_scalping():

        with placeholder.container():

            try:
                with st.spinner(
                    f"🔍 {selected_symbol} का मार्केट स्कैन हो रहा है..."
                ):
                    ticker = get_ticker(
                        selected_symbol
                    )

                    product_id = ticker.get(
                        "product_id"
                    )

                    mark_price = float(
                        ticker.get(
                            "mark_price"
                        )
                        or ticker.get(
                            "close"
                        )
                        or 0
                    )

                pos_size = get_position(
                    product_id
                )

                if pos_size != 0:
                    st.warning(
                        f"⚠️ **पोजीशन पहले से खुली है** "
                        f"(साइज: `{pos_size}`)। "
                        f"डुपलिकेट ट्रेड से बचाव सक्रिय है।"
                    )
                    return

                current_time = time.time()
                time_elapsed = current_time - st.session_state.last_trade_time

                if time_elapsed < COOLDOWN_SECONDS:
                    remaining = int(COOLDOWN_SECONDS - time_elapsed)
                    st.info(
                        f"⏳ **कूलडाउन मोड सक्रिय है:** "
                        f"अगला ट्रेड लेने से पहले `{remaining} सेकंड` बाकी हैं।"
                    )
                    return

                candles = get_candles(
                    selected_symbol
                )

                signal, analysis = get_signal_and_analysis(
                    candles,
                    selected_symbol
                )

                if signal == "NO TRADE":
                    st.warning(
                        "⏸️ **NO TRADE (बाजार स्पष्ट नहीं है)**"
                    )
                    st.info(
                        f"💡 {analysis}"
                    )
                    return

                if signal == "BUY":
                    st.success(
                        "🤖 **AI SIGNAL: BUY**"
                    )
                elif signal == "SELL":
                    st.error(
                        "🤖 **AI SIGNAL: SELL**"
                    )

                st.info(
                    f"💡 **AI ट्रेड एनालिसिस:**\n\n{analysis}"
                )

                side = (
                    "buy"
                    if signal == "BUY"
                    else "sell"
                )

                st.markdown(
                    f"🚀 **MARKET {side.upper()} "
                    f"ORDER भेजा जा रहा है...**"
                )

                order_res = place_market_order(
                    selected_symbol,
                    side
                )

                fill_price = float(
                    order_res.get(
                        "average_fill_price"
                    )
                    or mark_price
                )

                with st.expander(
                    "📦 देखें ऑर्डर डिटेल्स"
                ):
                    st.json(order_res)

                st.markdown(
                    "🎯 **ऑटो TP & SL आर्डर सेट किए जा रहे हैं...**"
                )

                sl_tp_res = place_sl_tp_orders(
                    selected_symbol,
                    side,
                    fill_price
                )

                with st.expander(
                    "🛡️ देखें TP/SL डिटेल्स"
                ):
                    for label, res in sl_tp_res:
                        st.write(
                            f"🔹 **{label}:**"
                        )
                        st.json(res)

                st.session_state.last_trade_time = time.time()

                st.success(
                    "✅ **ट्रेड सफलतापूर्वक "
                    "एक्जीक्यूट हो गया है!**"
                )

            except Exception as e:
                st.error(
                    f"❌ **एक्जीक्यूशन एरर:** "
                    f"{str(e)}"
                )


    if not auto_trade:
        if st.button(
            "⚡ तुरंत एक ट्रेड निष्पादित करें "
            "(One-Click Execute)"
        ):
            run_scalping()
    else:
        st.warning(
            "🔄 AUTO SCALPING MODE ACTIVE (डुपलिकेट और कूलडाउन रक्षित)"
        )

        while True:
            run_scalping()
            time.sleep(refresh_rate)
            st.rerun()


# ============================================================
# TAB 2 — AI MENTOR CHAT
# ============================================================

with tab2:

    st.markdown(
        "### 💬 GYAN AI Pro ट्रेडिंग मेंटर से सीधी बातचीत"
    )

    chat_symbol = st.selectbox(
        "चैट के लिए सिंबल चुनें",
        symbols_list,
        key="t2_sym"
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(
            message["role"]
        ):
            st.markdown(
                message["content"]
            )

    if user_query := st.chat_input(
        "जैसे पूछें: 'इस कॉइन में फास्ट ट्रेड दो' "
        "या 'स्केलपिंग स्ट्रेटजी बताओ'"
    ):

        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_query
            }
        )

        with st.chat_message(
            "user"
        ):
            st.markdown(
                user_query
            )

        with st.chat_message(
            "assistant"
        ):
            with st.spinner(
                "GYAN AI मेंटर जवाब तैयार कर रहा है..."
            ):

                try:
                    ticker = get_ticker(
                        chat_symbol
                    )

                    price = ticker.get(
                        "mark_price",
                        "N/A"
                    )

                    system_prompt = f"""
आप GYAN AI Pro के बहुत स्मार्ट और प्रोफेशनल ट्रेडिंग मेंटर हैं।
वर्तमान कॉइन: {chat_symbol}, प्राइस: {price}
हर जवाब स्पष्ट और आसान हिंदी में दें।
"""

                    client = Groq(
                        api_key=GROQ_API_KEY
                    )

                    res = client.chat.completions.create(

                        model=GROQ_MODEL,

                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": user_query
                            }
                        ],

                        temperature=0.3,

                        max_tokens=1400
                    )

                    reply = (
                        res
                        .choices[0]
                        .message
                        .content
                    )

                    st.markdown(reply)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": reply
                        }
                    )

                except Exception as e:
                    err_msg = (
                        "क्षमा करें, चैट में एरर आ गया: "
                        f"{str(e)}"
                    )
                    st.error(err_msg)
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": err_msg
                        }
                    )
