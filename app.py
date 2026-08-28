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

# रिस्क मैनेजमेंट सेटिंग्स (TP और SL प्रतिशत)
TP_PERCENT = 0.015  # 1.5% टेक प्रॉफिट
SL_PERCENT = 0.01   # 1.0% स्टॉप लॉस

bot_running = True  
last_analysis_log = "Hybrid BOSS Engine Ready..."
last_price_val = 1.0  

app = Flask(__name__)

def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

# **स्मार्ट ब्रेन चैट इंजन**
def get_smart_brain_reply(user_text, current_price, is_running):
    text = user_text.lower()
    status_text = "ऑटो-ट्रेडिंग चालू है 🟢" if is_running else "ऑटो-ट्रेडिंग बंद है 🔴 (मैनुअल मोड)"
    
    if any(word in text for word in ["kya kr", "kya kar", "kya chal", "what are you doing", "के कर"]):
        return f"भैया, अभी मैं {SYMBOL} पर नजर गड़ाए बैठा हूँ। लाइव भाव ${current_price} है और {status_text}!"
    elif any(word in text for word in ["price", "भाव", "rate", "bhav", "kitna"]):
        return f"अभी {SYMBOL} का वर्तमान भाव ${current_price} डॉलर चल रहा है, भाई साहब।"
    elif any(word in text for word in ["status", "hal", "हाल", "कैसा"]):
        return f"सिस्टम स्टेटस: {status_text} | भाव: ${current_price} | /buy या /sell से मैनुअल ट्रेड ले सकते हैं।"
    elif any(word in text for word in ["kota", "कोटा"]):
        return f"कोटा अपना होमटाउन है भाई, शिक्षा की नगरी! वहीं से बैठ कर पूरा सिस्टम कंट्रोल हो रहा है।"
    elif any(word in text for word in ["hi", "hello", "hey", "राम राम", "नमस्ते"]):
        return f"राम-राम भाई! {status_text}। बताओ क्या हुकुम है?"
    else:
        return f"बात तुम्हारी बिल्कुल सही है भाई! {SYMBOL} का भाव ${current_price} है। ({status_text})"

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

# **मास्टर ट्रेड फंक्शन (TP और SL के साथ)**
def execute_trade_with_tpsl(side, entry_price, mode="Manual"):
    try:
        exchange = ccxt.delta({
            'apiKey': DELTA_API_KEY,
            'secret': DELTA_API_SECRET,
            'enableRateLimit': True,
        })
        
        # 1. मार्केट आर्डर लगाएं
        order = exchange.create_order(symbol=SYMBOL, type='market', side=side, amount=AMOUNT)
        print(f"✅ [{mode}] Market {side.upper()} Order Executed at {entry_price}")
        
        # 2. TP और SL के लेवल कैलकुलेट करें
        if side == 'buy':
            tp_price = entry_price * (1 + TP_PERCENT)
            sl_price = entry_price * (1 - SL_PERCENT)
        else:
            tp_price = entry_price * (1 - TP_PERCENT)
            sl_price = entry_price * (1 + SL_PERCENT)
            
        # टेलीग्राम अलर्ट भेजें
        alert_msg = (
            f"🚀 *BOSS [{mode}] {side.upper()} Executed!*\n"
            f"- Symbol: {SYMBOL}\n"
            f"- Entry: ${entry_price}\n"
            f"- Target (TP): ${round(tp_price, 4)}\n"
            f"- Stop Loss (SL): ${round(sl_price, 4)}"
        )
        send_telegram_message(alert_msg)
        threading.Thread(target=send_voice_sync, args=(f"भाई, {mode} मोड में {side} ट्रेड ले लिया है। टारगेट और स्टॉप लॉस सेट हैं।",)).start()
        
    except Exception as e:
        print(f"❌ [{mode}] Trade Error: {e}")
        send_telegram_message(f"❌ *Trade Error ({mode}):* {e}")

@app.route('/')
def home():
    return "⚡ Hybrid Control BOSS Trading Bot is Live!"

# --- 2. TELEGRAM WEBHOOK (स्टॉप, स्टार्ट, मैनुअल और चैट) ---
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
            reply = "🟢 *BOSS Auto-Trading Started!* अब बोट खुद भी मार्केट पर नजर रखेगा।"
            send_telegram_message(reply)
            threading.Thread(target=send_voice_sync, args=("बोट की ऑटो ट्रेडिंग चालू कर दी गई है।",)).start()
            
        elif text_lower == "/stop" or text_lower == "stop":
            bot_running = False
            reply = "🔴 *BOSS Auto-Trading Stopped!* ऑटो-ट्रेडिंग बंद कर दी गई है, लेकिन आप /buy और /sell से मैनुअल ट्रेड ले सकते हैं।"
            send_telegram_message(reply)
            threading.Thread(target=send_voice_sync, args=("ऑटो ट्रेडिंग बंद कर दी गई है।",)).start()
            
        elif text_lower == "/status" or text_lower == "status":
            status_str = "Running 🟢" if bot_running else "Stopped 🔴 (Manual Mode)"
            reply = f"📊 *BOSS Status:*\n- Auto-Trading: {status_str}\n- Price: ${last_price_val}\n- Symbol: {SYMBOL}"
            send_telegram_message(reply)
            threading.Thread(target=send_voice_sync, args=(f"अभी ऑटो ट्रेडिंग {status_str} है और भाव {last_price_val} डॉलर है।",)).start()
            
        elif text_lower == "/buy" or text_lower == "buy":
            send_telegram_message("⚡ *Manual BUY Command Received!*")
            threading.Thread(target=execute_trade_with_tpsl, args=('buy', last_price_val, "Manual")).start()
            
        elif text_lower == "/sell" or text_lower == "sell":
            send_telegram_message("⚡ *Manual SELL Command Received!*")
            threading.Thread(target=execute_trade_with_tpsl, args=('sell', last_price_val, "Manual")).start()
            
        elif text:
            reply = get_smart_brain_reply(text, last_price_val, bot_running)
            send_telegram_message(f"🤖 *BOSS:* {reply}")
            threading.Thread(target=send_voice_sync, args=(reply,)).start()
                
    return "OK", 200

# --- 3. BACKGROUND TRADING ENGINE ---
def boss_autonomous_trading_loop():
    global last_analysis_log, last_price_val, bot_running
    print("🚀 Hybrid BOSS Engine Started...")
    
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
        # केवल तभी ऑटो ट्रेड लेगा जब bot_running True होगा
        if bot_running and exchange:
            try:
                ticker = exchange.fetch_ticker(SYMBOL)
                if ticker and 'last' in ticker and ticker['last']:
                    current_price = ticker['last']
                    last_price_val = current_price
                    
                    # ओएचएलसीवी (OHLCV) डेटा से ऑटोमैटिक ट्रेंड चेक करें
                    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe='1h', limit=5)
                    if len(ohlcv) >= 3:
                        c1 = ohlcv[-3][4]
                        c2 = ohlcv[-2][4]
                        c3 = ohlcv[-1][4]
                        
                        # ऑटोमैटिक एंट्री कंडीशन
                        if c3 > c2 and c2 > c1 * 1.001:
                            last_analysis_log = f"Auto Setup matched at ${current_price}"
                            execute_trade_with_tpsl('buy', current_price, "Auto")
                            time.sleep(3600) # 1 घंटे का कूलडाउन
                            
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
