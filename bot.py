import os
import time
import json
import threading
import requests
import ccxt

from flask import Flask, request
from google import genai
from pydantic import BaseModel, Field
from gtts import gTTS

# ============================================================
# CONFIG
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

DELTA_API_KEY = os.getenv("DELTA_API_KEY", "")
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "")

SYMBOL = "ARCUSD"

REAL_TRADING = True
AMOUNT = 1
ANALYSIS_INTERVAL = 60
COOLDOWN_SECONDS = 300
MAX_DAILY_TRADES = 10
MIN_CONFIDENCE = 70

# ============================================================
# GEMINI
# ============================================================

if not GEMINI_API_KEY:
    gemini = None
else:
    gemini = genai.Client(api_key=GEMINI_API_KEY)

MODEL = "gemini-2.5-flash"

class TradeDecision(BaseModel):
    decision: str = Field(description="BUY, SELL or NO_TRADE")
    confidence: int = Field(description="0 to 100")
    entry: float = Field(description="Entry price")
    stop_loss: float = Field(description="Stop loss price")
    take_profit: float = Field(description="Take profit price")
    reason: str = Field(description="Detailed market reasoning")
    invalidation: str = Field(description="Trade invalidation condition")

# ============================================================
# GLOBAL STATE
# ============================================================

app = Flask(__name__)

running = True
last_price = 0.0
last_decision = "NO_TRADE"
last_confidence = 0
last_reason = "Waiting..."
last_entry = 0.0
last_sl = 0.0
last_tp = 0.0
last_trade_time = 0
daily_trades = 0
daily_date = time.strftime("%Y-%m-%d")
order_lock = threading.Lock()

def telegram(text, chat_id=None):
    target_chat = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not target_chat:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": target_chat, "text": text}, timeout=15)
    except Exception as e:
        print("Telegram Error:", e)

def telegram_voice(text, chat_id=None):
    target_chat = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not target_chat:
        return
    try:
        # Convert text to speech (Hindi/Hinglish)
        tts = gTTS(text=text, lang='hi', slow=False)
        voice_path = "response.ogg"
        tts.save(voice_path)

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
        with open(voice_path, "rb") as voice_file:
            requests.post(url, data={"chat_id": target_chat}, files={"voice": voice_file}, timeout=30)
        
        if os.path.exists(voice_path):
            os.remove(voice_path)
    except Exception as e:
        print("Voice Error:", e)
        # Fallback to text if voice fails
        telegram(text, chat_id)

def create_exchange():
    exchange = ccxt.delta({
        "apiKey": DELTA_API_KEY,
        "secret": DELTA_API_SECRET,
        "enableRateLimit": True
    })
    exchange.load_markets()
    return exchange

def find_symbol(exchange):
    if SYMBOL in exchange.markets:
        return SYMBOL
    for s in exchange.markets:
        if SYMBOL.upper() in s.upper():
            return s
    raise Exception(f"Delta market not found: {SYMBOL}")

def get_market_data(exchange, symbol):
    data = {}
    for tf in ["1m", "5m", "15m"]:
        candles = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
        data[tf] = [{"time": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in candles]
    ticker = exchange.fetch_ticker(symbol)
    data["ticker"] = {
        "last": ticker.get("last"),
        "bid": ticker.get("bid"),
        "ask": ticker.get("ask"),
        "high": ticker.get("high"),
        "low": ticker.get("low"),
        "volume": ticker.get("baseVolume")
    }
    return data

def get_position(exchange, symbol):
    try:
        positions = exchange.fetch_positions([symbol])
        for p in positions:
            contracts = p.get("contracts")
            if contracts is not None and abs(float(contracts)) > 0:
                return p
    except Exception as e:
        print("Position check error:", e)
    return None

def ask_gemini(market_data, position):
    if not gemini:
        raise Exception("Gemini client not initialized")
    
    prompt = f"""
You are GH BOSS. You are the autonomous trading brain.
SYMBOL: {SYMBOL}
CURRENT POSITION: {json.dumps(position, indent=2)}
LIVE DATA: {json.dumps(market_data, indent=2)}

Analyze raw market data. Decide: BUY, SELL or NO_TRADE.
Return ONLY JSON matching the schema.
"""
    response = gemini.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": TradeDecision
        }
    )
    return TradeDecision.model_validate_json(response.text)

