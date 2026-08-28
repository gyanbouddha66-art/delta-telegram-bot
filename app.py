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

DELTA_API_KEY = "nHv2Al08t6Bd8O1KSGBXCHP2ZbpmP3"
DELTA_API_SECRET = "tCTPHxKcZxZ2wvk9oMyFrgDRkTK37ryjRNDM6Lhkt6neE2MfIkv9lL5vW8se"

SYMBOL = 'ARCUSD'         
AMOUNT = 1.0              
CHECK_INTERVAL = 60       

bot_running = True  
last_analysis_log = "Initializing BOSS Bot..."
last_price_val = 0.0

app = Flask(__name__)

def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

# **स्मार्ट लोकल रिस्पॉन्स इंजन (बिना किसी बाहरी API Key के हर सवाल का अलग जवाब)**
def get_smart_reply(user_text, current_price):
    text = user_text.lower()
    
    if "kya kr" in text or "क्या कर" in text or "what are you" in text:
        return f"भैया, अभी मैं {SYMBOL} पर नजर बनाए हुए हूँ। मार्केट का लाइव भाव ${current_price} चल रहा है और स्मार्ट मनी स्ट्रक्चर स्कैन हो रहा है!"
    elif "price" in text or "भाव" in text or "rate" in text or "bhav" in text:
        return f"अभी {SYMBOL} का वर्तमान भाव ${current_price} डॉलर चल रहा है, भाई साहब।"
    elif "status" in text or "hal" in text or "हाल" in text:
        return f"सिस्टम एकदम मस्त और एक्टिव मोड में चल रहा है! भाव ${current_price} है और ट्रेडिंग लूप चालू है।"
    elif "kaise" in text or "كيف" in text or "कैसे" in text:
        return f"मैं एकदम बढ़िया हूँ भाई! आप बताओ, मार्केट में कौन से ट्रेड का प्लान है?"
    else:
        return f"आपकी बात समझ गया भाई! {SYMBOL} का भाव ${current_price} है और मेरी पूरी नजर चार्ट पर है।"

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
    return "⚡ BOSS Autonomous Trading & Chat Bot is Live!"

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
            reply = "🟢 BOSS बोट फिर से पूरी तरह एक्टिव हो गया है!"
            send_telegram_message(reply)
            threading.Thread(target=send_voice_sync, args=("बोट चालू हो गया है, बताइए क्या हुकुम है।",)).start()
            
        elif text_lower == "/stop" or text_lower == "stop":
            bot_running = False
            reply = "🔴 BOSS बोट को रोक दिया गया है।"
            send_telegram_message(reply)
            threading.Thread(target=send_voice_sync, args=("बोट को रोक दिया गया है।",)).start()
            
        elif text_lower == "/status" or text_lower == "status":
            reply = f"📊 *BOSS Status:*\n- State: {'Running 🟢' if bot_running else 'Stopped 🔴'}\n- Price: ${last_price_val}\n- Symbol: {SYMBOL}"
            send_telegram_message(reply)
            threading.Thread(target=send_voice_sync, args=(f"अभी कॉइन का भाव है {last_price_val} डॉलर।",)).start()
            
        elif text:
            # अब हर अलग मैसेज का अलग और सटीक जवाब मिलेगा!
            reply = get_smart_reply(text, last_price_val)
            send_telegram_message(f"🤖 *BOSS:* {reply}")
            threading.Thread(target=send_voice_sync, args=(reply,)).start()
                
    return "OK", 200

# --- 3. BACKGROUND TRADING ENGINE ---
def boss_autonomous_trading_loop():
    global last_analysis_log, last_price_val, bot_running
    print("🚀 BOSS Background Trading Engine Started...")
    
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
                
                # यहाँ आप अपने हिसाब से ट्रेडिंग कंडीशन रख सकते हैं
                print(f"Checked {SYMBOL}: ${current_price}")
                
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
