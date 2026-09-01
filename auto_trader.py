# ============================================================
# AUTO TRADER MODULE (`auto_trader.py`)
# ============================================================

import time
from config import SYMBOL, DEFAULT_SIZE, PRODUCT_ID
from delta_api import get_live_price, get_candles, place_order
from trading_engine import get_engine_status

def run_auto_trading_loop():
    print("🤖 Auto Trader background loop initialized...")
    while True:
        try:
            if get_engine_status():
                price = get_live_price(SYMBOL)
                candles = get_candles(SYMBOL, "15m", 10)
                
                if candles and price > 0:
                    latest = float(candles[-1].get("close", price))
                    prev = float(candles[-2].get("close", price))
                    diff = latest - prev
                    
                    if diff > 0:
                        print(f"📈 [AUTO] Bullish condition met for {SYMBOL} at {price}. Placing BUY order...")
                        place_order(product_id=PRODUCT_ID, symbol=SYMBOL, side="buy", size=DEFAULT_SIZE)
                    elif diff < 0:
                        print(f"📉 [AUTO] Bearish condition met for {SYMBOL} at {price}. Placing SELL order...")
                        place_order(product_id=PRODUCT_ID, symbol=SYMBOL, side="sell", size=DEFAULT_SIZE)
            
            time.sleep(60)
        except Exception as e:
            print(f"❌ Auto trader loop error: {str(e)}")
            time.sleep(30)
