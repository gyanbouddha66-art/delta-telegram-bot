
# ============================================================
# GH BOSS AI — VOICE UTILS
# GROQ WHISPER STT + EDGE-TTS
# Telegram Voice Input + Voice Reply
# ============================================================

import os
import asyncio
import tempfile
import requests

# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    ""
).strip()

TELEGRAM_API = (
    f"https://api.telegram.org/bot{TOKEN}"
)

GROQ_TRANSCRIBE_URL = (
    "https://api.groq.com/openai/v1/audio/transcriptions"
)

# Groq Whisper
WHISPER_MODEL = "whisper-large-v3-turbo"

# Edge-TTS Hindi voice
# Hindi female voice
EDGE_TTS_VOICE = "hi-IN-SwaraNeural"


# ============================================================
# SEND TELEGRAM TEXT
# ============================================================

def send_message(chat_id, text):

    if not TOKEN:

        print(
            "❌ TELEGRAM_BOT_TOKEN missing"
        )

        return False

    try:

        response = requests.post(

            f"{TELEGRAM_API}/sendMessage",

            json={
                "chat_id": chat_id,
                "text": str(text)
            },

            timeout=20
        )

        print(
            "Telegram:",
            response.status_code,
            response.text[:300]
        )

        return response.ok

    except Exception as e:

        print(
            "❌ Telegram send error:",
            e
        )

        return False


# ============================================================
# SEND TELEGRAM VOICE
# ============================================================

def send_voice(chat_id, audio_file):

    if not TOKEN:

        print(
            "❌ TELEGRAM_BOT_TOKEN missing"
        )

        return False

    if not audio_file:

        return False

    if not os.path.exists(audio_file):

        print(
            "❌ Voice file not found"
        )

        return False

    try:

        with open(
            audio_file,
            "rb"
        ) as voice:

            response = requests.post(

                f"{TELEGRAM_API}/sendVoice",

                data={
                    "chat_id": chat_id
                },

                files={
                    "voice": (
                        "gh_boss_ai.ogg",
                        voice,
                        "audio/ogg"
                    )
                },

                timeout=60
            )

        print(
            "Telegram Voice:",
            response.status_code,
            response.text[:300]
        )

        return response.ok

    except Exception as e:

        print(
            "❌ Voice send error:",
            e
        )

        return False


# ============================================================
# DOWNLOAD TELEGRAM VOICE
# ============================================================

def download_telegram_file(file_id):

    if not TOKEN:

        print(
            "❌ TELEGRAM_BOT_TOKEN missing"
        )

        return None

    try:

        # ----------------------------------------------------
        # GET FILE PATH
        # ----------------------------------------------------

        response = requests.get(

            f"{TELEGRAM_API}/getFile",

            params={
                "file_id": file_id
            },

            timeout=20
        )

        data = response.json()

        if not data.get("ok"):

            print(
                "❌ Telegram getFile error:",
                data
            )

            return None

        file_path = (
            data
            .get("result", {})
            .get("file_path")
        )

        if not file_path:

            print(
                "❌ Telegram file_path missing"
            )

            return None

        # ----------------------------------------------------
        # DOWNLOAD FILE
        # ----------------------------------------------------

        download_url = (
            f"https://api.telegram.org/"
            f"file/bot{TOKEN}/{file_path}"
        )

        audio_response = requests.get(

            download_url,

            timeout=60
        )

        if not audio_response.ok:

            print(
                "❌ Voice download failed:",
                audio_response.status_code
            )

            return None

        # ----------------------------------------------------
        # TEMP FILE
        # ----------------------------------------------------

        suffix = os.path.splitext(
            file_path
        )[1]

        if not suffix:

            suffix = ".ogg"

        temp = tempfile.NamedTemporaryFile(

            delete=False,

            suffix=suffix
        )

        temp.write(
            audio_response.content
        )

        temp.close()

        print(
            "🎤 Voice downloaded:",
            temp.name
        )

        return temp.name

    except Exception as e:

        print(
            "❌ Telegram file error:",
            e
        )

        return None


# ============================================================
# GROQ WHISPER — VOICE TO TEXT
# ============================================================

def transcribe_voice(audio_file):

    if not GROQ_API_KEY:

        return (
            None,
            "❌ GROQ_API_KEY missing."
        )

    if not audio_file:

        return (
            None,
            "❌ Audio file missing."
        )

    try:

        with open(
            audio_file,
            "rb"
        ) as audio:

            response = requests.post(

                GROQ_TRANSCRIBE_URL,

                headers={
                    "Authorization":
                    f"Bearer {GROQ_API_KEY}"
                },

                files={
                    "file": (
                        os.path.basename(
                            audio_file
                        ),
                        audio,
                        "audio/ogg"
                    )
                },

                data={

                    "model":
                    WHISPER_MODEL,

                    "language":
                    "hi",

                    "response_format":
                    "json"
                },

                timeout=120
            )

        print(
            "GROQ WHISPER:",
            response.status_code
        )

        print(
            response.text[:500]
        )

        if response.status_code != 200:

            return (

                None,

                "❌ Voice transcription failed\n\n"
                + response.text[:1500]
            )

        data = response.json()

        text = str(

            data.get(
                "text",
                ""
            )

        ).strip()

        if not text:

            return (

                None,

                "❌ आवाज़ समझ नहीं आई।"
            )

        return text, None

    except Exception as e:

        print(
            "❌ Whisper error:",
            e
        )

        return (

            None,

            "❌ Voice AI Error\n\n"
            + str(e)
        )


