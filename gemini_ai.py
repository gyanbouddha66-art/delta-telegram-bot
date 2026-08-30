import os
import requests


# ============================================================
# GH GEMINI 3.6 FLASH — INTERACTIONS API
# ============================================================

API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/interactions"
)


# ============================================================
# ASK GEMINI
# ============================================================

def ask_gemini(prompt):

    if not API_KEY:
        return (
            "GEMINI ERROR\n\n"
            "GEMINI_API_KEY is missing."
        )

    if "\n" in API_KEY or "\r" in API_KEY:
        return (
            "GEMINI ERROR\n\n"
            "GEMINI_API_KEY contains newline."
        )

    if not prompt:
        prompt = "Explain the current question clearly."

    payload = {
        "model": "gemini-3.6-flash",
        "input": str(prompt)
    }

    headers = {
        "x-goog-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    try:

        response = requests.post(
            GEMINI_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        print(
            "GEMINI HTTP:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "GEMINI RESPONSE:",
                response.text[:3000]
            )

            return (
                "GEMINI API ERROR\n\n"
                "HTTP STATUS: "
                + str(response.status_code)
                + "\n\n"
                + response.text[:3000]
            )

        data = response.json()

        # ----------------------------------------------------
        # INTERACTIONS API OUTPUT
        # ----------------------------------------------------

        steps = data.get(
            "steps",
            []
        )

        texts = []

        for step in steps:

            if step.get("type") != "model_output":
                continue

            content = step.get(
                "content",
                []
            )

            for item in content:

                if item.get("type") == "text":

                    text = item.get(
                        "text",
                        ""
                    )

                    if text:
                        texts.append(
                            text
                        )

        answer = "\n".join(
            texts
        ).strip()

        if answer:
            return answer

        return (
            "GEMINI ERROR\n\n"
            "No text output returned.\n\n"
            + str(data)[:3000]
        )

    except requests.exceptions.RequestException as e:

        print(
            "GEMINI CONNECTION ERROR:",
            repr(e)
        )

        return (
            "GEMINI CONNECTION ERROR\n\n"
            + str(e)
        )

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
