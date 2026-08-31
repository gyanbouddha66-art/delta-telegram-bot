# ============================================================
# GH BOSS AI — VOICE UTILS (UPDATED & FIXED)
# ============================================================

import os
import asyncio
import tempfile
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"
GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

WHISPER_MODEL = "whisper-large-v3-turbo"
EDGE_TTS_VOICE = "hi-IN-SwaraNeural"


# ============================================================
# VOICE STATUS (REQUIRED BY TELEGRAM BOT)
# ============================================================

def voice_status():
    return {
        "voice_input": bool(GROQ_API_KEY),
        "stt": "Groq Whisper",
        "stt_model": WHISPER_MODEL,
        "tts": "Edge-TTS",
        "tts_voice": EDGE_TTS_VOICE,
        "telegram": bool(TOKEN)
    }


# ============================================================
# SEND TELEGRAM TEXT (WITH CHUNKING TO PREVENT LENGTH ERROR)
# ============================================================

def send_message(chat_id, text):
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN missing")
        return False

    try:
        text_str = str(text)
        if len(text_str) > 3900:
            chunks = [text_str[i:i+3900] for i in range(0, len(text_str), 3900)]
            success = True
            for chunk in chunks:
                res = requests.post(
                    f"{TELEGRAM_API}/sendMessage",
                    json={"chat_id": chat_id, "text": chunk},
                    timeout=20
                )
                if not res.ok:
                    success = False
            return success
        else:
            response = requests.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": text_str},
                timeout=20
            )
            return response.ok

    except Exception as e:
        print("❌ Telegram send error:", e)
        return False


# ============================================================
# SEND TELEGRAM VOICE
# ============================================================

def send_voice(chat_id, audio_file):
    if not TOKEN or not audio_file or not os.path.exists(audio_file):
        return False

    try:
        with open(audio_file, "rb") as voice:
            response = requests.post(
                f"{TELEGRAM_API}/sendVoice",
                data={"chat_id": chat_id},
                files={"voice": ("gh_boss_ai.ogg", voice, "audio/ogg")},
                timeout=60
            )
        return response.ok
    except Exception as e:
        print("❌ Voice send error:", e)
        return False


# ============================================================
# DOWNLOAD TELEGRAM VOICE
# ============================================================

def download_telegram_file(file_id):
    if not TOKEN:
        return None

    try:
        response = requests.get(
            f"{TELEGRAM_API}/getFile",
            params={"file_id": file_id},
            timeout=20
        )
        data = response.json()
        if not data.get("ok"):
            return None

        file_path = data.get("result", {}).get("file_path")
        if not file_path:
            return None

        download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        audio_response = requests.get(download_url, timeout=60)
        if not audio_response.ok:
            return None

        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
        temp.write(audio_response.content)
        temp.close()

        print("🎤 Voice downloaded:", temp.name)
        return temp.name

    except Exception as e:
        print("❌ Telegram file error:", e)
        return None


# ============================================================
# GROQ WHISPER — VOICE TO TEXT (FIXED FORMAT)
# ============================================================

def transcribe_voice(audio_file):
    if not GROQ_API_KEY:
        return None, "❌ GROQ_API_KEY missing."

    if not audio_file:
        return None, "❌ Audio file missing."

    try:
        with open(audio_file, "rb") as audio:
            response = requests.post(
                GROQ_TRANSCRIBE_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={
                    "file": (
                        "voice.ogg",
                        audio,
                        "audio/ogg"
                    )
                },
                data={
                    "model": WHISPER_MODEL,
                    "language": "hi",
                    "response_format": "json"
                },
                timeout=120
            )

        print("GROQ WHISPER STATUS:", response.status_code)

        if response.status_code != 200:
            print("GROQ WHISPER ERROR:", response.text)
            return None, "❌ Voice transcription failed\n\n" + response.text[:500]

        data = response.json()
        text = str(data.get("text", "")).strip()

        if not text:
            return None, "❌ आवाज़ समझ नहीं आई।"

        return text, None

    except Exception as e:
        print("❌ Whisper error:", e)
        return None, "❌ Voice AI Error\n\n" + str(e)


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
    await communicate.save(output_file)


# ============================================================
# TEXT → VOICE
# ============================================================

def text_to_voice(text):
    try:
        text = str(text).strip()
        if not text:
            return None

        if len(text) > 3000:
            text = text[:3000]

        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        output_file = temp.name
        temp.close()

        try:
            asyncio.run(_edge_tts_generate(text, output_file))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_edge_tts_generate(text, output_file))
            finally:
                loop.close()

        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            return None

        return output_file

    except Exception as e:
        print("❌ Edge-TTS ERROR:", e)
        return None


# ============================================================
# COMPLETE VOICE PROCESS
# ============================================================

def process_voice(chat_id, file_id, ai_function):
    send_message(chat_id, "🎤 Voice received...\n🧠 GH BOSS AI सुन रहा है...")

    audio_file = download_telegram_file(file_id)
    if not audio_file:
        send_message(chat_id, "❌ Voice file download नहीं हो पाई।")
        return False

    try:
        text, error = transcribe_voice(audio_file)
        if error:
            send_message(chat_id, error)
            return False

        print("🎤 USER SAID:", text)
        send_message(chat_id, "🎤 आपने कहा:\n\n" + text)

        answer = ai_function(text)
        answer = str(answer).strip()
        if not answer:
            answer = "AI ने कोई जवाब नहीं दिया।"

        send_message(chat_id, "🧠 GH BOSS AI\n\n" + answer)

        voice_file = text_to_voice(answer)
        if voice_file:
            send_voice(chat_id, voice_file)
            try:
                os.remove(voice_file)
            except Exception:
                pass
        else:
            send_message(chat_id, "⚠️ Voice reply generate नहीं हो पाया।")

        return True

    except Exception as e:
        print("❌ PROCESS VOICE ERROR:", e)
        send_message(chat_id, "❌ Voice processing error\n\n" + str(e))
        return False

    finally:
        try:
            if os.path.exists(audio_file):
                os.remove(audio_file)
        except Exception:
            pass
