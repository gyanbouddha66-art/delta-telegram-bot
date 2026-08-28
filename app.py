import os
import time
import asyncio
import threading
import requests
from flask import Flask, request
import ccxt
import edge_tts

# --- 1. CONFIGURATIONS ---
TELEGRAM_BOT_TOKEN = "8919168139:AAFijo1uf4BoJo1oJjqKvO9UjYj96wASpw8"  
TELEGRAM_CHAT_ID = "965643127"              

# आपकी असली Gemini API Key यहाँ सेट कर दी गई है
GEMINI_API_KEY = "AQ.Ab8RN6LBu4eJ5cldWMqexslIbvZ2Wc3aKnMlclgM-wuoOF2mFg"
DELTA_API_KEY = "nHv2Al08t6Bd8O1KSGBXCHP2ZbpmP3"
DELTA_API_SECRET = "tCTPHxKcZxZ2wvk9oMyFrgDRkTK37ryjRNDM6Lhkt6neE2MfIkv9lL5vW8se"

SYMBOL = 'ARCUSD'         
AMOUNT = 1.0              
CHECK_INTERVAL = 60       

bot_running = True  
last_analysis_log = "Initializing BOSS AI..."
last_price_val = 0.0

app = Flask(__name__)

def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

# **सीधे गूगल API को कॉल करने का सुरक्षित तरीका**
def ask_gemini(prompt_text):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [{"text": prompt_text}]
            }]
        }
        response = requests.post(url, headers=headers, json=data)
        res_json = response.json()
        
        if "candidates" in res_json:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return f"API Response Error: {res_json.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Gemini Request Error: {e}"

# **Edge-TTS के जरिए प्रीमियम आवाज़ भेजने का फंक्शन**
async def generate_and_send_voice(text_message):
    try:
        audio_path = "boss_voice.mp3"
        communicate = edge_tts.Communicate(text_message, "hi-IN-SwaraNeural")
        await communicate.save(audio_path)
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
        with open(audio_path, 'rb') as audio_file:
            files = {'audio': audio_file}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': "🗣️ *BOSS Voice Update*"}
            requests.post(url, data=data, files=files)
            
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception as e:
        print(f"Voice Error: {e}")

def send_voice_sync(text):
    asyncio.run(generate_and_send_voice(text))

@app.route('/')
def home():
    return "⚡ BOSS Autonomous AI Trading with Edge-TTS & Telegram is Live!"

# --- 2. TELEGRAM WEBHOOK ---
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    global bot_running
    update = request.get_json()
    
    if update and "message" in update:
        text = update["message"].get("text", "").strip().lower()
        
        if text == "/start" or text == "start":
            bot_running = True
            send_telegram_message("🟢 BOSS AI फिर से चालू कर दिया गया है!")
            threading.Thread(target=send_voice_sync, args=("बोट चालू हो गया है, अब मैं मार्केट स्कैन कर रहा हूँ।",)).start()
            
        elif text == "/stop" or text == "stop":
            bot_running = False
            send_telegram_message("🔴 BOSS AI को रोक दिया गया है।")
            threading.Thread(target=send_voice_sync, args=("बोट को रोक दिया गया है।",)).start()
            
        elif text == "/status" or text == "status":
            status_text = f"📊 *BOSS Status:*\n- State: {'Running 🟢' if bot_running else 'Stopped 🔴'}\n- Price: ${last_price_val}\n- Analysis: {last_analysis_log}"
            send_telegram_message(status_text)
            threading.Thread(target=send_voice_sync, args=(f"अभी कॉइन का भाव है {last_price_val} डॉलर और सिस्टम चालू है।",)).start()
        else:
            try:
                full_prompt = f"You are BOSS, an elite crypto trading AI. Reply shortly in Hindi/Hinglish to: '{text}'"
                reply = ask_gemini(full_prompt)
                
                send_telegram_message(f"🤖 *BOSS:* {reply}")
                threading.Thread(target=send_voice_sync, args=(reply,)).start()
            except Exception as e:
                send_telegram_message(f"Error: {e}")
                
    return "OK", 200

# --- 3. BACKGROUND TRADING ENGINE ---
def boss_autonomous_trading_loop():
    global last_analysis_log, last_price_val, bot_running
    print("🚀 BOSS Background Engine Started...")
    
    try:
        exchange = ccxt.delta({
            'apiKey': DELTA_API_KEY,
            'secret': DELTA_API_SECRET,
            'enableRateLimit': True,
        })
    except Exception as e:
        print(f"❌ Exchange Init Error: {e}")
        exchange = None

    while True:
        if bot_running and exchange:
            try:
                ticker = exchange.fetch_ticker(SYMBOL)
                current_price = ticker['last']
                last_price_val = current_price
                
                ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe='1h', limit=20)
                
                prompt = (
                    f"You are BOSS, an elite autonomous crypto trading AI. Current market data for {SYMBOL}: "
                    f"Current Price is {current_price}. Recent candles (OHLCV): {ohlcv[-5:]}. "
                    "Analyze the market completely based on Smart Money Concepts. "
                    "Output a brief analysis in Hinglish, and if a trade is necessary, end with: "
                    "[ACTION: BUY] or [ACTION: SELL]. If safe, output [ACTION: HOLD]."
                )

                decision_text = ask_gemini(prompt)
                last_analysis_log = decision_text

                if "[ACTION: BUY]" in decision_text:
                    exchange.create_order(symbol=SYMBOL, type='market', side='buy', amount=AMOUNT)
                    alert_txt = f"बधाई हो भाई! BOSS ने {current_price} डॉलर पर बाय ट्रेड ले लिया है।"
                    send_telegram_message(f"✅ *BOSS BUY Trade Executed!*\n- Price: {current_price}\n- {decision_text}")
                    threading.Thread(target=send_voice_sync, args=(alert_txt,)).start()
                    
                elif "[ACTION: SELL]" in decision_text:
                    exchange.create_order(symbol=SYMBOL, type='market', side='sell', amount=AMOUNT)
                    alert_txt = f"सावधान! BOSS ने {current_price} डॉलर पर सेल ट्रेड ले लिया है।"
                    send_telegram_message(f"🚨 *BOSS SELL Trade Executed!*\n- Price: {current_price}\n- {decision_text}")
                    threading.Thread(target=send_voice_sync, args=(alert_txt,)).start()
                
            except Exception as e:
                print(f"❌ Loop Error: {e}")
                
        time.sleep(CHECK_INTERVAL)

def start_background_thread():
    t = threading.Thread(target=boss_autonomous_trading_loop, daemon=True)
    t.start()

start_background_thread()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
