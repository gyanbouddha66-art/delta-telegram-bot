
# ============================================================
# GH AI TRADING ENGINE
# TEST MODE ONLY
# ============================================================

LIVE_TRADING = False


def get_engine_status():
    return {
        "engine": "ONLINE",
        "mode": "TEST",
        "live_trading": LIVE_TRADING,
        "signal": "NO TRADE"
    }


def get_signal():
    """
    अभी सिर्फ test signal है।
    बाद में यहाँ आपकी वास्तविक trading strategy लगेगी।
    """

    return {
        "signal": "NO TRADE",
        "confidence": 0,
        "reason": "Strategy not connected yet"
    }
