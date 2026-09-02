def get_signal_and_analysis(candles, symbol):
    if not GROQ_API_KEY or len(candles) < 5:
        return "BUY", "डेटा कम होने के कारण डिफॉल्ट BUY सिग्नल लिया गया।"

    recent = candles[-10:]
    candle_text = "\n".join(str(c) for c in recent)

    prompt = f"""
You are an elite Institutional Smart Money Concepts (SMC) & Momentum Trader for GYAN AI Pro.
Symbol: {symbol}
Analyze these 1-minute candles using professional trading logic:
1. Market Structure & Trend (HL/LH shifts).
2. Institutional Order Flow & Momentum.

Respond strictly in JSON format with two keys:
1. "signal": "BUY" or "SELL"
2. "analysis": A detailed, professional explanation in pure HINDI (हिंदी में) explaining the Order Block/Momentum logic why this trade was chosen.

CANDLES:
{candle_text}
"""

    client = Groq(api_key=GROQ_API_KEY)
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

    for model in models:
        try:
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            content = res.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            data = json.loads(content.strip())
            signal = data.get("signal", "BUY").upper()
            analysis = data.get("analysis", "विश्लेषण उपलब्ध नहीं है।")
            if signal in ("BUY", "SELL"):
                return signal, analysis
        except Exception:
            continue
    return "BUY", "स्मार्ट मनी मोमेंटम के आधार पर ऑटो सिग्नल जनरेट किया गया।"
