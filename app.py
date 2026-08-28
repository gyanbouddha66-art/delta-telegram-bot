import os
import time
import asyncio
import threading
import requests
from flask import Flask, request
import ccxt
import edge_tts
import google.generativeai as genai

# --- 1. CONFIGURATIONS ---
TELEGRAM_BOT_TOKEN = "8919168139:AAFijo1uf4BoJo1oJjqKvO9UjYj96wASpw8"  
TELEGRAM_CHAT_ID = "965643127"              

GEMINI_API_KEY = "AQ.Ab8RN6LBu4eJ5cIdWMqexsllbvZ2Wc3aKnMlclgM-wuoOF2mFg"
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-pro')

DELTA_API_KEY = "nHv2Al08t6Bd8O1KSGBXCHP2ZbpmP3"
DELTA_API_SECRET = "tCTPHxKcZxZ2wvk9oMyFrgDRkTK37ryjRNDM6Lhkt6neE2MfIkv9lL5vW8se"

SYMBOL = 'ARCUSD'         
AMOUNT = 1.0              
CHECK_INTERVAL = 60       

TP_PERCENT = 0.015  # 1.5% टेक प्रॉफिट
SL_PERCENT = 0.01   # 1.0% स्टॉप लॉस

bot_running = True  
last_analysis_log = "Gemini Powered BOSS Active..."
last_price_val = 0.06767  

app = Flask(__name__)

def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

# **सुधरा हुआ Gemini AI चैट इंजन**
def get_gemini_brain_reply(user_text, current_price, is_running):
    try:
        status_str = "चालू है (Active)" if is_running else "बंद है (Stopped)"
        prompt = f"""
        तुम एक बहुत ही स्मार्ट, शार्प और प्रोफेशनल क्रिप्टो/ट्रेडिंग पार्टनर हो (नाम: BOSS)। 
        तुम हमेशा हिंदी भाषा में, दोस्ताना और तगड़े अंदाज़ में बात करते हो ("भाई साहब" या "भाई" कहकर संबोधित करते हो)।
        
        वर्तमान स्थिति:
        - कॉइन: {SYMBOL}
        - लाइव भाव: ${current_price}
        - ऑटो-ट्रेडिंग स्टेटस: {status_str}
        
        यूज़र का सवाल है: "{user_text}"
        
        इस सवाल का एकदम सटीक, स्मार्ट और नेचुरल जवाब दो।
        """
        response = gemini_model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
        else:
            return f"भाई, अभी {SYMBOL} का भाव ${current_price} चल रहा है, सब कंट्रोल में है।"
    except Exception as e:
        print(f"Gemini AI Error: {e}")
        # अगर जेमिनी एरर दे तो सीधा सादा स्मार्ट जवाब दें ताकि बोट अटके नहीं
        return f"भाई साहब, अभी {SYMBOL} का लाइव भाव ${current_price} है। बताओ कौन सा ट्रेड मारना है?"

async def generate_and_send_voice(text_message):
    try:
        audio_path = "boss_voice.mp3"
        clean_text = text_message.replace("*", "").replace("#", "").replace("$", " डॉलर ")
        communicate = edge_tts.Communicate(clean_text, "hi-IN-SwaraNeural")
        await communicate.save(audio_path)
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
        with open(audio_path, 'rb') as audio_file:
            files = {'audio': audio_file}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': "🗣️ *BOSS AI Voice Update*"}
            requests.post(url, data=data, files=files)
            
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception as e:
        print(f"Voice Error: {e}")

def send_voice_sync(text):
    asyncio.run(generate_and_send_voice(text))

# **मास्टर ट्रेड फंक्शन**
def execute_trade_with_tpsl(side, entry_price, mode="Manual"):
    try:
        exchange = ccxt.delta({
            'apiKey': DELTA_API_KEY,
            'secret': DELTA_API_SECRET,
            'enableRateLimit': True,
        })
        exchange.load_markets()
        
        market_symbol = SYMBOL
        if market_symbol not in exchange.markets:
            for s in exchange.markets:
                if 'ARC' in s and 'USD' in s:
                    market_symbol = s
                    break

        order = exchange.create_order(symbol=market_symbol, type='market', side=side, amount=AMOUNT)
        print(f"✅ [{mode}] Market {side.upper()} Order Executed on {market_symbol} at {entry_price}")
        
        if side == 'buy':
            tp_price = entry_price * (1 + TP_PERCENT)
            sl_price = entry_price * (1 - SL_PERCENT)
        else:
            tp_price = entry_price * (1 - TP_PERCENT)
            sl_price = entry_price * (1 + SL_PERCENT)
            
        alert_msg = (
            f"🚀 *BOSS AI [{mode}] {side.upper()} Executed!*\n"
            f"- Symbol: {market_symbol}\n"
            f"- Entry: ${entry_price}\n"
            f"- Target (TP): ${round(tp_price, 4)}\n"
            f"- Stop Loss (SL): ${round(sl_price, 4)}"
        )
        send_telegram_message(alert_msg)
        threading.Thread(target=send_voice_sync, args=(f"भाई, {mode} मोड में {side} ट्रेड ले लिया है।",)).start()
        
    except Exception as e:
        print(f"❌ [{mode}] Trade Error: {e}")
        send_telegram_message(f"❌ *Trade Error ({mode}):* {e}")

