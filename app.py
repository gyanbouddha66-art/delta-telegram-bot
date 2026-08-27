import os
import streamlit as st
import ccxt
from google import genai
import streamlit.components.v1 as components

# Page Config
st.set_page_config(page_title="BOSS AI - Smart & Fast", page_icon="⚡", layout="wide")
st.title("⚡ BOSS Smart AI - Super Fast Real-Time Assistant")

# --- SIDEBAR FOR SECURE API KEYS INPUT ---
st.sidebar.header("🔑 API Keys Setup")
st.sidebar.write("डैशबोर्ड की जरूरत नहीं, यहाँ अपनी चाबियाँ दर्ज करें:")

input_gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
input_delta_key = st.sidebar.text_input("Delta API Key", type="password", value=os.environ.get("DELTA_API_KEY", ""))
input_delta_secret = st.sidebar.text_input("Delta API Secret", type="password", value=os.environ.get("DELTA_API_SECRET", ""))

# Use input keys or fallback to environment/secrets
GEMINI_KEY = input_gemini_key or st.secrets.get("GEMINI_API_KEY", "")
DELTA_KEY = input_delta_key or st.secrets.get("DELTA_API_KEY", "")
DELTA_SECRET = input_delta_secret or st.secrets.get("DELTA_API_SECRET", "")

client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

def get_delta_exchange():
    if DELTA_KEY and DELTA_SECRET:
        try:
            return ccxt.delta({
                'apiKey': DELTA_KEY,
                'secret': DELTA_SECRET,
                'enableRateLimit': True,
            })
        except Exception:
            return None
    return None

exchange = get_delta_exchange()

# Instant Browser Speech Synthesis (Zero Lag, Gemini Style Audio)
def speak_instantly(text):
    clean_text = text.split("[ACTION:")[0].strip() if "[ACTION:" in text else text
    clean_text = clean_text.replace("*", "").replace("#", "").replace("`", "").replace('"', '').replace("'", "")
    
    js_code = f"""
    <script>
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            let utterance = new SpeechSynthesisUtterance("{clean_text}");
            utterance.lang = 'hi-IN';
            utterance.rate = 1.0;
            window.speechSynthesis.speak(utterance);
        }}
    </script>
    """
    components.html(js_code, height=0)

# Autonomous Trade Execution
def execute_autonomous_trade(symbol, side, amount):
    if not exchange:
        return "⚠️ Delta Exchange API Key / Secret सही से दर्ज नहीं हैं!"
    try:
        order = exchange.create_order(symbol=symbol, type='market', side=side.lower(), amount=amount)
        price = float(order.get('price') or exchange.fetch_ticker(symbol)['last'])
        return f"✅ **BOSS ने ट्रेड ले लिया है!**\n- Side: {side.upper()}\n- Symbol: {symbol}\n- Entry Price: {price}"
    except Exception as e:
        return f"❌ **Execution Error:** {e}"

def close_autonomous_position(symbol):
    if not exchange:
        return "⚠️ Exchange Connected नहीं है!"
    try:
        positions = exchange.fetch_positions()
        for p in positions:
            if p['symbol'] == symbol and float(p.get('contracts', 0)) > 0:
                side_to_close = 'sell' if p['side'].lower() in ['long', 'buy'] else 'buy'
                amount = float(p['contracts'])
                exchange.create_order(symbol=symbol, type='market', side=side_to_close, amount=amount)
                return f"🚨 **BOSS ने पोजीशन काट दी है!** {symbol} की {amount} quantity बंद।"
        return f"⚠️ {symbol} पर कोई ओपन पोजीशन नहीं मिली।"
    except Exception as e:
        return f"❌ **Close Position Error:** {e}"

def close_all_positions():
    if not exchange:
        return "⚠️ Exchange Connected नहीं है!"
    try:
        positions = exchange.fetch_positions()
        closed_count = 0
        for p in positions:
            contracts = float(p.get('contracts', 0))
            if contracts > 0:
                symbol = p['symbol']
                side_to_close = 'sell' if p['side'].lower() in ['long', 'buy'] else 'buy'
                exchange.create_order(symbol=symbol, type='market', side=side_to_close, amount=contracts)
                closed_count += 1
        return f"🚨 **Emergency Close!** BOSS ने सभी {closed_count} ट्रेड्स बंद कर दी हैं।"
    except Exception as e:
        return f"❌ Error: {e}"

