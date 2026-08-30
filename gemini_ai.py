import os
import sys
import locale

from google import genai


# ============================================================
# UTF-8 ENVIRONMENT
# ============================================================

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["LANG"] = "C.UTF-8"
os.environ["LC_ALL"] = "C.UTF-8"

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# ============================================================
# GEMINI
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

_client = None


def get_client():

    global _client

    if _client is not None:
        return _client

    if not API_KEY:
        raise Exception("GEMINI_API_KEY missing")

    _client = genai.Client(
        api_key=API_KEY
    )

    return _client


# ============================================================
# SAFE TEXT
# ============================================================

def safe_text(value):

    if value is None:
        return ""

    try:
        text = str(value)

        # Force UTF-8 round trip
        text = text.encode(
            "utf-8",
            errors="replace"
        ).decode(
            "utf-8",
            errors="replace"
        )

        return text

    except Exception:

        return "Gemini response encoding error."


# ============================================================
# ASK GEMINI
# ============================================================

def ask_gemini(prompt):

    try:

        client = get_client()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=safe_text(prompt)
        )

        text = getattr(
            response,
            "text",
            None
        )

        if not text:

            return "Gemini ने कोई response नहीं दिया।"

        return safe_text(text)

    except Exception as e:

        return (
            "Gemini Error: "
            + safe_text(e)
        )
