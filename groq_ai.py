import os
import requests

# ============================================================
# GH BOSS AI — GROQ ONLY
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODEL = "llama-3.3-70b-versatile"


# ============================================================
# GROQ CHAT
# ============================================================

def ask_groq(prompt):

    if not GROQ_API_KEY:
        return (
            "❌ GROQ ERROR\n\n"
            "GROQ_API_KEY Render Environment में missing है."
        )

    try:

        response = requests.post(
            GROQ_URL,

            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },

            json={
                "model": MODEL,

                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are GH BOSS AI.\n\n"
                            "Answer the user's actual question.\n"
                            "Do normal conversation.\n"
                            "Discuss cryptocurrencies when asked.\n"
                            "Supported assets include BTC, ETH, SOL and ARCUSD.\n"
                            "If another cryptocurrency is mentioned, discuss it too.\n"
                            "For trading questions explain trend, momentum, "
                            "support, resistance, entry, stop loss, take profit "
                            "and risk/reward when appropriate.\n"
                            "Never invent a live price.\n"
                            "If live market data is not supplied, clearly say "
                            "that verified live data is unavailable.\n"
                            "Do not place any order.\n"
                            "Reply in Hindi unless the user uses another language.\n"
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

        print("GROQ STATUS:", response.status_code)

        if response.status_code != 200:

            print(
                "GROQ RESPONSE:",
                response.text[:1000]
            )

            return (
                "❌ GROQ API ERROR\n\n"
                f"HTTP STATUS: {response.status_code}\n\n"
                f"{response.text[:1500]}"
            )

        data = response.json()

        choices = data.get("choices", [])

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

    except requests.exceptions.Timeout:

        return (
            "❌ GROQ ERROR\n\n"
            "Groq API request timeout."
        )

    except requests.exceptions.RequestException as e:

        print("GROQ REQUEST ERROR:", e)

        return (
            "❌ GROQ CONNECTION ERROR\n\n"
            f"{str(e)}"
        )

    except Exception as e:

        print("GROQ ERROR:", e)

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