# Gemini-like Smart AI Core
def run_boss_agent(user_input):
    if not GEMINI_KEY:
        st.error("⚠️ कृपया पहले बाईं ओर (Sidebar में) अपनी Gemini API Key दर्ज करें!")
        return
        
    with st.spinner("BOSS सोच रहा है..."):
        try:
            system_prompt = (
                "Your name is BOSS. You are an ultra-intelligent, sharp, and multi-talented AI companion, just like Gemini, "
                "with elite expertise in crypto trading using Smart Money Concepts (SMC) and Order Flow. "
                "Always refer to yourself as BOSS. Speak exclusively in natural, powerful, and engaging Hindi / Hinglish. "
                "You can answer ANY general questions, write code, solve problems, or chat casually with high intelligence and wit. "
                "CRITICAL: Give a smart, detailed, and clear response. "
                "If a trade action is required, output your thought process in Hindi first, "
                "and strictly include the trigger at the very end in this format:\n"
                "[ACTION: BUY, SYMBOL: ARCUSD, AMOUNT: 1.0]"
            )
            
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[system_prompt, user_input] if isinstance(user_input, dict) else f"{system_prompt}\nUser: {user_input}"
                )
            except Exception as api_err:
                if "429" in str(api_err) or "RESOURCE_EXHAUSTED" in str(api_err):
                    st.warning("⏳ भाई साहब, 1 मिनट की कोटा लिमिट पूरी हो गई है। कृपया थोड़ा रुककर दोबारा कमांड दें।")
                    speak_instantly("भाई साहब, लिमिट पूरी हो गई है, थोड़ा रुककर कमांड दें।")
                    return
                else:
                    raise api_err
            
            reply = response.text
            
            st.markdown("---")
            st.markdown("### 🧠 **BOSS का स्मार्ट उत्तर और विश्लेषण:**")
            st.markdown(f"## 🗣️ `{reply}`")
            st.markdown("---")

            speak_instantly(reply)

            if "[ACTION:" in reply:
                action_part = reply.split("[ACTION:")[1].split("]")[0]
                items = action_part.split(",")
                parts = {}
                for item in items:
                    if ":" in item:
                        k, v = item.split(":", 1)
                        parts[k.strip().upper()] = v.strip()
                
                action = parts.get("ACTION", "").upper()
                symbol = parts.get("SYMBOL", "ARCUSD").upper()

                if action in ["BUY", "SELL"]:
                    amount = float(parts.get("AMOUNT", 1.0))
                    st.warning(f"⚡ BOSS एक्शन ले रहा है: Executing {action} on {symbol}...")
                    st.markdown(execute_autonomous_trade(symbol, action, amount))
                elif action == "CLOSE":
                    st.warning(f"🚨 BOSS पोजीशन बंद कर रहा है...")
                    st.markdown(close_autonomous_position(symbol))
                elif action == "CLOSE_ALL":
                    st.warning(f"🚨 BOSS सभी पोजीशन बंद कर रहा है...")
                    st.markdown(close_all_positions())

        except Exception as e:
            st.error(f"Error: {e}")

# Streamlit UI Setup
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 BOSS सुपर-फास्ट चैट और वॉयस कंट्रोल")
    
    user_text = st.text_input("कुछ भी पूछें या कमांड दें:", placeholder="जैसे: 'भाई कैसे हो?' या मार्केट के बारे में पूछो")
    if st.button("Ask BOSS"):
        if user_text:
            run_boss_agent(user_text)

with col2:
    st.subheader("📊 Live Open Positions")
    if st.button("🚨 CLOSE ALL POSITIONS NOW", type="primary"):
        st.markdown(close_all_positions())
        
    st.divider()

    if exchange:
        st.success("✅ Delta Exchange Connected!")
        if st.button("🔄 Refresh Positions"):
            try:
                positions = exchange.fetch_positions()
                active_pos = [p for p in positions if float(p.get('contracts', 0)) > 0]
                if active_pos:
                    for pos in active_pos:
                        st.info(f"**Symbol:** {pos['symbol']}\n- Side: {pos['side']}\n- Contracts: {pos['contracts']}\n- Entry: {pos['entryPrice']}\n- PnL: {pos['unrealizedPnl']}")
                        if st.button(f"Close {pos['symbol']}", key=pos['symbol']):
                            st.markdown(close_autonomous_position(pos['symbol']))
                else:
                    st.write("कोई खुली पोजीशन नहीं है।")
            except Exception as e:
                st.error(f"Positions Error: {e}")
    else:
        st.warning("⚠️ कृपया बाईं तरफ (Sidebar में) Delta API Key और Secret दर्ज करें।")
