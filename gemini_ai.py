
import os
from google import genai


def ask_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return "Gemini API key configured nahi hai."

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text

    except Exception as e:
        return f"Gemini Error: {e}"
