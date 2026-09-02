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
# GH BOSS AI - DELTA SCALPER
# ============================================================

BASE_URL = "https://api.india.delta.exchange"

SYMBOL = "ARCUSD"
LOT_SIZE = 1

SL_PERCENT = 0.005   # 0.5%
TP_PERCENT = 0.010   # 1.0%

SCAN_SECONDS = 30    # reserved for future auto mode


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="GH BOSS AI",
    page_icon="⚡"
)

st.title("⚡ GH BOSS AI")
st.subheader("Delta Exchange India - ARCUSD Scalper")


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
        if not DELTA_API_KEY:
            raise Exception("DELTA_API_KEY missing")
        if not DELTA_API_SECRET:
            raise Exception("DELTA_API_SECRET missing")

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
            "HTTP " + str(response.status_code) + " " + str(data)
        )

    return data


# ============================================================
# PRODUCT / TICKER / CANDLES
# ============================================================

def get_product():
    data = delta_request("GET", "/v2/products/" + SYMBOL)
    if not data.get("success"):
        raise Exception(str(data))
    return data["result"]


def get_ticker():
    data = delta_request("GET", "/v2/tickers/" + SYMBOL)
    if not data.get("success"):
        raise Exception(str(data))
    return data["result"]


def get_candles():
    end_time = int(time.time())
    start_time = end_time - 3600  # last 60 minutes

    params = {
        "resolution": "1m",
        "symbol": SYMBOL,
        "start": start_time,
        "end": end_time
    }

    data = delta_request("GET", "/v2/history/candles", params=params)
    if not data.get("success"):
        raise Exception(str(data))
    return data["result"]


# ============================================================
# AI SIGNAL (Groq)
# ============================================================

def get_signal(candles):
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY missing")

    if len(candles) < 10:
        return "NO_TRADE"

    recent = candles[-20:]
    candle_text = "\n".join(str(c) for c in recent)

    prompt = f"""
You are a strict 1-minute crypto scalping engine.

Analyze these ARCUSD candles.

Return ONLY one of:

BUY
SELL
NO_TRADE

Do not explain anything else.

CANDLES:
{candle_text}
"""

    client = Groq(api_key=GROQ_API_KEY)

    result = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=5
    )

    answer = (
        result.choices[0]
        .message
        .content
        .strip()
        .upper()
    )

    if answer in ("BUY", "SELL"):
        return answer
    return "NO_TRADE"


# ============================================================
# POSITION
# ============================================================

def get_position(product_id):
    data = delta_request(
        "GET",
        "/v2/positions",
        params={"product_id": product_id},
        auth=True
    )

    if not data.get("success"):
        raise Exception(str(data))

    result = data.get("result")

    if isinstance(result, list):
        if len(result) == 0:
            return None
        return result[0]

    return result


# ============================================================
# MARKET ORDER
# ============================================================

def place_order(side):
    body = {
        "product_symbol": SYMBOL,
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

    if not data.get("success"):
        raise Exception(str(data))

    return data["result"]


# ============================================================
# BRACKET (SL + TP)
# ============================================================

def place_bracket(side, entry):
    entry = float(entry)

    if side == "buy":
        stop = entry * (1 - SL_PERCENT)
        target = entry * (1 + TP_PERCENT)
    else:
        stop = entry * (1 + SL_PERCENT)
        target = entry * (1 - TP_PERCENT)

    body = {
        "product_symbol": SYMBOL,
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

    data = delta_request(
        "POST",
        "/v2/orders/bracket",
        body=body,
        auth=True
    )

    if not data.get("success"):
        raise Exception(str(data))

    return data["result"]


# ============================================================
# TEST API
# ============================================================

if st.button("🔐 TEST DELTA API"):
    try:
        result = delta_request(
            "GET",
            "/v2/orders",
            params={"page_size": 1},
            auth=True
        )
        st.success("Delta API OK")
        st.json(result)
    except Exception as error:
        st.error("Delta API ERROR: " + str(error))


# ============================================================
# MARKET DATA
# ============================================================

st.divider()

try:
    product = get_product()
    ticker = get_ticker()

    st.write("Product ID:", product.get("id"))
    st.write("Symbol:", SYMBOL)
    st.write("Mark Price:", ticker.get("mark_price"))
    st.write("Last Price:", ticker.get("close"))
except Exception as error:
    st.error("Market data error: " + str(error))


# ============================================================
# MANUAL SCAN + REAL TRADE
# ============================================================

st.divider()

if st.button("⚡ SCAN + REAL TRADE"):
    try:
        product = get_product()
        product_id = product.get("id")

        candles = get_candles()
        signal = get_signal(candles)

        st.write("AI SIGNAL:", signal)

        if signal == "NO_TRADE":
            st.info("No trade signal from AI.")
        else:
            # Check existing position
            position = get_position(product_id)
            size = 0.0
            if position:
                size = float(position.get("size") or 0)

            if size != 0:
                st.warning(f"Already in position (size={size}). Skipping new entry.")
            else:
                side = "buy" if signal == "BUY" else "sell"

                st.write(f"Placing {side.upper()} market order...")
                order = place_order(side)
                st.json(order)

                # Prefer average fill price, fallback to current mark
                entry = order.get("average_fill_price")
                if not entry:
                    ticker = get_ticker()
                    entry = ticker.get("mark_price")

                if not entry:
                    raise Exception("Could not determine entry price")

                st.write(f"Entry price used for bracket: {entry}")

                bracket = place_bracket(side, entry)
                st.success("Bracket (SL + TP) placed successfully")
                st.json(bracket)

    except Exception as error:
        st.error("Trade error: " + str(error))
