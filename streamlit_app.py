
import streamlit as st
import requests

st.set_page_config(
    page_title="GH AI Trading",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 GH AI TRADING")
st.caption("Delta + Telegram + Gemini")

st.warning("TEST MODE — LIVE TRADING OFF")

RENDER_URL = "https://delta-telegram-bot-agg7.onrender.com"

try:
    response = requests.get(
        f"{RENDER_URL}/status",
        timeout=10
    )

    data = response.json()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Render",
        data.get("server", "UNKNOWN")
    )

    col2.metric(
        "Telegram",
        "CONNECTED"
        if data.get("telegram")
        else "NOT SET"
    )

    col3.metric(
        "Gemini",
        "CONNECTED"
        if data.get("gemini")
        else "NOT SET"
    )

    col4.metric(
        "Delta",
        "CONNECTED"
        if data.get("delta")
        else "NOT SET"
    )

    st.divider()

    st.subheader("Trading Engine")

    st.write("Mode: TEST")
    st.write("Live Trading: OFF")
    st.write("Signal: NO TRADE")

except Exception as e:

    st.error(
        f"Render connection failed: {e}"
    )