# ============================================================
# EDGE-TTS ASYNC
# ============================================================

async def _edge_tts_generate(text, output_file):

    import edge_tts

    communicate = edge_tts.Communicate(

        text=str(text),

        voice=EDGE_TTS_VOICE,

        rate="+0%",

        volume="+0%",

        pitch="+0Hz"
    )

    await communicate.save(
        output_file
    )


# ============================================================
# TEXT → VOICE
# ============================================================

def text_to_voice(text):

    try:

        text = str(
            text
        ).strip()

        if not text:

            return None

        # Telegram voice बहुत लंबी न हो
        if len(text) > 3000:

            text = text[:3000]

        temp = tempfile.NamedTemporaryFile(

            delete=False,

            suffix=".mp3"
        )

        output_file = temp.name

        temp.close()

        # ----------------------------------------------------
        # EDGE TTS
        # ----------------------------------------------------

        try:

            asyncio.run(

                _edge_tts_generate(

                    text,

                    output_file
                )
            )

        except RuntimeError:

            # यदि event loop पहले से running हो
            loop = asyncio.new_event_loop()

            try:

                loop.run_until_complete(

                    _edge_tts_generate(

                        text,

                        output_file
                    )
                )

            finally:

                loop.close()

        if not os.path.exists(
            output_file
        ):

            print(
                "❌ Edge-TTS file not created"
            )

            return None

        if os.path.getsize(
            output_file
        ) == 0:

            print(
                "❌ Edge-TTS generated empty file"
            )

            return None

        print(
            "🔊 Edge-TTS generated:",
            output_file
        )

        return output_file

    except Exception as e:

        print(
            "❌ Edge-TTS ERROR:",
            e
        )

        return None


# ============================================================
# COMPLETE VOICE PROCESS
# Telegram Voice
#       ↓
# Groq Whisper
#       ↓
# Text
#       ↓
# GH BOSS AI
#       ↓
# Edge-TTS
#       ↓
# Telegram Voice Reply
# ============================================================

def process_voice(
    chat_id,
    file_id,
    ai_function
):

    # --------------------------------------------------------
    # RECEIVED
    # --------------------------------------------------------

    send_message(

        chat_id,

        "🎤 Voice received...\n"
        "🧠 GH BOSS AI सुन रहा है..."
    )

    # --------------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------------

    audio_file = download_telegram_file(
        file_id
    )

    if not audio_file:

        send_message(

            chat_id,

            "❌ Voice file download नहीं हो पाई।"
        )

        return False

    try:

        # ----------------------------------------------------
        # SPEECH → TEXT
        # ----------------------------------------------------

        text, error = transcribe_voice(

            audio_file
        )

        if error:

            send_message(
                chat_id,
                error
            )

            return False

        print(
            "🎤 USER SAID:",
            text
        )

        # ----------------------------------------------------
        # SHOW TRANSCRIPTION
        # ----------------------------------------------------

        send_message(

            chat_id,

            "🎤 आपने कहा:\n\n"
            + text
        )

        # ----------------------------------------------------
        # AI RESPONSE
        # ai_function must return text
        # ----------------------------------------------------

        answer = ai_function(
            text
        )

        answer = str(
            answer
        ).strip()

        if not answer:

            answer = (
                "AI ने कोई जवाब नहीं दिया।"
            )

        # ----------------------------------------------------
        # TEXT RESPONSE
        # ----------------------------------------------------

        send_message(

            chat_id,

            "🧠 GH BOSS AI\n\n"
            + answer
        )

        # ----------------------------------------------------
        # AI TEXT → VOICE
        # ----------------------------------------------------

        voice_file = text_to_voice(
            answer
        )

        if voice_file:

            send_voice(

                chat_id,

                voice_file
            )

            try:

                os.remove(
                    voice_file
                )

            except Exception:

                pass

        else:

            send_message(

                chat_id,

                "⚠️ Voice reply generate नहीं हो पाया।"
            )

        return True

    except Exception as e:

        print(
            "❌ PROCESS VOICE ERROR:",
            e
        )

        send_message(

            chat_id,

            "❌ Voice processing error\n\n"
            + str(e)
        )

        return False

    finally:

        # ----------------------------------------------------
        # DELETE DOWNLOADED AUDIO
        # ----------------------------------------------------

        try:

            if os.path.exists(
                audio_file
            ):

                os.remove(
                    audio_file
                )

        except Exception:

            pass


# ============================================================
# VOICE STATUS
# ============================================================

def voice_status():

    return {

        "voice_input":
        bool(GROQ_API_KEY),

        "stt":
        "Groq Whisper",

        "stt_model":
        WHISPER_MODEL,

        "tts":
        "Edge-TTS",

        "tts_voice":
        EDGE_TTS_VOICE,

        "telegram":
        bool(TOKEN)
    }
