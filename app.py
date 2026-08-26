import os
import streamlit as st
from google import genai
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io

# Page Config
st.set_page_config(page_title="Gemini Fast Voice Trading Assistant", page_icon="🎙️")
st.title("🎙️ Gemini Powered Trading & Voice Assistant")

# Gemini Setup
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

if not GEMINI_KEY:
    st.error("⚠️ Gemini API Key नहीं मिली! Please Set GEMINI_API_KEY in Environment Settings.")
else:
    client = genai.Client(api_key=GEMINI_KEY)

# Function to play audio response fast
def speak(text):
    try:
        # Convert text to Hindi speech
        tts = gTTS(text=text, lang='hi', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format="audio/mp3", autoplay=True)
    except Exception as e:
        st.warning(f"Audio Output Error: {e}")

st.write("भाई साहब, बोलकर या लिखकर सवाल पूछें — Gemini तुरंत बोलकर जवाब देगा:")

# Voice Input Section
st.subheader("🎤 बोलकर पूछें")
audio_bytes = audio_recorder(text="रिकॉर्डिंग शुरू करने के लिए टैप करें", icon_name="microphone", icon_size="2x")

if audio_bytes and GEMINI_KEY:
    with st.spinner("Gemini सुन रहा है और सोच रहा है..."):
        try:
            prompt = "You are a fast SMC trading assistant. Keep response concise (under 3-4 sentences) and answer in natural spoken Hindi/Hinglish."
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[
                    prompt,
                    genai.types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
                ]
            )
            reply_text = response.text
            st.success("🤖 **Gemini AI Answer:**")
            st.write(reply_text)
            speak(reply_text)  # बोलकर सुनाएगा
        except Exception as e:
            st.error(f"Voice Error: {e}")

st.divider()

# Text Input Section
st.subheader("💬 लिखकर पूछें")
text_query = st.text_input("अपनी कमांड या सवाल दर्ज करें:", placeholder="जैसे: ARCUSD में Liquidity Sweep कैसे पहचानें?")

if st.button("Ask Gemini"):
    if text_query and GEMINI_KEY:
        with st.spinner("Gemini सोच रहा है..."):
            try:
                prompt = f"You are a fast SMC trading assistant. Keep response concise (under 3-4 sentences) and answer in natural spoken Hindi/Hinglish: {text_query}"
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                )
                reply_text = response.text
                st.success("🤖 **Gemini AI Answer:**")
                st.write(reply_text)
                speak(reply_text)  # बोलकर सुनाएगा
            except Exception as e:
                st.error(f"Error: {e}")
    elif not text_query:
        st.warning("कृपया सवाल लिखें।")
