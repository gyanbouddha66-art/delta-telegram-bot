import os
from google import genai

# ============================================================
# GH BOSS AI — GEMINI 3.7 FLASH
# INTERACTIONS API
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

MODEL = "gemini-3.7-flash"

# Gemini client
client = None

if API_KEY:
    client = genai.Client(api_key=API_KEY)


# ============================================================
# ASK GEMINI
# ============================================================

def ask_gemini(prompt):

    if not API_KEY:
        return (
            "GEMINI ERROR\n\n"
            "GEMINI_API_KEY is missing."
        )

    if client is None:
        return (
            "GEMINI ERROR\n\n"
            "Gemini client was not initialized."
        )

    try:

        interaction = client.interactions.create(
            model=MODEL,
            input=prompt,
            generation_config={
                "thinking_level": "medium"
            }
        )

        answer = getattr(
            interaction,
            "output_text",
            None
        )

        if answer:
            return str(answer).strip()

        return (
            "GEMINI ERROR\n\n"
            "Gemini returned an empty response."
        )

    except Exception as e:

        return (
            "GEMINI ERROR\n\n"
            "TYPE: "
            + type(e).__name__
            + "\n\n"
            "MESSAGE: "
            + str(e)
        )


# ============================================================
# TEST
# ============================================================

def test_gemini():

    return ask_gemini(
        "Namaste GH BOSS AI. "
        "Reply in Hindi with exactly: "
        "Gemini 3.7 connected successfully."
    )
