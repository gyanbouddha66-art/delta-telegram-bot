def execute_trade(exchange, symbol, decision):
    global last_trade_time, total_trades
    current_time = time.time()
    
    if current_time - last_trade_time < COOLDOWN_SECONDS:
        print("Cooldown active, skipping trade.")
        return

    try:
        side = decision.decision.lower() # buy or sell
        amount = AMOUNT
        
        if not REAL_TRADING:
            print(f"Simulated Trade: {side.upper()} {amount} {symbol}")
            return

        print(f"Attempting to send real order to Delta: {side.upper()} {amount} {symbol}")
        
        # यहाँ असली आर्डर पंच किया जा रहा है और डेल्टा का रिस्पॉन्स चेक होगा
        order = exchange.create_market_order(symbol, side, amount)
        print("Delta Order Response:", order)
        
        last_trade_time = current_time
        total_trades += 1
        
        total_bal, free_bal = get_account_balance(exchange)
        
        msg = (
            f"🚀 ट्रेड सफलतापर्वक डेल्टा पर ले ली गई है भाई साहब!\n"
            f"Side: {side.upper()}\n"
            f"Symbol: {symbol}\n"
            f"Wallet Balance: ${total_bal:.2f}"
        )
        telegram(msg)
        telegram_voice(f"भाई साहब, डेल्टा पर ट्रेड सफलतापूर्वक ले ली गई है।", TELEGRAM_CHAT_ID)
        
    except Exception as e:
        # अगर डेल्टा तक बात नहीं पहुँची या कोई भी एरर आया, तो वह यहाँ पकड़ा जाएगा
        error_msg = f"❌ Delta Order Failed Error: {str(e)}"
        print(error_msg)
        telegram(error_msg)
        telegram_voice("भाई साहब, डेल्टा पर आर्डर देते समय एरर आ गया है, कृपया लोग्स चेक करें।", TELEGRAM_CHAT_ID)