@app.route('/')
def home():
    return "⚡ Gemini AI Powered BOSS Trading Bot is Live!"

# --- 2. TELEGRAM WEBHOOK ---
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    global bot_running, last_price_val
    update = request.get_json()
    
    if update and "message" in update:
        msg = update["message"]
        text = msg.get("text", "").strip()
        text_lower = text.lower()
        
        if text_lower == "/start" or text_lower == "start":
            bot_running = True
            reply = "🟢 *BOSS Gemini AI Activated!* अब दिमाग पूरी तरह चालू है, बोलिए भाई साहब!"
            send_telegram_message(reply)
            threading.Thread(target=send_voice_sync, args=("बोट का जेमिनी ए आई दिमाग चालू हो गया है।",)).start()
            
        elif text_lower == "/stop" or text_lower == "stop":
            bot_running = False
            reply = "🔴 *BOSS Auto-Trading Stopped!* ऑटो-ट्रेडिंग रोक दी गई है।"
            send_telegram_message(reply)
            threading.Thread(target=send_voice_sync, args=("ऑटो ट्रेडिंग रोक दी गई है।",)).start()
            
        elif text_lower == "/status" or text_lower == "status":
            status_str = "Running 🟢" if bot_running else "Stopped 🔴"
            reply = f"📊 *BOSS AI Status:*\n- Auto-Trading: {status_str}\n- Price: ${last_price_val}\n- Symbol: {SYMBOL}"
            send_telegram_message(reply)
            threading.Thread(target=send_voice_sync, args=(f"अभी भाव {last_price_val} डॉलर है।",)).start()
            
        elif text_lower == "/buy" or text_lower == "buy" or text_lower == "long":
            send_telegram_message("⚡ *Manual BUY Command Received!*")
            threading.Thread(target=execute_trade_with_tpsl, args=('buy', last_price_val, "Manual")).start()
            
        elif text_lower == "/sell" or text_lower == "sell" or text_lower == "short":
            send_telegram_message("⚡ *Manual SELL Command Received!*")
            threading.Thread(target=execute_trade_with_tpsl, args=('sell', last_price_val, "Manual")).start()
            
        elif text:
            reply = get_gemini_brain_reply(text, last_price_val, bot_running)
            send_telegram_message(f"🤖 *BOSS AI:* {reply}")
            threading.Thread(target=send_voice_sync, args=(reply,)).start()
                
    return "OK", 200

# --- 3. BACKGROUND TRADING ENGINE ---
def boss_autonomous_trading_loop():
    global last_analysis_log, last_price_val, bot_running
    print("🚀 Gemini Powered BOSS Engine Started...")
    
    try:
        exchange = ccxt.delta({
            'apiKey': DELTA_API_KEY,
            'secret': DELTA_API_SECRET,
            'enableRateLimit': True,
        })
        exchange.load_markets()
    except Exception as e:
        print(f"❌ Exchange Init Error: {e}")
        exchange = None

    while True:
        if bot_running and exchange:
            try:
                market_symbol = SYMBOL
                if market_symbol not in exchange.markets:
                    for s in exchange.markets:
                        if 'ARC' in s and 'USD' in s:
                            market_symbol = s
                            break

                ticker = exchange.fetch_ticker(market_symbol)
                if ticker and 'last' in ticker and ticker['last']:
                    current_price = ticker['last']
                    last_price_val = current_price
                    
                    ohlcv = exchange.fetch_ohlcv(market_symbol, timeframe='1h', limit=5)
                    if len(ohlcv) >= 3:
                        c1 = ohlcv[-3][4]
                        c2 = ohlcv[-2][4]
                        c3 = ohlcv[-1][4]
                        
                        if c3 > c2 and c2 > c1 * 1.001:
                            last_analysis_log = f"Auto Setup matched at ${current_price}"
                            execute_trade_with_tpsl('buy', current_price, "Auto")
                            time.sleep(3600) 
                            
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
