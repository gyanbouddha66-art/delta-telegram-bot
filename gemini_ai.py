import os

from google import genai


API_KEY = os.getenv("GEMINI_API_KEY")

_client = None


def get_client():

    global _client

    if _client is None:

        if not API_KEY:
            raise Exception(
                "GEMINI_API_KEY missing"
            )

        _client = genai.Client(
            api_key=API_KEY
        )

    return _client


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

            return "EMPTY_GEMINI_RESPONSE"

        return str(text)

    except Exception as e:

        return (
            "GEMINI_ERROR: "
            + str(e)
        )
