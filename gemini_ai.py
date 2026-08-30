import os
import requests


# ============================================================
# GH GEMINI DIRECT REST API
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-2.5-flash:generateContent"
)


# ============================================================
# ASK GEMINI
# ============================================================

def ask_gemini(prompt):

    if not API_KEY:

        return (
            "GEMINI ERROR\n"
            "GEMINI_API_KEY is missing"
        )

    try:

        # ASCII-only test prompt
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

        response = requests.post(
            GEMINI_URL,
            params={
                "key": API_KEY.strip()
            },
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
                + response.text[:1500]
            )

        # ----------------------------------------------------
        # JSON
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

        text = (
            candidates[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        if not text:

            return (
                "GEMINI ERROR\n"
                "Empty response"
            )

        return text

    except requests.exceptions.RequestException as e:

        return (
            "GEMINI CONNECTION ERROR\n"
            + str(e)
        )

    except Exception as e:

        # Keep diagnostic message simple
        try:
            error_text = str(e)
        except Exception:
            error_text = "Unknown error"

        return (
            "GEMINI ERROR\n"
            "TYPE: "
            + type(e).__name__
            + "\n"
            "MESSAGE: "
            + error_text
        )
