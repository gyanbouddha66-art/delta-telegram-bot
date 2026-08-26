import os
import streamlit as st
import ccxt
from google import genai
from audio_recorder_streamlit import audio_recorder

# Page Config
st.set_page_config(page_title="BOSS AI Trading Manager", page_icon="⚡", layout="wide")
st.title("⚡ BOSS Trading & Voice Control System")

# 1. API Keys Setup
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
DELTA_KEY = os.environ.get("DELTA_API_KEY", "")
DELTA_SECRET = os.environ.get("DELTA_API_SECRET", "")

client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

def get_delta_exchange():
    if DELTA_KEY and DELTA_SECRET:
        return ccxt.delta({
            'apiKey': DELTA_KEY,
            'secret': DELTA_SECRET,
            'enableRateLimit': True,
        })
    return None

exchange = get_delta_exchange()

# Trade Execution Engine (Small TP & Wide SL)
def execute_smc_trade(symbol, side, amount, tp_percent=0.5, sl_percent=2.0):
    if not exchange:
        return "⚠️ Delta Exchange API Key / Secret missing!"
    try:
        order = exchange.create_order(symbol=symbol, type='market', side=side.lower(), amount=amount)
        price = float(order.get('price') or exchange.fetch_ticker(symbol)['last'])
        
        if side.upper() == 'BUY':
            tp_price = price * (1 + (tp_percent / 100))
            sl_price = price * (1 - (sl_percent / 100))
        else:
            tp_price = price * (1 - (tp_percent / 100))
            sl_price = price * (1 + (sl_percent / 100))

        exchange.create_order(symbol=symbol, type='take_profit', side='sell' if side.upper() == 'BUY' else 'buy', amount=amount, price=tp_price)
        exchange.create_order(symbol=symbol, type='stop_loss', side='sell' if side.upper() == 'BUY' else 'buy', amount=amount, price=sl_price)

        return f"✅ **Trade Open Successful!**\n- Side: {side.upper()}\n- Entry: {price}\n- Small TP: {tp_price}\n- Wide SL: {sl_price}"
    except Exception as e:
        return f"❌ **Execution Error:** {e}"

# Close Specific Position Function
def close_position(symbol):
    if not exchange:
        return "⚠️ Exchange Connected नहीं है!"
    try:
        positions = exchange.fetch_positions()
        for p in positions:
            if p['symbol'] == symbol and float(p.get('contracts', 0)) > 0:
                side_to_close = 'sell' if p['side'].lower() in ['long', 'buy'] else 'buy'
                amount = float(p['contracts'])
                exchange.create_order(symbol=symbol, type='market', side=side_to_close, amount=amount)
                return f"🚨 **Position Closed!** {symbol} की {amount} quantity बंद कर दी गई है।"
        return f"⚠️ {symbol} पर कोई ओपन पोजीशन नहीं मिली।"
    except Exception as e:
        return f"❌ **Close Position Error:** {e}"

# Emergency Close All Positions
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
        return f"🚨 **Emergency Action Completed!** कुल {closed_count} खुली ट्रेड्स बंद कर दी गईं।"
    except Exception as e:
        return f"❌ Error: {e}"

# AI Core Processing (Renamed to BOSS)
def run_boss_agent(user_input):
    with st.spinner("BOSS एनालाइज कर रहा है..."):
        try:
            system_prompt = (
                "Your name is BOSS. You are an elite crypto SMC trading assistant and companion. "
                "Always refer to yourself as BOSS. "
                "You execute trades with Small TP and Wide SL based on Smart Money Concepts. "
                "You can also CLOSE trades if user asks or if market structure turns invalid. "
                "Respond naturally in simple Hindi/Hinglish. "
                "Triggers for trade operations:\n"
                "1. Open Trade: '[ACTION: BUY|SELL, SYMBOL: ARCUSD, AMOUNT: 1.0, TP: 0.5, SL: 2.0]'\n"
                "2. Close Single Trade: '[ACTION: CLOSE, SYMBOL: ARCUSD]'\n"
                "3. Close ALL Trades: '[ACTION: CLOSE_ALL]'"
            )
            
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[system_prompt, user_input] if isinstance(user_input, dict) else f"{system_prompt}\nUser: {user_input}"
            )
            
            reply = response.text
            st.success("🤖 **BOSS AI:**")
            st.write(reply)

            # Execution Logic Check
            if "[ACTION:" in reply:
                action_part = reply.split("[ACTION:")[1].split("]")[0]
                parts = dict(item.strip().split(":") for item in action_part.split(","))
                
                action = parts.get("ACTION").strip()
                symbol = parts.get("SYMBOL", "ARCUSD").strip()

                if action in ["BUY", "SELL"]:
                    amount = float(parts.get("AMOUNT", 1.0))
                    tp = float(parts.get("TP", 0.5))
                    sl = float(parts.get("SL", 2.0))
                    st.warning(f"⚡ Executing {action} Order on {symbol}...")
                    st.markdown(execute_smc_trade(symbol, action, amount, tp_percent=tp, sl_percent=sl))
                elif action == "CLOSE":
                    st.warning(f"🚨 Closing Position on {symbol}...")
                    st.markdown(close_position(symbol))
                elif action == "CLOSE_ALL":
                    st.warning("🚨 Closing ALL Active Positions...")
                    st.markdown(close_all_positions())

        except Exception as e:
            st.error(f"Error: {e}")

# Streamlit UI Setup
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 BOSS Voice & Command Control")
    audio_bytes = audio_recorder(text="बोलकर BOSS को कमांड दें", icon_name="microphone", icon_size="2x")
    if audio_bytes and GEMINI_KEY:
        audio_part = genai.types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
        run_boss_agent(audio_part)

    user_text = st.text_input("संदेश या कमांड लिखें:", placeholder="जैसे: 'BOSS ARCUSD पर 1 buy करो' या 'सारे ट्रेड बंद करो'")
    if st.button("Ask / Command BOSS"):
        if user_text:
            run_boss_agent(user_text)

with col2:
    st.subheader("📊 Live Open Positions")
    
    # Emergency Close All Button
    if st.button("🚨 CLOSE ALL POSITIONS NOW", type="primary"):
        st.markdown(close_all_positions())
        
    st.divider()

    if exchange:
        if st.button("🔄 Refresh Positions"):
            try:
                positions = exchange.fetch_positions()
                active_pos = [p for p in positions if float(p.get('contracts', 0)) > 0]
                if active_pos:
                    for pos in active_pos:
                        st.info(f"**Symbol:** {pos['symbol']}\n- Side: {pos['side']}\n- Contracts: {pos['contracts']}\n- Entry: {pos['entryPrice']}\n- PnL: {pos['unrealizedPnl']}")
                        if st.button(f"Close {pos['symbol']}", key=pos['symbol']):
                            st.markdown(close_position(pos['symbol']))
                else:
                    st.write("कोई खुली पोजीशन नहीं है।")
            except Exception as e:
                st.error(f"Positions Error: {e}")
    else:
        st.warning("Delta API Connect नहीं है।")
