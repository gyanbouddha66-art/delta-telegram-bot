# gemini_ai.py

import os
import requests

# ============================================================
# GH BOSS AI — GEMINI MODULE
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

MODEL = "gemini-3.6-flash"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{MODEL}:generateContent"
)


# ============================================================
# GEMINI REQUEST
# ============================================================

def ask_gemini(prompt):

    if not API_KEY:
        return (
            "❌ GEMINI ERROR\n\n"
            "GEMINI_API_KEY Render Environment "
            "Variables में नहीं मिली।"
        )

    # accidental newline / whitespace protection
    clean_prompt = str(prompt).strip()

    if not clean_prompt:
        return "भाई, अपना सवाल लिखो।"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": clean_prompt
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

        # ----------------------------------------------------
        # API ERROR
        # ----------------------------------------------------

        if response.status_code != 200:

            return (
                "❌ GEMINI API ERROR\n\n"
                f"HTTP STATUS: {response.status_code}\n\n"
                f"{response.text[:3000]}"
            )

        data = response.json()

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        candidates = data.get("candidates", [])

        if not candidates:
            return (
                "❌ GEMINI ERROR\n\n"
                "Gemini ने कोई response नहीं दिया.\n\n"
                + str(data)[:2000]
            )

        content = candidates[0].get(
            "content",
            {}
        )

        parts = content.get(
            "parts",
            []
        )

        if not parts:
            return "❌ GEMINI ERROR\nNo response parts."

        text = parts[0].get(
            "text",
            ""
        )

        if not text:
            return "❌ GEMINI ERROR\nEmpty response."

        return text.strip()

    except requests.exceptions.Timeout:

        return (
            "❌ GEMINI CONNECTION ERROR\n\n"
            "Gemini response timeout."
        )

    except requests.exceptions.RequestException as e:

        return (
            "❌ GEMINI CONNECTION ERROR\n\n"
            + str(e)
        )

    except Exception as e:

        return (
            "❌ GEMINI ERROR\n\n"
            f"TYPE: {type(e).__name__}\n"
            f"MESSAGE: {str(e)}"
        )


# ============================================================
# NORMAL GH BOSS CHAT
# ============================================================

def ask_gemini_chat(user_message):

    prompt = f"""
You are GH BOSS AI.

You are a professional AI assistant created for the user.

Speak naturally in Hindi/Hinglish unless the user asks
for another language.

You can discuss:
- normal questions
- technology
- crypto
- trading
- market concepts
- coding
- research

Do NOT pretend that you have live market data unless it is
actually supplied to you.

USER MESSAGE:
{user_message}

Give a direct, useful and natural answer.
"""

    return ask_gemini(prompt)


# ============================================================
# CRYPTO ANALYSIS
# ============================================================

def ask_gemini_analysis(symbol, market_data):

    prompt = f"""
You are GH BOSS AI, the market-analysis brain.

CRYPTO:
{symbol}

IMPORTANT:
Analyze ONLY the market data supplied below.
Do not invent live prices, volume, indicators,
news or order-book information.

MARKET DATA:
{market_data}

Analyze:

1. Market direction
2. Trend
3. Price structure
4. Momentum
5. Volume
6. Volatility
7. Support
8. Resistance
9. Bullish scenario
10. Bearish scenario
11. Risk
12. Possible trading setup

If the data does not justify a trade, clearly say:

NO TRADE

If a setup is justified, provide:

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

Do not claim certainty.
Do not fabricate missing data.
Return a clear professional analysis in Hindi.
"""

    return ask_gemini(prompt)


# ============================================================
# GEMINI CONNECTION TEST
# ============================================================

def test_gemini():

    result = ask_gemini(
        "Reply only: GH GEMINI CONNECTION OK"
    )

    if "GH GEMINI CONNECTION OK" in result:
        return {
            "success": True,
            "model": MODEL,
            "message": result
        }

    return {
        "success": False,
        "model": MODEL,
        "error": result
    }