def chat_with_gemini(user_message):
    if not gemini:
        return "Gemini client not initialized."
    try:
        prompt = f"""
You are GH BOSS, an intelligent, friendly, and smart AI companion and trading partner to your user (address him respectfully like 'भाई साहब'). 
The user is talking to you on Telegram. Respond concisely (suitable for a voice note) in a smart, warm, helpful, and natural conversational tone (in Hinglish/Hindi). Keep it relatively brief so the audio note isn't too long.

User message: {user_message}
"""
        response = gemini.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        return response.text
    except Exception as e:
        print("Chat Error:", e)
        return "भाई साहब, अभी दिमाग थोड़ा बिजी है, बाद में बात करते हैं!"

def trading_engine():
    global last_price, last_decision, last_confidence, last_reason, last_entry, last_sl, last_tp
    print("🧠 GEMINI AUTONOMOUS ENGINE STARTED")
    try:
        exchange = create_exchange()
        symbol = find_symbol(exchange)
    except Exception as e:
        print("DELTA ERROR:", e)
        return

    while True:
        try:
            if not running:
                time.sleep(ANALYSIS_INTERVAL)
                continue
            market_data = get_market_data(exchange, symbol)
            last_price = market_data["ticker"]["last"]
            position = get_position(exchange, symbol)
            decision = ask_gemini(market_data, position)
            last_decision = decision.decision
            last_confidence = decision.confidence
            last_reason = decision.reason
            last_entry = decision.entry
            last_sl = decision.stop_loss
            last_tp = decision.take_profit
            
            time.sleep(ANALYSIS_INTERVAL)
        except Exception as e:
            print("ENGINE ERROR:", e)
            time.sleep(30)

# ============================================================
# FLASK WEBHOOK ROUTES
# ============================================================

@app.route("/")
def home():
    return "GH GEMINI WEB SERVICE ONLINE"

@app.route("/webhook", methods=["POST"])
def webhook():
    global running
    try:
        data = request.get_json()
        if "message" in data:
            msg = data["message"]
            text = msg.get("text", "").strip()
            text_lower = text.lower()
            chat_id = msg["chat"]["id"]

            if TELEGRAM_CHAT_ID and str(chat_id) != str(TELEGRAM_CHAT_ID):
                print("Unauthorized Telegram chat:", chat_id)
                return "OK", 200

            # Commands Handling
            if text_lower in ["/start", "start"]:
                running = True
                telegram("🟢 GEMINI REAL TRADING ON", chat_id)

            elif text_lower in ["/stop", "stop"]:
                running = False
                telegram("🔴 GEMINI AUTOTRADING OFF", chat_id)

            elif text_lower in ["/status", "status"]:
                status_text = (
                    "📊 GH BOSS STATUS\n\n"
                    f"Trading: {'ON 🟢' if running else 'OFF 🔴'}\n"
                    f"Symbol: {SYMBOL}\n"
                    f"Price: {last_price}\n"
                    f"Gemini: {last_decision}\n"
                    f"Confidence: {last_confidence}%\n\n"
                    f"Entry: {last_entry}\n"
                    f"SL: {last_sl}\n"
                    f"TP: {last_tp}\n\n"
                    f"Daily trades: {daily_trades}"
                )
                telegram(status_text, chat_id)

            elif text_lower in ["/analysis", "analysis"]:
                analysis_text = (
                    "🧠 GEMINI ANALYSIS\n\n"
                    f"Decision: {last_decision}\n\n"
                    f"Confidence: {last_confidence}%\n\n"
                    f"Price: {last_price}\n\n"
                    f"Reason:\n{last_reason}"
                )
                telegram(analysis_text, chat_id)

            elif text_lower in ["/kill", "kill"]:
                running = False
                telegram("🛑 EMERGENCY KILL\nNew trades stopped.", chat_id)

            elif text_lower in ["/help", "help"]:
                help_text = (
                    "🤖 GH BOSS COMMANDS & CHAT\n\n"
                    "/start - Start trading\n"
                    "/stop - Stop new trades\n"
                    "/status - Current status\n"
                    "/analysis - Gemini analysis\n"
                    "/kill - Emergency stop\n"
                    "/help - Commands\n\n"
                    "💡 Chat with me and I will reply in Voice Notes!"
                )
                telegram(help_text, chat_id)

            else:
                # Generate Smart Reply and send as a Voice Note!
                reply_text = chat_with_gemini(text)
                telegram_voice(reply_text, chat_id)

        return "OK", 200
    except Exception as e:
        print("Webhook Error:", e)
        return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=trading_engine, daemon=True).start()
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
