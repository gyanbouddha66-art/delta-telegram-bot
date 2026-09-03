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
SL_PERCENT = 0.005   # 0.5% SL
TP_PERCENT = 0.010   # 1.0% TP


# ============================================================
# PAGE CONFIG & STYLING
# ============================================================

st.set_page_config(
    page_title="GYAN AI Pro — Profitable Trading",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
""", unsafe_allow_html=True)


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
        raise Exception(
            f"HTTP {response.status_code}: {data}"
        )

    return data


# ============================================================
# GET SYMBOLS & DATA
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

        symbol = str(
            p.get("symbol", "")
        ).upper().strip()

        ptype = str(
            p.get("product_type", "")
        ).lower()

        state = str(
            p.get("state", "")
        ).lower()

        if not symbol or "perpetual" not in ptype:
            continue

        if symbol.startswith("C-") or symbol.startswith("P-"):
            continue

        if state and state not in ["live", "active"]:
            continue

        tradable.append(symbol)

    return sorted(list(set(tradable)))


def get_ticker(symbol):

    data = delta_request(
        "GET",
        f"/v2/tickers/{symbol}"
    )

    return data.get("result", {})


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
        params=params
    )

    return data.get("result", [])


# ============================================================
# AI SIGNAL & ANALYSIS
# ============================================================

def get_signal_and_analysis(candles, symbol):

    if not GROQ_API_KEY or len(candles) < 5:

        return (
            "BUY",
            "डेटा कम होने के कारण डिफॉल्ट BUY सिग्नल लिया गया।"
        )

    recent = candles[-10:]

    candle_text = "\n".join(
        str(c)
        for c in recent
    )

    prompt = f"""
You are an elite Institutional Smart Money Concepts (SMC)
& Momentum Trader for GYAN AI Pro.

Symbol: {symbol}

Analyze these 1-minute candles using professional
trading logic:

1. Market Structure & Trend (HL/LH shifts).

2. Institutional Order Flow & Momentum.

Respond strictly in JSON format with two keys:

1. "signal": "BUY" or "SELL"

2. "analysis": A detailed, professional explanation
in pure HINDI (हिंदी में) explaining the
Order Block/Momentum logic why this trade was chosen.

CANDLES:

{candle_text}
"""

    client = Groq(
        api_key=GROQ_API_KEY
    )

    # ========================================================
    # ONLY MODEL CHANGED
    # ========================================================

    models = [
        "openai/gpt-oss-120b"
    ]

    for model in models:

        try:

            res = client.chat.completions.create(

                model=model,

                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0.3,
                max_tokens=300
            )

            content = (
                res.choices[0]
                .message
                .content
                .strip()
            )

            if content.startswith("```json"):
                content = content[7:]

            if content.endswith("```"):
                content = content[:-3]

            data = json.loads(
                content.strip()
            )

            signal = data.get(
                "signal",
                "BUY"
            ).upper()

            analysis = data.get(
                "analysis",
                "विश्लेषण उपलब्ध नहीं है।"
            )

            if signal in ("BUY", "SELL"):

                return signal, analysis

        except Exception:

            continue

    return (
        "BUY",
        "स्मार्ट मनी मोमेंटम के आधार पर ऑटो सिग्नल जनरेट किया गया।"
    )


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

        if len(result) == 0:
            return 0.0

        return float(
            result[0].get(
                "size",
                0
            )
        )

    elif isinstance(result, dict):

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
# SL / TP
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

    results = []

    # --------------------------------------------------------
    # STOP LOSS
    # --------------------------------------------------------

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

        results.append(
            ("Stop Loss", sl_res)
        )

    except Exception as e:

        results.append(
            ("Stop Loss Error", str(e))
        )

    # --------------------------------------------------------
    # TAKE PROFIT
    # --------------------------------------------------------

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

        results.append(
            ("Take Profit", tp_res)
        )

    except Exception as e:

        results.append(
            ("Take Profit Error", str(e))
        )

    return results


# ============================================================
# MAIN UI LAYOUT
# ============================================================

st.markdown(
    "# ⚡ GYAN AI Pro — PROFITABLE TRADING"
)

st.markdown(
    "### *Universal Trading Institute & Institutional Smart Scalper*"
)

st.divider()


symbols_list = get_all_symbols()

if not symbols_list:

    symbols_list = [
        "ARCUSD",
        "BTCUSD",
        "ETHUSD"
    ]


tab1, tab2 = st.tabs(
    [
        "⚡ लाइव स्केल्पर टर्मिनल",
        "💬 AI मेंटर & चैट रूम"
    ]
)


# ============================================================
# TAB 1
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

    except Exception:

        pass


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
                        f"नई एंट्री होल्ड पर है।"
                    )

                else:

                    candles = get_candles(
                        selected_symbol
                    )

                    signal, analysis = (
                        get_signal_and_analysis(
                            candles,
                            selected_symbol
                        )
                    )

                    st.success(
                        f"🤖 **AI सिग्नल डिटेक्टेड:** "
                        f"`{signal}`"
                    )

                    st.info(
                        f"💡 **AI ट्रेड एनालिसिस & स्ट्रेटजी:**\n\n"
                        f"{analysis}"
                    )

                    side = (
                        "buy"
                        if signal == "BUY"
                        else "sell"
                    )

                    st.markdown(
                        f"🚀 **मार्केट {side.upper()} "
                        f"आर्डर भेजा जा रहा है...**"
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

                        st.json(
                            order_res
                        )


                    st.markdown(
                        "🎯 **ऑटो TP & SL "
                        "आर्डर सेट किए जा रहे हैं...**"
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

                            st.json(
                                res
                            )


                    st.balloons()

                    st.success(
                        "✅ **ट्रेड सफलतापूर्वक "
                        "निष्पादित और सुरक्षित हो गया है!**"
                    )


            except Exception as e:

                st.error(
                    f"❌ **एक्जीक्यूशन एरर:** "
                    f"{str(e)}"
                )


    if auto_trade:

        st.success(
            "🔄 **AUTO SCALPING MODE ACTIVE**"
        )

        while True:

            run_scalping()

            time.sleep(
                refresh_rate
            )

            st.rerun()

    else:

        if st.button(
            "⚡ तुरंत एक ट्रेड निष्पादित करें "
            "(One-Click Execute)"
        ):

            run_scalping()


# ============================================================
# TAB 2 — AI MENTOR & CHAT
# ============================================================

with tab2:

    st.markdown(
        "### 💬 GYAN AI Pro ट्रेडिंग मेंटर से सीधी बातचीत"
    )

    st.markdown(
        "यहाँ आप Universal Trading Institute के "
        "इस AI मेंटर से किसी भी कॉइन या अपनी "
        "ट्रेडिंग स्ट्रेटजी के बारे में हिंदी में "
        "चर्चा कर सकते हैं।"
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


        with st.chat_message("user"):

            st.markdown(
                user_query
            )


        with st.chat_message("assistant"):

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
आप GYAN AI Pro के बहुत स्मार्ट, फास्ट और
प्रोफेशनल ट्रेडिंग मेंटर हैं।

आप हमेशा शुद्ध और आसान हिंदी में जवाब देते हैं।

आपका मुख्य लक्ष्य:

- जल्दी प्रॉफिट वाले Fast Trading / Scalping स्ट्रेटजी बनाना
- हर स्ट्रेटजी को साफ और लॉजिकल रखना
- Entry, Stop Loss और Take Profit सटीक बताना
- रिस्क कम रखना और जल्दी प्रॉफिट बुक करवाना

हर जवाब में ये फॉर्मेट जरूर फॉलो करें:

1. स्ट्रेटजी का नाम

2. स्ट्रेटजी का लॉजिक

3. ट्रेड सेटअप:

- Direction: Buy / Sell
- Entry Zone:
- Stop Loss:
- Take Profit 1:
- Take Profit 2:
- Risk-Reward Ratio:

4. ट्रेडिंग प्लान:

- कितने प्रतिशत कैपिटल लगाना है
- कब एग्जिट करना है
- क्या ध्यान रखना है

5. अतिरिक्त सलाह:

नियम:

- हमेशा फास्ट और स्मार्ट सोचें
- ओवर-कॉन्फिडेंट न बनें
- अगर मार्केट साफ न हो तो साफ कह दें
- जवाब प्रोफेशनल और स्ट्रक्चर्ड रखें

वर्तमान जानकारी:

कॉइन: {chat_symbol}

मौजूदा प्राइस: {price}
"""


                    client = Groq(
                        api_key=GROQ_API_KEY
                    )


                    # ====================================================
                    # ONLY MODEL CHANGED
                    # ====================================================

                    res = client.chat.completions.create(

                        model="openai/gpt-oss-120b",

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
                        res.choices[0]
                        .message
                        .content
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

                    err_msg = (
                        f"क्षमा करें, चैट में एरर आ गया: "
                        f"{str(e)}"
                    )

                    st.error(
                        err_msg
                    )

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": err_msg
                        }
                    )
