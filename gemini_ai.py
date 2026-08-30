import os
import requests


# ============================================================
# GH GEMINI REST API
# ============================================================

def get_gemini_key():

    key = os.getenv(
        "GEMINI_API_KEY",
        ""
    )

    return key.strip()


GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-2.5-flash:generateContent"
)


# ============================================================
# ASK GEMINI
# ============================================================

def ask_gemini(prompt):

    api_key = get_gemini_key()

    # --------------------------------------------------------
    # CHECK API KEY
    # --------------------------------------------------------

    if not api_key:

        return (
            "GEMINI ERROR\n\n"
            "GEMINI_API_KEY is missing."
        )

    # --------------------------------------------------------
    # BASIC KEY VALIDATION
    # --------------------------------------------------------

    if "\n" in api_key or "\r" in api_key:

        return (
            "GEMINI ERROR\n\n"
            "GEMINI_API_KEY contains a newline."
        )

    # --------------------------------------------------------
    # PROMPT
    # --------------------------------------------------------

    if not prompt:

        prompt = (
            "Explain professional market analysis "
            "using price action, trend, momentum, "
            "volume and volatility."
        )

    prompt = str(prompt).strip()

    # --------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------

    payload = {

        "contents": [

            {

                "parts": [

                    {
                        "text": prompt
                    }

                ]

            }

        ]

    }

    headers = {

        "Content-Type":
        "application/json",

        "x-goog-api-key":
        api_key

    }

    try:

        response = requests.post(

            GEMINI_URL,

            headers=headers,

            json=payload,

            timeout=45

        )

        print(
            "GEMINI HTTP:",
            response.status_code
        )

        # ----------------------------------------------------
        # HTTP ERROR
        # ----------------------------------------------------

        if response.status_code != 200:

            print(
                "GEMINI RESPONSE:",
                response.text[:2000]
            )

            return (
                "GEMINI API ERROR\n\n"

                "HTTP STATUS: "
                + str(response.status_code)

                + "\n\n"

                + response.text[:2000]
            )

        # ----------------------------------------------------
        # JSON
        # ----------------------------------------------------

        try:

            data = response.json()

        except Exception:

            return (
                "GEMINI ERROR\n\n"
                "Invalid JSON response."
            )

        # ----------------------------------------------------
        # CANDIDATES
        # ----------------------------------------------------

        candidates = data.get(
            "candidates",
            []
        )

        if not candidates:

            return (
                "GEMINI ERROR\n\n"
                "No candidates returned.\n\n"
                + str(data)[:2000]
            )

        # ----------------------------------------------------
        # CONTENT
        # ----------------------------------------------------

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
                "GEMINI ERROR\n\n"
                "No response parts."
            )

        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

        answer_parts = []

        for part in parts:

            text = part.get(
                "text"
            )

            if text:

                answer_parts.append(
                    str(text)
                )

        answer = "\n".join(
            answer_parts
        ).strip()

        if not answer:

            return (
                "GEMINI ERROR\n\n"
                "Empty response."
            )

        return answer

    # --------------------------------------------------------
    # REQUEST ERROR
    # --------------------------------------------------------

    except requests.exceptions.RequestException as e:

        print(
            "GEMINI CONNECTION ERROR:",
            repr(e)
        )

        return (
            "GEMINI CONNECTION ERROR\n\n"
            + str(e)
        )

    # --------------------------------------------------------
    # UNKNOWN ERROR
    # --------------------------------------------------------

    except Exception as e:

        print(
            "GEMINI ERROR:",
            repr(e)
        )

        return (
            "GEMINI ERROR\n\n"
            "TYPE: "
            + type(e).__name__
            + "\n\n"
            "MESSAGE: "
            + str(e)
        )
