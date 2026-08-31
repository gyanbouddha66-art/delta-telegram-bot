import os
import tempfile
import asyncio
import requests
import edge_tts

from trading_engine import get_engine_status, get_signal
from groq_ai import ask_groq
from delta_api import test_delta, get_delta_balances


# ============================================================
# GH BOSS AI — TELEGRAM BOT
# GROQ + TELEGRAM + DELTA + VOICE
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

WHISPER_MODEL = "whisper-large-v3-turbo"


# ============================================================
# SEND TEXT MESSAGE
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
            "❌ Telegram Error:",
            e
        )

        return False


# ============================================================
# SEND VOICE
# ============================================================

def send_voice(chat_id, audio_file):

    if not TOKEN:

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
                        "gh_boss_ai.mp3",
                        voice,
                        "audio/mpeg"
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
            "❌ Voice Send Error:",
            e
        )

        return False


# ============================================================
# DOWNLOAD TELEGRAM FILE
# ============================================================

def download_telegram_file(file_id):

    if not TOKEN:

        return None

    try:

        result = requests.get(

            f"{TELEGRAM_API}/getFile",

            params={
                "file_id": file_id
            },

            timeout=20
        )

        data = result.json()

        if not data.get("ok"):

            print(
                "❌ Telegram getFile error:",
                data
            )

            return None

        file_path = data["result"]["file_path"]

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
                "❌ Audio download failed:",
                audio_response.status_code
            )

            return None

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
            "✅ Voice file downloaded:",
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
# GROQ WHISPER — VOICE → TEXT
# ============================================================

