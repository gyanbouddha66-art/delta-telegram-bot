import os
import requests


# ============================================================
# GH GEMINI DIRECT REST API
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-2.5-flash:generateContent"
)


# ============================================================
# ASK GEMINI
# ============================================================

def ask_gemini(prompt):

    # --------------------------------------------------------
    # CHECK KEY
    # --------------------------------------------------------

    if not API_KEY:

        return (
            "GEMINI ERROR\n"
            "GEMINI_API_KEY is missing"
        )

    try:

        # ----------------------------------------------------
        # ASCII ONLY TEST PROMPT
        # ----------------------------------------------------

        safe_prompt = (
            "Explain how a professional trading "
            "system evaluates market direction. "
            "Use simple English. "
            "Do not recommend a live trade."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": safe_prompt
                        }
                    ]
                }
            ]
        }

        # ----------------------------------------------------
        # API KEY IN HEADER
        # ----------------------------------------------------

        headers = {
            "x-goog-api-key": API_KEY,
            "Content-Type": "application/json"
        }

        # ----------------------------------------------------
        # GEMINI REQUEST
        # ----------------------------------------------------

        response = requests.post(
            GEMINI_URL,
            headers=headers,
            json=payload,
            timeout=45
        )

        # ----------------------------------------------------
        # HTTP ERROR
        # ----------------------------------------------------

        if response.status_code != 200:

            return (
                "GEMINI API ERROR\n"
                "HTTP STATUS: "
                + str(response.status_code)
                + "\n\n"
                + response.text[:2000]
            )

        # ----------------------------------------------------
        # JSON RESPONSE
        # ----------------------------------------------------

        data = response.json()

        candidates = data.get(
            "candidates",
            []
        )

        if not candidates:

            return (
                "GEMINI ERROR\n"
                "No candidates returned.\n\n"
                + str(data)[:1500]
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

            return (
                "GEMINI ERROR\n"
                "No response parts returned."
            )

        text = parts[0].get(
            "text",
            ""
        )

        if not text:

            return (
                "GEMINI ERROR\n"
                "Empty Gemini response."
            )

        return str(text)

    # --------------------------------------------------------
    # CONNECTION ERROR
    # --------------------------------------------------------

    except requests.exceptions.RequestException as e:

        return (
            "GEMINI CONNECTION ERROR\n"
            + str(e)
        )

    # --------------------------------------------------------
    # OTHER ERROR
    # --------------------------------------------------------

    except Exception as e:

        return (
            "GEMINI ERROR\n"
            "TYPE: "
            + type(e).__name__
            + "\n"
            "MESSAGE: "
            + str(e)
        )
