import os
import requests

# ============================================================
# GH BOSS AI — GROQ AUTO MODEL ENGINE
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_CHAT_URL = f"{GROQ_BASE_URL}/chat/completions"
GROQ_MODELS_URL = f"{GROQ_BASE_URL}/models"


# ============================================================
# MODEL PREFERENCE
# ============================================================

PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]


# ============================================================
# GET AVAILABLE GROQ MODELS
# ============================================================

def get_available_models():

    if not GROQ_API_KEY:
        return []

    try:

        response = requests.get(
            GROQ_MODELS_URL,

            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}"
            },

            timeout=20
        )

        print(
            "GROQ MODELS STATUS:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "GROQ MODELS RESPONSE:",
                response.text[:1000]
            )

            return []

        data = response.json()

        models = data.get("data", [])

        result = []

        for model in models:

            model_id = model.get("id")

            if model_id:
                result.append(model_id)

        print(
            "AVAILABLE GROQ MODELS:",
            result
        )

        return result

    except Exception as e:

        print(
            "GROQ MODEL LIST ERROR:",
            e
        )

        return []


# ============================================================
# SELECT MODEL
# ============================================================

def select_model():

    available = get_available_models()

    if not available:

        print(
            "⚠️ Could not read Groq model list."
        )

        return None

    # First try preferred models
    for preferred in PREFERRED_MODELS:

        if preferred in available:

            print(
                "✅ SELECTED GROQ MODEL:",
                preferred
            )

            return preferred

    # Otherwise select a compatible chat model
    excluded_words = [
        "whisper",
        "guard",
        "safety",
        "tts",
        "speech",
        "audio",
        "embedding"
    ]

    for model in available:

        lower_model = model.lower()

        if any(
            word in lower_model
            for word in excluded_words
        ):
            continue

        print(
            "✅ FALLBACK GROQ MODEL:",
            model
        )

        return model

    return None


# ============================================================
# GROQ CHAT
# ============================================================

def ask_groq(prompt):

    if not GROQ_API_KEY:

        return (
            "❌ GROQ ERROR\n\n"
            "GROQ_API_KEY Render/Streamlit Environment "
            "में missing है."
        )

    model = select_model()

    if not model:

        return (
            "❌ GROQ ERROR\n\n"
            "इस API key के लिए कोई usable Groq model "
            "available नहीं मिला."
        )

    try:

        response = requests.post(

            GROQ_CHAT_URL,

            headers={
                "Authorization":
                    f"Bearer {GROQ_API_KEY}",

                "Content-Type":
                    "application/json"
            },

            json={

                "model": model,

                "messages": [

                    {
                        "role": "system",

                        "content": (
                            "You are GH BOSS AI.\n\n"

                            "Answer the user's actual question.\n"
                            "Do normal conversation.\n"

                            "Discuss cryptocurrencies when asked.\n"

                            "Supported assets include BTC, ETH, "
                            "SOL and ARCUSD.\n"

                            "If another cryptocurrency is mentioned, "
                            "discuss it too.\n"

                            "For trading questions explain trend, "
                            "momentum, support, resistance, entry, "
                            "stop loss, take profit and risk/reward "
                            "when appropriate.\n"

                            "Never invent a live price.\n"

                            "If live market data is not supplied, "
                            "clearly say that verified live data "
                            "is unavailable.\n"

                            "Do not place any order.\n"

                            "Reply in Hindi unless the user uses "
                            "another language.\n"

                            "Be concise and useful."
                        )
                    },

                    {
                        "role": "user",

                        "content": str(prompt)
                    }
                ],

                "temperature": 0.2,

                "max_tokens": 1500
            },

            timeout=45
        )

        print(
            "GROQ STATUS:",
            response.status_code
        )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        if response.status_code == 200:

            data = response.json()

            choices = data.get(
                "choices",
                []
            )

            if not choices:

                return (
                    "❌ GROQ ERROR\n\n"
                    "No response returned."
                )

            answer = (
                choices[0]
                .get("message", {})
                .get("content", "")
            )

            if not answer:

                return (
                    "❌ GROQ ERROR\n\n"
                    "Empty AI response."
                )

            return str(answer).strip()

        # ----------------------------------------------------
        # RATE LIMIT
        # ----------------------------------------------------

        if response.status_code == 429:

            print(
                "GROQ RATE LIMIT:",
                response.text[:1000]
            )

            return (
                "❌ GROQ RATE LIMIT\n\n"
                "Groq ने अभी request limit लगा दी है.\n"
                "थोड़ी देर बाद फिर कोशिश करें."
            )

        # ----------------------------------------------------
        # MODEL NOT FOUND
        # ----------------------------------------------------

        if response.status_code == 404:

            print(
                "❌ GROQ MODEL ERROR:",
                response.text[:1000]
            )

            return (
                "❌ GROQ MODEL ERROR\n\n"
                f"Selected model: {model}\n\n"
                "यह model आपकी API key के लिए available नहीं है."
            )

        # ----------------------------------------------------
        # OTHER API ERROR
        # ----------------------------------------------------

        print(
            "GROQ RESPONSE:",
            response.text[:1500]
        )

        return (
            "❌ GROQ API ERROR\n\n"
            f"HTTP STATUS: {response.status_code}\n\n"
            f"{response.text[:1500]}"
        )

    except requests.exceptions.Timeout:

        return (
            "❌ GROQ ERROR\n\n"
            "Groq API request timeout."
        )

    except requests.exceptions.RequestException as e:

        print(
            "GROQ REQUEST ERROR:",
            e
        )

        return (
            "❌ GROQ CONNECTION ERROR\n\n"
            f"{str(e)}"
        )

    except Exception as e:

        print(
            "GROQ ERROR:",
            e
        )

        return (
            "❌ GROQ ERROR\n\n"
            f"{str(e)}"
        )


# ============================================================
# SIMPLE TEST
# ============================================================

def test_groq():

    return ask_groq(
        "नमस्ते GH BOSS AI. "
        "सिर्फ इतना बताओ कि तुम connected हो."
    )


# ============================================================
# DEBUG MODEL LIST
# ============================================================

if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        "GH BOSS AI — GROQ MODEL TEST"
    )

    print(
        "=========================================="
    )

    models = get_available_models()

    print(
        "\nAVAILABLE MODELS:"
    )

    for model in models:

        print(
            "-",
            model
        )

    print(
        "\nSELECTED MODEL:",
        select_model()
    )
