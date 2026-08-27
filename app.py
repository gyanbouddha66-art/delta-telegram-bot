import os
import time
import threading
import streamlit as st
import ccxt
import requests
from google import genai

# --- 1. CONFIGURATIONS ---
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"              
GEMINI_API_KEY = "AQ.Ab8RN6LRNq3mOnbnzB3T3Yny8Uskk7DRpOajm6ssmHXavzPYAg"

DELTA_API_KEY = "nHv2Al08t6Bd8O1KSGBXCHP2ZbpmP3"
DELTA_API_SECRET = "tCTPHxKcZxZ2wvk9oMyFrgDRkTK37ryjRNDM6Lhkt6neE2MfIkv9lL5vW8se"

SYMBOL = 'ARCUSD'         
AMOUNT = 1.0              
CHECK_INTERVAL = 60       

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# --- STREAMLIT SESSION STATE SETUP ---
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'bot_status' not in st.session_state:
    st.session_state.bot_status = "Stopped (Manual Mode)"
if 'last_price' not in st.session_state:
    st.session_state.last_price = 0.0
if 'account_balance' not in st.session_state:
    st.session_state.account_balance = 0.0
if 'open_positions' not in st.session_state:
    st.session_state.open_positions = "No Active Trades"
if 'live_pnl' not in st.session_state:
    st.session_state.live_pnl = 0.0
if 'total_trades' not in st.session_state:
    st.session_state.total_trades = 0
if 'wins' not in st.session_state:
    st.session_state.wins = 0
if 'last_decision' not in st.session_state:
    st.session_state.last_decision = "Waiting to start..."

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def boss_autonomous_trading_loop():
    print("BOSS Background Loop Started.")
    
    # Safe Exchange Initialization inside loop to prevent immediate startup crash
    try:
        exchange = ccxt.delta({
            'apiKey': DELTA_API_KEY,
            'secret': DELTA_API_SECRET,
            'enableRateLimit': True,
        })
    except Exception as e:
        print(f"Exchange Init Error: {e}")
        exchange = None

    while True:
        if st.session_state.bot_running and exchange:
            try:
                # 1. Fetch Balance safely
                try:
                    balance = exchange.fetch_balance()
                    st.session_state.account_balance = balance.get('USDT', {}).get('free', 0.0)
                except Exception:
                    pass

                # 2. Market Ticker & Price
                st.session_state.bot_status = "Scanning Market..."
                ticker = exchange.fetch_ticker(SYMBOL)
                current_price = ticker['last']
                st.session_state.last_price = current_price
                
                # 3. Fetch Positions / PnL safely
                try:
                    positions = exchange.fetch_positions([SYMBOL])
                    if positions:
                        pos = positions[0]
                        st.session_state.open_positions = f"{pos.get('side', 'N/A').upper()} | Size: {pos.get('contracts', 0)}"
                        st.session_state.live_pnl = pos.get('unrealizedPnl', 0.0)
                    else:
                        st.session_state.open_positions = "No Open Positions"
                        st.session_state.live_pnl = 0.0
                except Exception:
                    st.session_state.open_positions = "Tracking Active"

                # 4. AI Decision Making via Gemini
                ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe='1h', limit=20)
                prompt = (
                    f"You are BOSS, an elite autonomous crypto trading AI. Current market data for {SYMBOL}: "
                    f"Current Price is {current_price}. Recent candles (OHLCV): {ohlcv[-5:]}. "
                    "Analyze the market completely based on Smart Money Concepts, price action, and momentum. "
                    "Decide if we should take a trade right now. "
                    "If a trade is strictly necessary, output ONLY in this exact format at the end: "
                    "[ACTION: BUY] or [ACTION: SELL]. If no trade is safe, output [ACTION: HOLD]."
                )

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                decision_text = response.text
                st.session_state.last_decision = decision_text

                if "[ACTION: BUY]" in decision_text:
                    exchange.create_order(symbol=SYMBOL, type='market', side='buy', amount=AMOUNT)
                    st.session_state.total_trades += 1
                    send_telegram_message(f"✅ *BOSS ने खुद BUY ट्रेड लिया!*\n- Symbol: {SYMBOL}\n- Price: {current_price}")
                elif "[ACTION: SELL]" in decision_text:
                    exchange.create_order(symbol=SYMBOL, type='market', side='sell', amount=AMOUNT)
                    st.session_state.total_trades += 1
                    send_telegram_message(f"🚨 *BOSS ने खुद SELL ट्रेड लिया!*\n- Symbol: {SYMBOL}\n- Price: {current_price}")
                
                st.session_state.bot_status = "Running & Monitoring..."
            except Exception as e:
                st.session_state.bot_status = f"Error: {e}"
        else:
            st.session_state.bot_status = "Stopped (Manual Mode)"
            
        time.sleep(CHECK_INTERVAL)

@st.cache_resource
def start_boss_background_thread():
    t = threading.Thread(target=boss_autonomous_trading_loop, daemon=True)
    t.start()
    return "Started"

start_boss_background_thread()


# --- 2. STREAMLIT DASHBOARD UI ---
st.set_page_config(page_title="BOSS AI - Command & Control", page_icon="⚡", layout="wide")
st.title("⚡ BOSS Autonomous AI - Command & Live Analytics")

# --- MANUAL CONTROL PANEL ---
st.markdown("### 🎛️ Manual Control Panel")
col_btn1, col_btn2, col_status = st.columns([1, 1, 2])

with col_btn1:
    if st.button("▶️ START BOSS", type="primary"):
        st.session_state.bot_running = True

with col_btn2:
    if st.button("⏹️ STOP BOSS", type="secondary"):
        st.session_state.bot_running = False

with col_status:
    st.info(f"**Current Status:** {st.session_state.bot_status}")

st.markdown("---")

# --- LIVE METRICS & DELTA STATS ---
st.markdown("### 📊 Delta Real-Time Portfolio & Performance")
m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.metric(label="Delta Balance", value=f"${st.session_state.account_balance:.2f}")
with m2:
    st.metric(label=f"{SYMBOL} Price", value=f"${st.session_state.last_price}")
with m3:
    st.metric(label="Live PnL", value=f"${st.session_state.live_pnl:.2f}")
with m4:
    win_rate = (st.session_state.wins / st.session_state.total_trades * 100) if st.session_state.total_trades > 0 else 0.0
    st.metric(label="Win Rate", value=f"{win_rate:.1f}%")
with m5:
    st.metric(label="Total Trades", value=st.session_state.total_trades)

# --- ACTIVE POSITION & AI LOG ---
st.markdown("### 🔍 Live Position & AI Analysis Log")
col_pos, col_log = st.columns(2)

with col_pos:
    st.subheader("Active Trade Position")
    st.success(st.session_state.open_positions)

with col_log:
    st.subheader("Latest AI Decision")
    st.info(st.session_state.last_decision)

# Auto-refresh every 10 seconds
st.markdown("<meta http-equiv='refresh' content='10'>", unsafe_allow_html=True)