def transcribe_voice(audio_file):

    if not GROQ_API_KEY:

        return (
            None,
            "❌ GROQ_API_KEY missing."
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
                    "model": WHISPER_MODEL,
                    "language": "hi",
                    "response_format": "json"
                },

                timeout=120
            )

        print(
            "GROQ WHISPER:",
            response.status_code,
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

        return (
            text,
            None
        )

    except Exception as e:

        print(
            "❌ Whisper Error:",
            e
        )

        return (

            None,

            "❌ Voice AI Error\n\n"
            + str(e)
        )


# ============================================================
# EDGE TTS — TEXT → VOICE
# ============================================================

def text_to_voice(text):

    try:

        text = str(
            text
        ).strip()

        if not text:

            return None

        # बहुत लंबा voice response न बनाएं
        if len(text) > 3000:

            text = text[:3000]

        temp = tempfile.NamedTemporaryFile(

            delete=False,

            suffix=".mp3"
        )

        temp.close()

        async def generate_voice():

            communicate = edge_tts.Communicate(

                text,

                "hi-IN-SwaraNeural"
            )

            await communicate.save(
                temp.name
            )

        asyncio.run(
            generate_voice()
        )

        print(
            "✅ Edge TTS generated:",
            temp.name
        )

        return temp.name

    except Exception as e:

        print(
            "❌ Edge TTS Error:",
            e
        )

        return None


# ============================================================
# AI CHAT
# ============================================================

def ai_chat(
    chat_id,
    user_text,
    voice_reply=False
):

    print(
        "🧠 GH BOSS AI:",
        user_text
    )

    send_message(
        chat_id,
        "🧠 GH BOSS AI analyzing..."
    )

    try:

        prompt = f"""
You are GH BOSS AI.

User message:

{user_text}

Understand the exact question.

NORMAL CONVERSATION:
You can answer general questions normally.

CRYPTO:
You can discuss:

BTC
ETH
SOL
ARCUSD

If another cryptocurrency is mentioned,
discuss that cryptocurrency too.

TRADING ANALYSIS:

When appropriate discuss:

Direction
Trend
Momentum
Price Action
Support
Resistance
Entry
Stop Loss
Take Profit
Risk/Reward
Invalidation

LIVE DATA RULE:

Never invent a live price.

If verified live market data is not supplied,
clearly say:

"मेरे पास verified live market data उपलब्ध नहीं है।"

Do not pretend old prices are current.

EXECUTION RULE:

Normal AI chat must NOT place an order.

Do not claim that an order was placed.

Do not claim an order was executed unless
the actual trading engine confirms execution.

Reply in Hindi unless the user uses another language.

Keep the answer concise and useful.

User has manual control over trading execution.
"""

        answer = ask_groq(
            prompt
        )

        answer = str(
            answer
        ).strip()

        if not answer:

            answer = (
                "AI ने कोई response नहीं दिया।"
            )


        # ====================================================
        # SEND TEXT
        # ====================================================

        remaining = answer

        while len(remaining) > 3900:

            part = remaining[:3900]

            remaining = remaining[3900:]

            send_message(

                chat_id,

                "🧠 GH BOSS AI\n\n"
                + part
            )

        if remaining:

            send_message(

                chat_id,

                "🧠 GH BOSS AI\n\n"
                + remaining
            )


        # ====================================================
        # SEND VOICE
        # ====================================================

        if voice_reply:

            audio_file = text_to_voice(
                answer
            )

            if audio_file:

                send_voice(

                    chat_id,

                    audio_file
                )

                try:

                    os.remove(
                        audio_file
                    )

                except:

                    pass

            else:

                send_message(

                    chat_id,

                    "⚠️ Voice reply generate नहीं हो पाया।"
                )

    except Exception as e:

        print(
            "❌ GROQ CHAT ERROR:",
            e
        )

        send_message(

            chat_id,

            "❌ GROQ AI ERROR\n\n"
            + str(e)
        )


# ============================================================
# VOICE MESSAGE HANDLER
# ============================================================

def process_voice(
    chat_id,
    file_id
):

    print(
        "🎤 VOICE MESSAGE RECEIVED"
    )

    send_message(

        chat_id,

        "🎤 Voice received...\n"
        "🧠 GH BOSS AI सुन रहा है..."
    )

    audio_file = download_telegram_file(
        file_id
    )

    if not audio_file:

        send_message(

            chat_id,

            "❌ Voice file download नहीं हो पाई।"
        )

        return


    try:

        text, error = transcribe_voice(
            audio_file
        )

        if error:

            send_message(
                chat_id,
                error
            )

            return


        print(
            "🎤 TRANSCRIBED:",
            text
        )


        # User ने क्या कहा
        send_message(

            chat_id,

            "🎤 आपने कहा:\n\n"
            + text
        )


        # AI response + voice
        ai_chat(

            chat_id,

            text,

            voice_reply=True
        )


    except Exception as e:

        print(
            "❌ VOICE PROCESS ERROR:",
            e
        )

        send_message(

            chat_id,

            "❌ Voice processing error\n\n"
            + str(e)
        )


    finally:

        try:

            os.remove(
                audio_file
            )

        except:

            pass


# ============================================================
# START
# ============================================================

def command_start(chat_id):

    send_message(

        chat_id,

        "🧠 GH BOSS AI\n\n"

        "✅ Telegram Connected\n"
        "✅ Command System Online\n"
        "✅ Groq AI Loaded\n"
        "✅ Delta Module Loaded\n"
        "🎤 Voice Input Enabled\n"
        "🔊 Voice Reply Enabled\n\n"

        "🤖 NORMAL CHAT ENABLED\n\n"

        "आप text या voice दोनों में सवाल पूछ सकते हैं।\n\n"

        "Examples:\n"

        "BTC कैसा है?\n"
        "ETH analysis करो\n"
        "SOL trend बताओ\n"
        "ARCUSD analysis करो\n"
        "नमस्ते\n\n"

        "COMMANDS\n\n"

        "/status\n"
        "/delta\n"
        "/balance\n"
        "/signal\n"
        "/ai\n"
        "/help\n\n"

        "🎤 Voice → Groq Whisper\n"
        "🧠 Groq AI\n"
        "🔊 Edge TTS\n\n"

        "Trading Execution: MANUAL"
    )


# ============================================================
# STATUS
# ============================================================

def command_status(chat_id):

    try:

        status = get_engine_status()

        delta = test_delta()

        groq_ok = bool(
            GROQ_API_KEY
        )

        send_message(

            chat_id,

            "📊 GH BOSS STATUS\n\n"

            f"Engine: "
            f"{status.get('engine', 'UNKNOWN')}\n"

            f"Mode: "
            f"{status.get('mode', 'UNKNOWN')}\n"

            f"Signal: "
            f"{status.get('signal', 'NO SIGNAL')}\n"

            f"Confidence: "
            f"{status.get('confidence', 0)}%\n\n"

            "Telegram: CONNECTED 🟢\n"

            f"Groq: "
            f"{'CONNECTED 🟢' if groq_ok else 'MISSING 🔴'}\n"

            f"Delta: "
            f"{'CONNECTED 🟢' if delta.get('success') else 'ERROR 🔴'}\n"

            "Voice Input: ENABLED 🎤\n"
            "Voice Reply: ENABLED 🔊\n"
            "Gemini: REMOVED\n"
            "Execution: MANUAL"
        )

    except Exception as e:

        send_message(

            chat_id,

            "❌ STATUS ERROR\n\n"
            + str(e)
        )


# ============================================================
# DELTA
# ============================================================

def command_delta(chat_id):

    send_message(

        chat_id,

        "🔄 Testing Delta API..."
    )

    try:

        result = test_delta()

        if result.get("success"):

            send_message(

                chat_id,

                "🟢 DELTA API OK\n\n"

                "Authentication: OK\n"
                "Connection: OK\n"
                "Read-only test completed.\n"
                "No order placed."
            )

        else:

            send_message(

                chat_id,

                "🔴 DELTA API ERROR\n\n"

                + str(
                    result.get(
                        "error",
                        "Unknown error"
                    )
                )
            )

    except Exception as e:

        send_message(

            chat_id,

            "❌ DELTA ERROR\n\n"
            + str(e)
        )


# ============================================================
# BALANCE
# ============================================================

def command_balance(chat_id):

    send_message(

        chat_id,

        "💰 Checking Delta balance..."
    )

    try:

        result = get_delta_balances()

        if not result.get("success"):

            send_message(

                chat_id,

                "❌ BALANCE ERROR\n\n"

                + str(
                    result.get(
                        "error",
                        "Unknown error"
                    )
                )
            )

            return


        send_message(

            chat_id,

            "💰 DELTA ACCOUNT\n\n"

            + str(result)
        )

    except Exception as e:

        send_message(

            chat_id,

            "❌ BALANCE ERROR\n\n"
            + str(e)
        )


# ============================================================
# SIGNAL
# ============================================================

def command_signal(chat_id):

    try:

        signal = get_signal()

        direction = signal.get(
            "signal",
            "NO SIGNAL"
        )

        confidence = signal.get(
            "confidence",
            0
        )

        reason = signal.get(
            "reason",
            "No reason available"
        )

        send_message(

            chat_id,

            "📈 GH MARKET SIGNAL\n\n"

            f"Signal: {direction}\n"
            f"Confidence: {confidence}%\n\n"

            f"Analysis:\n{reason}\n\n"

            "Execution: MANUAL"
        )

    except Exception as e:

        send_message(

            chat_id,

            "❌ SIGNAL ERROR\n\n"
            + str(e)
        )


# ============================================================
# AI COMMAND
# ============================================================

def command_ai(chat_id):

    ai_chat(

        chat_id,

        "नमस्ते GH BOSS AI, सामान्य बातचीत शुरू करो।"
    )


# ============================================================
# HELP
# ============================================================

def command_help(chat_id):

    send_message(

        chat_id,

        "🧠 GH BOSS AI\n\n"

        "COMMANDS\n\n"

        "/start\n"
        "Bot start\n\n"

        "/status\n"
        "System status\n\n"

        "/delta\n"
        "Delta API test\n\n"

        "/balance\n"
        "Delta balance\n\n"

        "/signal\n"
        "Trading signal\n\n"

        "/ai\n"
        "AI chat\n\n"

        "/help\n"
        "Commands\n\n"

        "━━━━━━━━━━━━━━\n"
        "🎤 VOICE AI\n"
        "━━━━━━━━━━━━━━\n\n"

        "Telegram में voice message भेजें।\n\n"

        "🎤 Voice\n"
        "↓\n"
        "🧠 Groq Whisper\n"
        "↓\n"
        "📝 Text\n"
        "↓\n"
        "🧠 GH BOSS AI\n"
        "↓\n"
        "🔊 Edge TTS\n\n"

        "AI: GROQ\n"
        "Voice STT: GROQ WHISPER\n"
        "Voice TTS: EDGE-TTS\n"
        "Gemini: REMOVED\n\n"

        "Trading Execution: MANUAL"
    )


# ============================================================
# MAIN ROUTER
# ============================================================

def process_command(
    chat_id,
    command
):

    if not command:

        return

    original_text = str(
        command
    ).strip()

    if not original_text:

        return

    command_lower = (
        original_text.lower()
    )


    # /start@botname
    if (

        command_lower.startswith("/")

        and

        "@"
        in command_lower

    ):

        command_lower = (
            command_lower
            .split("@")[0]
        )


    print(
        "🎯 TELEGRAM MESSAGE:",
        original_text
    )


    try:

        if command_lower == "/start":

            command_start(
                chat_id
            )

        elif command_lower == "/status":

            command_status(
                chat_id
            )

        elif command_lower == "/delta":

            command_delta(
                chat_id
            )

        elif command_lower == "/balance":

            command_balance(
                chat_id
            )

        elif command_lower == "/signal":

            command_signal(
                chat_id
            )

        elif command_lower == "/ai":

            command_ai(
                chat_id
            )

        elif command_lower == "/help":

            command_help(
                chat_id
            )

        else:

            ai_chat(

                chat_id,

                original_text
            )


    except Exception as e:

        print(
            "❌ COMMAND ROUTER ERROR:",
            e
        )

        send_message(

            chat_id,

            "❌ SYSTEM ERROR\n\n"
            + str(e)
        )
