import os
import time
import json
import threading
import requests
import ccxt

from flask import Flask
from google import genai
from pydantic import BaseModel, Field

# ============================================================
# CONFIG
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

DELTA_API_KEY = os.getenv("DELTA_API_KEY", "")
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET", "")

SYMBOL = "ARCUSD"

# ============================================================
# REAL MONEY
# ============================================================

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
    print("⚠️ WARNING: GEMINI_API_KEY missing in environment variables!")
    gemini = None
else:
    gemini = genai.Client(api_key=GEMINI_API_KEY)

MODEL = "gemini-2.5-flash"

# ============================================================
# GEMINI OUTPUT SCHEMA
# ============================================================

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

# ============================================================
# TELEGRAM
# ============================================================

def telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
    except Exception as e:
        print("Telegram Error:", e)

# ============================================================
# DELTA EXCHANGE
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

# ============================================================
# GEMINI BRAIN
# ============================================================

def ask_gemini(market_data, position):
    if not gemini:
        raise Exception("Gemini client not initialized")
    
    prompt = f"""
You are GH BOSS. You are the autonomous trading brain.
SYMBOL: {SYMBOL}
CURRENT POSITION: {json.dumps(position, indent=2)}
LIVE DATA: {json.dumps(market_data, indent=2)}

Analyze raw market data (price action, structure, momentum, volume, volatility).
Decide: BUY, SELL or NO_TRADE. Do not force a trade.
If trading, provide Entry, Stop Loss, Take Profit.
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

def validate_gemini_trade(decision):
    side = decision.decision.upper()
    if side not in ["BUY", "SELL", "NO_TRADE"]:
        return False, "Invalid decision"
    if side == "NO_TRADE":
        return False, "Gemini selected NO_TRADE"
    if decision.confidence < MIN_CONFIDENCE:
        return False, f"Confidence {decision.confidence}% too low"
    
    entry, sl, tp = float(decision.entry), float(decision.stop_loss), float(decision.take_profit)
    if entry <= 0 or sl <= 0 or tp <= 0:
        return False, "Invalid prices"
    if side == "BUY" and not (sl < entry < tp):
        return False, "Invalid BUY structure"
    if side == "SELL" and not (tp < entry < sl):
        return False, "Invalid SELL structure"
    return True, "OK"

def reset_daily_counter():
    global daily_date, daily_trades
    today = time.strftime("%Y-%m-%d")
    if today != daily_date:
        daily_date = today
        daily_trades = 0

def execution_gate(exchange, symbol, decision):
    global last_trade_time, daily_trades
    reset_daily_counter()
    if not running:
        return False, "Trading stopped"
    if daily_trades >= MAX_DAILY_TRADES:
        return False, "Daily limit reached"
    if time.time() - last_trade_time < COOLDOWN_SECONDS:
        return False, "Cooldown active"
    if get_position(exchange, symbol):
        return False, "Existing position found"
    return validate_gemini_trade(decision)

# ============================================================
# REAL DELTA ORDER WITH BRACKET (SL & TP)
# ============================================================

def execute_real_order(exchange, symbol, decision):
    global last_trade_time, daily_trades
    side = "buy" if decision.decision.upper() == "BUY" else "sell"
    close_side = "sell" if side == "buy" else "buy"

    with order_lock:
        try:
            order = exchange.create_order(symbol=symbol, type="market", side=side, amount=AMOUNT)
            order_id = order.get("id", "UNKNOWN")

            tp_order_id = "N/A"
            try:
                tp_order = exchange.create_order(
                    symbol=symbol, type="limit", side=close_side, amount=AMOUNT,
                    price=decision.take_profit, params={"reduce_only": True}
                )
                tp_order_id = tp_order.get("id", "UNKNOWN")
            except Exception as e:
                print("TP Error:", e)

            sl_order_id = "N/A"
            try:
                sl_order = exchange.create_order(
                    symbol=symbol, type="stop_market", side=close_side, amount=AMOUNT,
                    price=decision.stop_loss, params={"stop_price": decision.stop_loss, "reduce_only": True}
                )
                sl_order_id = sl_order.get("id", "UNKNOWN")
            except Exception as e:
                print("SL Error:", e)

            last_trade_time = time.time()
            daily_trades += 1

            message = (
                "🚨 GEMINI REAL BRACKET TRADE\n\n"
                f"Symbol: {symbol}\n"
                f"Side: {side.upper()}\n"
                f"Amount: {AMOUNT}\n\n"
                f"Entry ID: {order_id}\n"
                f"TP ID: {tp_order_id} @ {decision.take_profit}\n"
                f"SL ID: {sl_order_id} @ {decision.stop_loss}\n\n"
                f"Confidence: {decision.confidence}%\n\n"
                f"Reason:\n{decision.reason}"
            )
            telegram(message)
        except Exception as e:
            print("REAL ORDER FAILED:", e)
            telegram("❌ REAL ORDER FAILED\n\n" + str(e))

# ============================================================
# AUTONOMOUS ENGINE
# ============================================================

def trading_engine():
    global last_price, last_decision, last_confidence, last_reason, last_entry, last_sl, last_tp
    print("🧠 GEMINI AUTONOMOUS ENGINE STARTED")
    
    try:
        exchange = create_exchange()
        symbol = find_symbol(exchange)
        print("DELTA SYMBOL:", symbol)
    except Exception as e:
        print("DELTA CONNECTION ERROR:", e)
        telegram("❌ Delta connection failed:\n" + str(e))
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

            allowed, reason = execution_gate(exchange, symbol, decision)
            if allowed:
                execute_real_order(exchange, symbol, decision)

            time.sleep(ANALYSIS_INTERVAL)
        except Exception as e:
            print("ENGINE ERROR:", e)
            time.sleep(30)

# ============================================================
# TELEGRAM LOOP
# ============================================================

def telegram_loop():
    global running
    offset = 0
    print("TELEGRAM CONTROL STARTED")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"timeout": 20, "offset": offset}

            response = requests.get(url, params=params, timeout=25)
            data = response.json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                if "message" not in update:
                    continue

                text = update["message"].get("text", "").strip().lower()
                if text == "/start":
                    running = True
                    telegram("🟢 GEMINI REAL TRADING ON")
                elif text == "/stop":
                    running = False
                    telegram("🔴 GEMINI AUTOTRADING OFF")
                elif text == "/kill":
                    running = False
                    telegram("🛑 EMERGENCY KILL: New trades stopped.")
                elif text == "/status":
                    telegram(
                        f"📊 GH BOSS STATUS\n\nTrading: {'ON 🟢' if running else 'OFF 🔴'}\n"
                        f"Symbol: {SYMBOL}\nPrice: {last_price}\nGemini: {last_decision}\n"
                        f"Confidence: {last_confidence}%\nDaily trades: {daily_trades}"
                    )
        except Exception as e:
            print("TELEGRAM ERROR:", e)
            time.sleep(5)

# ============================================================
# FLASK HEALTH CHECK
# ============================================================

@app.route("/")
def home():
    return "GH GEMINI REAL TRADING ENGINE ONLINE"

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("GH BOSS GEMINI REAL-MONEY TRADER")
    print("=" * 60)

    # Background Threads start
    threading.Thread(target=trading_engine, daemon=True).start()
    threading.Thread(target=telegram_loop, daemon=True).start()

    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
