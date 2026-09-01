# ============================================================
# GROQ AI MODULE (`groq_ai.py`)
# ============================================================

import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

def ask_groq_ai(prompt):
    """यह फंक्शन सीधे Groq AI (Llama 3) को कॉल करता है और SMC तथा डेल्टा ट्रेडिंग के आधार पर जवाब देता है"""
    if not GROQ_API_KEY:
        return "⚠️ Groq API Key Render environment में सेट नहीं है। कृपया Environment Variables में 'GROQ_API_KEY' जोड़ें।"
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {
                "role": "system",
                "content": "You are GH BOSS AI, an elite crypto trading assistant specialized in Smart Money Concepts (SMC), order flow, and Delta Exchange ARCUSD trading. Give direct, precise, practical, and expert trading insights in Hinglish/Hindi or English as requested."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            return answer
        else:
            return f"❌ Groq API Error ({response.status_code}): {response.text}"
    except Exception as e:
        return f"❌ Groq Connection Exception: {str(e)}"
