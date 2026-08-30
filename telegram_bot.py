elif command == "/ai":

    send_message(
        chat_id,
        "Gemini AI processing..."
    )

    answer = ask_gemini(
        "Explain how a professional trading "
        "system evaluates market direction "
        "using price action, trend, momentum, "
        "volume and risk management. "
        "Do not recommend a live trade."
    )

    # Telegram UTF-8 response
    try:

        send_message(
            chat_id,
            "GEMINI AI\n\n" + answer
        )

    except Exception as e:

        send_message(
            chat_id,
            "TELEGRAM SEND ERROR\n"
            + str(e)
        )
