import os
import time
import json
import threading
import requests
import ccxt

from flask import Flask
from google import genai


# ============================================================
# CONFIG (सभी कीज़ यहाँ सेट हैं)
# ============================================================

TELEGRAM_BOT_TOKEN = "8919168139:AAFijo1uf4BoJo1oJjqKvO9UjYj96wASpw8"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

GEMINI_API_KEY = "AQ.Ab8RN6LBu4eJ5cIdWMqexsllbvZ2Wc3aKnMlclgM-wuoOF2mFg"

DELTA_API_KEY = "nHv2Al08t6Bd8O1KSGBXCHP2ZbpmP3"
DELTA_API_SECRET = "tCTPHxKcZxZ2wvk9oMyFrgDRkTK37ryjRNDM6Lhkt6neE2MfIkv9lL5vW8se"

SYMBOL = "ARCUSD"
ANALYSIS_INTERVAL = 60


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# GEMINI — EXTERNAL API
# ============================================================

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

gemini = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"


# ============================================================
# GLOBAL STATE
# ============================================================

running = True
last_price = 0.0
last_analysis = "Waiting..."
last_gemini_status = "UNKNOWN"
last_update_time = 0


# ============================================================
# TELEGRAM SEND
# ============================================================

def telegram_send(text, chat_id=None):
    try:
        target = chat_id if chat_id else TELEGRAM_CHAT_ID
        if not TELEGRAM_BOT_TOKEN or not target:
            return False

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": target, "text": text}, timeout=15)
        return response.ok
    except Exception as e:
        print("Telegram error:", e)
        return False


# ============================================================
# GEMINI CONNECTION TEST
# ============================================================

def test_gemini():
    global last_gemini_status
    try:
        response = gemini.models.generate_content(
            model=MODEL,
            contents="Reply with exactly: GEMINI_CONNECTED"
        )
        text = response.text if response else ""
        if "GEMINI_CONNECTED" in text:
            last_gemini_status = "CONNECTED"
            return True
        last_gemini_status = "ERROR"
        return False
    except Exception as e:
        last_gemini_status = "ERROR"
        print("Gemini connection error:", e)
        return False


# ============================================================
# DELTA
# ============================================================

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
    for symbol in exchange.markets:
        if SYMBOL.upper() in symbol.upper():
            return symbol
    raise RuntimeError(f"Delta market not found: {SYMBOL}")


# ============================================================
# LIVE MARKET DATA
# ============================================================

def get_market_data(exchange, symbol):
    data = {}
    for timeframe in ["1m", "5m", "15m"]:
        candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        data[timeframe] = [
            {
                "time": c[0], "open": c[1], "high": c[2], 
                "low": c[3], "close": c[4], "volume": c[5]
            }
            for c in candles
        ]

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


# ============================================================
# SEND MARKET DATA TO GEMINI
# ============================================================

def gemini_market_analysis(market_data, question=""):
    prompt = f"""
You are GH BOSS. You are an external Gemini AI market analysis engine.
Analyze the RAW market data provided.
SYMBOL: {SYMBOL}
USER QUESTION: {question}
LIVE MARKET DATA: {json.dumps(market_data, indent=2)}

Give the answer in Hindi.
Format:
DECISION: BUY / SELL / NO_TRADE
CONFIDENCE: 0-100%
CURRENT PRICE:
ENTRY:
STOP LOSS:
TAKE PROFIT:
ANALYSIS:
INVALIDATION:
RISK:
"""
    response = gemini.models.generate_content(model=MODEL, contents=prompt)
    if not response:
        raise RuntimeError("Empty Gemini response")
    return response.text.strip()


# ============================================================
# GET FRESH DATA + GEMINI
# ============================================================

def run_gemini_analysis(question="", chat_id=None):
    global last_price, last_analysis, last_update_time
    try:
        telegram_send("🧠 Gemini live analysis शुरू...", chat_id)
        exchange = create_exchange()
        symbol = find_symbol(exchange)
        market_data = get_market_data(exchange, symbol)
        last_price = market_data["ticker"]["last"]
        
        analysis = gemini_market_analysis(market_data, question)
        last_analysis = analysis
        last_update_time = time.time()

        telegram_send(
            f"🧠 GEMINI LIVE ANALYSIS\n\nSymbol: {symbol}\nPrice: {last_price}\n\n{analysis}",
            chat_id
        )
    except Exception as e:
        print("Analysis error:", e)
        telegram_send("❌ ANALYSIS ERROR\n\n" + str(e), chat_id)


# ============================================================
# TELEGRAM POLLING
# ============================================================

def telegram_polling():
    print("📡 TELEGRAM POLLING STARTED")
    offset = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset

            response = requests.get(url, params=params, timeout=40)
            result = response.json()

            if not result.get("ok"):
                time.sleep(5)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1
                process_update(update)
        except Exception as e:
            print("Telegram polling error:", e)
            time.sleep(5)


# ============================================================
# TELEGRAM COMMANDS
# ============================================================

def process_update(update):
    global running
    try:
        message = update.get("message")
        if not message:
            return

        chat_id = str(message["chat"]["id"])
        text = message.get("text", "").strip()
        if not text:
            return

        if TELEGRAM_CHAT_ID and chat_id != str(TELEGRAM_CHAT_ID):
            return

        command = text.lower()

        if command == "/start":
            running = True
            telegram_send("🟢 GH BOSS ONLINE\nDelta, Gemini & Telegram connected successfully.", chat_id)
        elif command == "/stop":
            running = False
            telegram_send("🔴 ENGINE STOPPED", chat_id)
        elif command == "/status":
            telegram_send(f"📊 STATUS\nEngine: {'ON 🟢' if running else 'OFF 🔴'}\nPrice: {last_price}\n{last_analysis}", chat_id)
        elif command == "/analysis":
            threading.Thread(target=run_gemini_analysis, args=("Analyze market.", chat_id), daemon=True).start()
        elif command == "/help":
            telegram_send("🤖 Commands: /start, /stop, /status, /analysis", chat_id)
        else:
            threading.Thread(target=run_gemini_analysis, args=(text, chat_id), daemon=True).start()
    except Exception as e:
        print("Update processing error:", e)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/")
def home():
    return f"GH BOSS ONLINE | Gemini: {last_gemini_status}"


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    test_gemini()
    threading.Thread(target=telegram_polling, daemon=True).start()
    
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
