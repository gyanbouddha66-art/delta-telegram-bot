import os
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY")

_client = None


def get_client():

    global _client

    if _client is None:

        if not API_KEY:
            raise Exception("GEMINI_API_KEY missing")

        _client = genai.Client(
            api_key=API_KEY
        )

    return _client


def ask_gemini(prompt):

    try:

        client = get_client()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        # IMPORTANT:
        # Do not encode/decode the Gemini response.
        text = response.text

        if text is None:
            return "EMPTY_GEMINI_RESPONSE"

        return text

    except Exception as e:

        # Only ASCII characters in diagnostic error
        error_type = type(e).__name__

        try:
            error_msg = str(e).encode(
                "ascii",
                errors="replace"
            ).decode("ascii")
        except Exception:
            error_msg = "Unable to read Gemini error"

        return (
            "GEMINI_ERROR\n"
            "TYPE=" + error_type + "\n"
            "ERROR=" + error_msg
        )
