import os
import streamlit as st
from google import genai
from audio_recorder_streamlit import audio_recorder

# Page Config
st.set_page_config(page_title="Gemini Trading Assistant", page_icon="🎙️")
st.title("🎙️ Gemini Powered Trading & Voice Assistant")

# Gemini Setup
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

if not GEMINI_KEY:
    st.error("⚠️ Gemini API Key नहीं मिली! Please Set GEMINI_API_KEY in Environment Settings.")
else:
    client = genai.Client(api_key=GEMINI_KEY)

st.write("भाई साहब, टेक्स्ट से पूछें या नीचे माइक पर टैप करके अपनी आवाज़ में सवाल रिकॉर्ड करें:")

# Voice Input Section
st.subheader("🎤 वॉइस से सवाल पूछें")
audio_bytes = audio_recorder(text="माइक्स रिकॉर्डिंग शुरू करने के लिए टैप करें", icon_name="microphone", icon_size="2x")

user_input = ""

# Audio Processing
if audio_bytes and GEMINI_KEY:
    with st.spinner("आपकी आवाज़ सुनी जा रही है..."):
        try:
            # Send audio directly to Gemini 3.6 Flash
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[
                    "You are an expert crypto scalp trader and SMC analyst. Listen to this audio and answer the user's question in simple Hindi/Hinglish.",
                    genai.types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type="audio/wav",
                    )
                ]
            )
            st.success("🤖 **Gemini AI Voice Reply:**")
            st.write(response.text)
        except Exception as e:
            st.error(f"Voice Error: {e}")

st.divider()

# Text Input Section
st.subheader("💬 लिख कर सवाल पूछें")
text_query = st.text_input("अपनी कमांड या सवाल दर्ज करें:", placeholder="जैसे: ARCUSD में SMC liquidity sweep कैसे देखें?")

if st.button("Ask Gemini"):
    if text_query and GEMINI_KEY:
        with st.spinner("Gemini सोच रहा है..."):
            try:
                prompt = f"You are an expert crypto scalp trader, SMC analyst, and helpful assistant. Answer in simple Hindi/Hinglish: {text_query}"
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                )
                st.success("🤖 **Gemini AI Reply:**")
                st.write(response.text)
            except Exception as e:
                st.error(f"Error: {e}")
    elif not text_query:
        st.warning("कृपया सवाल लिखें।")
