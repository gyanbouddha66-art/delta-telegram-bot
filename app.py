import os
import streamlit as st
from google import genai

# Page Config
st.set_page_config(page_title="Gemini Trading Assistant", page_icon="🎙️")
st.title("🎙️ Gemini Powered Trading & Voice Assistant")

# Gemini Setup
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

if not GEMINI_KEY:
    st.error("⚠️ Gemini API Key नहीं मिली! Please Set GEMINI_API_KEY in Environment Settings.")
else:
    client = genai.Client(api_key=GEMINI_KEY)

# UI Layout
st.write("भाई साहब, स्मार्ट मनी कॉन्सेप्ट्स (SMC), रिस्क मैनेजमेंट या बॉट स्टेटस के बारे में कुछ भी पूछें:")

user_input = st.text_input("अपनी कमांड या सवाल दर्ज करें:", placeholder="जैसे: ARCUSD में SMC liquidity sweep कैसे देखें?")

if st.button("Ask Gemini"):
    if user_input and GEMINI_KEY:
        with st.spinner("Gemini सोच रहा है..."):
            try:
                prompt = f"You are an expert crypto scalp trader, SMC analyst, and helpful assistant. Answer in simple Hindi/Hinglish: {user_input}"
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                )
                st.success("🤖 **Gemini AI Reply:**")
                st.write(response.text)
            except Exception as e:
                st.error(f"Error: {e}")
    elif not user_input:
        st.warning("कृपया सवाल लिखें।")
