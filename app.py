# ============================================================
# REAL DELTA ORDER WITH EXCHANGE-SIDE SL & TP (BRACKET)
# ============================================================

def execute_real_order(
    exchange,
    symbol,
    decision
):

    global last_trade_time
    global daily_trades

    side = (
        "buy"
        if decision.decision.upper()
        == "BUY"
        else
        "sell"
    )

    # ऑपोजिट साइड (SL और TP के लिए)
    close_side = "sell" if side == "buy" else "buy"

    with order_lock:

        try:

            print(
                "=============================="
            )

            print(
                "REAL ORDER WITH SL/TP"
            )

            print(
                "SIDE:",
                side
            )

            print(
                "AMOUNT:",
                AMOUNT
            )

            print(
                "ENTRY:",
                decision.entry
            )

            print(
                "SL:",
                decision.stop_loss
            )

            print(
                "TP:",
                decision.take_profit
            )

            # ------------------------------------------------
            # 1. MAIN MARKET ORDER
            # ------------------------------------------------

            order = exchange.create_order(

                symbol=symbol,

                type="market",

                side=side,

                amount=AMOUNT
            )

            order_id = order.get(
                "id",
                "UNKNOWN"
            )

            # ------------------------------------------------
            # 2. EXCHANGE-SIDE TAKE PROFIT (LIMIT ORDER)
            # ------------------------------------------------
            tp_order_id = "N/A"
            try:
                tp_order = exchange.create_order(
                    symbol=symbol,
                    type="limit",
                    side=close_side,
                    amount=AMOUNT,
                    price=decision.take_profit,
                    params={"reduce_only": True}
                )
                tp_order_id = tp_order.get("id", "UNKNOWN")
            except Exception as tp_err:
                print("TP Order Failed:", tp_err)
                telegram(f"⚠️ TP Order Warning: {tp_err}")

            # ------------------------------------------------
            # 3. EXCHANGE-SIDE STOP LOSS (STOP MARKET ORDER)
            # ------------------------------------------------
            sl_order_id = "N/A"
            try:
                sl_order = exchange.create_order(
                    symbol=symbol,
                    type="stop_market",
                    side=close_side,
                    amount=AMOUNT,
                    price=decision.stop_loss,
                    params={
                        "stop_price": decision.stop_loss,
                        "reduce_only": True
                    }
                )
                sl_order_id = sl_order.get("id", "UNKNOWN")
            except Exception as sl_err:
                print("SL Order Failed:", sl_err)
                telegram(f"⚠️ SL Order Warning: {sl_err}")

            last_trade_time = time.time()

            daily_trades += 1

            message = (
                "🚨 GEMINI REAL BRACKET TRADE\n\n"

                f"Symbol: {symbol}\n"
                f"Side: {side.upper()}\n"
                f"Amount: {AMOUNT}\n\n"

                f"Entry ID: {order_id}\n"
                f"TP ID: {tp_order_id} @ {decision.take_profit}\n"
                f"SL ID: {sl_order_id} @ {decision.stop_loss}\n\n"

                f"Confidence: {decision.confidence}%\n\n"

                f"Reason:\n"
                f"{decision.reason}\n\n"

                f"Invalidation:\n"
                f"{decision.invalidation}"
            )

            telegram(message)

            print(message)

        except Exception as e:

            print(
                "REAL ORDER FAILED:",
                e
            )

            telegram(
                "❌ REAL ORDER FAILED\n\n"
                + str(e)
            )
