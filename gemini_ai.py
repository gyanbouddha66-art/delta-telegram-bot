import os
from google import genai


# ============================================================
# GH GEMINI AI
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

_client = None


# ============================================================
# CREATE CLIENT
# ============================================================

def get_client():

    global _client

    if _client is not None:
        return _client

    if not API_KEY:
        raise Exception(
            "GEMINI_API_KEY missing"
        )

    _client = genai.Client(
        api_key=API_KEY
    )

    return _client


# ============================================================
# ASK GEMINI
# ============================================================

def ask_gemini(prompt):

    try:

        client = get_client()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=str(prompt)
        )

        text = getattr(
            response,
            "text",
            None
        )

        if text is None:
            return "Gemini ने कोई text response नहीं दिया।"

        # ----------------------------------------------------
        # FORCE UTF-8 SAFE TEXT
        # ----------------------------------------------------

        return str(text)

    except Exception as e:

        return (
            "Gemini Error: "
            + str(e)
        )
