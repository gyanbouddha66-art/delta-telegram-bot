            return
        
        pos = wait_for_fill()
        if not pos:
            send_telegram_msg(bot, "🚨 Position verification pending...")
            return
        
        entry = pos["entry_price"]
        bracket = place_bracket(entry, side)
        if not bracket or bracket.get("success") is False:
            send_telegram_msg(bot, "🚨 BRACKET FAILED!")
            return
        
        send_telegram_msg(bot, f"✅ ORDER & BRACKET SUCCESSFUL!\nEntry: {entry}")
        last_trade_time = time.time()
    finally:
        with order_lock:
            order_in_progress = False

def trading_loop(bot):
    global candles, bot_active
    load_product()
    candles = fetch_history()
    last_candle_fetch = time.time()
    
    while bot_active:
        try:
            price = get_live_price()
            if price is None:
                time.sleep(0.3)
                continue
            
            if time.time() - last_candle_fetch > 10 or not candles:
                candles = fetch_history()
                last_candle_fetch = time.time()

            signal, er = get_signal(price)
            if time.time() - last_trade_time > COOLDOWN_SECONDS:
                execute_trade(signal, price, er, bot)
                
            time.sleep(0.3)
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(0.3)

# TELEGRAM COMMAND HANDLERS
def cmd_start(update: Update, context: CallbackContext):
    global bot_active
    if str(update.effective_chat.id) != ALLOWED_CHAT_ID:
        return
    if not bot_active:
        bot_active = True
        threading.Thread(target=trading_loop, args=(context.bot,), daemon=True).start()
        update.message.reply_text("🟢 GH-V12 Trading Engine STARTED!")
    else:
        update.message.reply_text("⚠️ Engine is already running.")

def cmd_stop(update: Update, context: CallbackContext):
    global bot_active
    if str(update.effective_chat.id) != ALLOWED_CHAT_ID:
        return
    bot_active = False
    update.message.reply_text("🔴 GH-V12 Trading Engine STOPPED!")

def cmd_status(update: Update, context: CallbackContext):
    if str(update.effective_chat.id) != ALLOWED_CHAT_ID:
        return
    status_str = "🟢 RUNNING" if bot_active else "🔴 STOPPED"
    price = get_live_price()
    pos = get_position()
    pos_str = f"Size: {pos['size']} | Entry: {pos['entry_price']}" if pos else "No Active Position"
    update.message.reply_text(f"Status: {status_str}\nLive Price: {price}\nPosition: {pos_str}")

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("stop", cmd_stop))
    dp.add_handler(CommandHandler("status", cmd_status))
    
    updater.start_polling()
    print("Telegram Bot Running...")
    updater.idle()

if __name__ == "__main__":
    main()
