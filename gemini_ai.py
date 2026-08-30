import os
import traceback

from google import genai


# ============================================================
# GEMINI CONFIG
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

_client = None


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_client():

    global _client

    if _client is None:

        if not API_KEY:
            raise Exception(
                "GEMINI_API_KEY is missing in Render Environment"
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

        # ----------------------------------------------------
        # VERY SIMPLE ASCII-ONLY TEST
        # ----------------------------------------------------

        test_prompt = (
            "Explain in simple English what "
            "a professional trading system "
            "checks before taking a trade. "
            "Do not recommend a live trade."
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=test_prompt
        )

        text = response.text

        if not text:

            return "Gemini returned an empty response."

        return text

    except Exception as e:

        # ----------------------------------------------------
        # DIAGNOSTIC ERROR
        # ----------------------------------------------------

        error_type = type(e).__name__

        try:
            error_message = str(e)
        except Exception:
            error_message = "Unable to read exception"

        return (
            "GEMINI_ERROR\n"
            "TYPE: "
            + error_type
            + "\n"
            "MESSAGE: "
            + error_message
        )
