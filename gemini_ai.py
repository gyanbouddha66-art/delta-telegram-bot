import os
import requests

# ============================================================
# GH BOSS AI — NORMAL CHAT GEMINI
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

MODEL = "gemini-3.6-flash"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{MODEL}:generateContent"
)


# ============================================================
# CORE GEMINI
# ============================================================

def ask_gemini(prompt):

    if not API_KEY:
        return "❌ GEMINI ERROR\nGEMINI_API_KEY missing."

    prompt = str(prompt).strip()

    if not prompt:
        return "भाई, क्या पूछना है लिखो।"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY
    }

    try:

        response = requests.post(
            GEMINI_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return (
                "❌ GEMINI API ERROR\n\n"
                f"HTTP: {response.status_code}\n\n"
                f"{response.text[:3000]}"
            )

        data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:
            return (
                "❌ GEMINI ERROR\n"
                "No response returned."
            )

        parts = (
            candidates[0]
            .get("content", {})
            .get("parts", [])
        )

        if not parts:
            return "❌ GEMINI ERROR\nEmpty response."

        answer = parts[0].get("text", "")

        if not answer:
            return "❌ GEMINI ERROR\nEmpty Gemini text."

        return answer.strip()

    except requests.exceptions.Timeout:
        return "❌ GEMINI TIMEOUT\nGemini ने समय पर जवाब नहीं दिया।"

    except requests.exceptions.RequestException as e:
        return f"❌ GEMINI CONNECTION ERROR\n{e}"

    except Exception as e:
        return (
            "❌ GEMINI ERROR\n"
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# NORMAL CHAT
# ============================================================

def ask_gemini_chat(user_message):

    prompt = f"""
You are GH BOSS AI.

You are a natural conversational AI assistant.

The user can talk to you normally about anything.

Rules:

- Understand the user's actual message.
- Answer the actual question.
- Do not repeat a fixed answer.
- Do not assume every message is about trading.
- If the user asks a normal question, answer normally.
- If the user asks about crypto, discuss crypto.
- If the user asks about trading, discuss trading.
- If the user asks for market analysis, explain that live
  market data is required before claiming a live analysis.
- Never pretend that data is live when it was not supplied.
- Speak naturally in Hindi/Hinglish.
- Be concise but useful.

USER MESSAGE:

{user_message}

Now answer the user's actual message.
"""

    return ask_gemini(prompt)


# ============================================================
# CRYPTO ANALYSIS
# ============================================================

def ask_gemini_analysis(symbol, market_data):

    prompt = f"""
You are GH BOSS AI.

Perform a professional crypto market analysis.

CRYPTO:
{symbol}

REAL MARKET DATA:
{market_data}

Analyze the supplied data.

Cover:

Trend
Market Structure
Momentum
Volume
Volatility
Support
Resistance
Bullish Scenario
Bearish Scenario
Risk

Then give:

DECISION:
BUY / SELL / NO TRADE

ENTRY:
...

STOP LOSS:
...

TAKE PROFIT:
...

INVALIDATION:
...

CONFIDENCE:
0-100%

REASON:
...

IMPORTANT:

Only use the supplied market data.
Do not invent prices or indicators.
Do not claim certainty.

Answer in Hindi/Hinglish.
"""

    return ask_gemini(prompt)


# ============================================================
# CONNECTION TEST
# ============================================================

def test_gemini():

    result = ask_gemini(
        "Reply only with: GH GEMINI CONNECTION OK"
    )

    return {
        "success": "GH GEMINI CONNECTION OK" in result,
        "model": MODEL,
        "response": result
    }
