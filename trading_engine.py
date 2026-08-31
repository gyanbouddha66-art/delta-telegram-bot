import os
import math

from delta_api import get_live_price, get_candles


# ============================================================
# GH LIVE TRADING ENGINE
# ============================================================

SYMBOL = os.getenv("TRADE_SYMBOL", "BTCUSD")
TIMEFRAME = os.getenv("TRADE_TIMEFRAME", "1m")

SL_PERCENT = float(
    os.getenv("SL_PERCENT", "0.40")
)

TP_PERCENT = float(
    os.getenv("TP_PERCENT", "0.80")
)

MIN_CONFIDENCE = float(
    os.getenv("MIN_CONFIDENCE", "70")
)


# ============================================================
# EMA
# ============================================================

def ema(values, length):

    if len(values) < length:
        return None

    multiplier = 2 / (length + 1)

    result = sum(
        values[:length]
    ) / length

    for price in values[length:]:

        result = (
            (price - result) * multiplier
            + result
        )

    return result


# ============================================================
# ENGINE
# ============================================================

def get_signal(
    symbol=None,
    timeframe=None
):

    symbol = symbol or SYMBOL
    timeframe = timeframe or TIMEFRAME

    market = get_candles(
        symbol,
        timeframe,
        200
    )

    if not market.get("success"):

        return {
            "signal": "NO TRADE",
            "confidence": 0,
            "reason": "Market data unavailable",
            "error": market.get("error")
        }

    candles = market.get(
        "candles",
        []
    )

    if len(candles) < 50:

        return {
            "signal": "NO TRADE",
            "confidence": 0,
            "reason": "Not enough candles"
        }

    closes = [
        float(x["close"])
        for x in candles
        if x.get("close") is not None
    ]

    if len(closes) < 50:

        return {
            "signal": "NO TRADE",
            "confidence": 0,
            "reason": "Invalid candle data"
        }

    price = closes[-1]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)

    score_buy = 0
    score_sell = 0

    if ema9 > ema21:
        score_buy += 30
    elif ema9 < ema21:
        score_sell += 30

    if ema21 > ema50:
        score_buy += 30
    elif ema21 < ema50:
        score_sell += 30

    if price > ema9:
        score_buy += 20
    elif price < ema9:
        score_sell += 20

    if closes[-1] > closes[-2]:
        score_buy += 20
    elif closes[-1] < closes[-2]:
        score_sell += 20

    if score_buy >= MIN_CONFIDENCE:

        entry = price

        sl = entry * (
            1 - SL_PERCENT / 100
        )

        tp = entry * (
            1 + TP_PERCENT / 100
        )

        return {
            "signal": "BUY",
            "confidence": score_buy,
            "symbol": symbol,
            "timeframe": timeframe,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "rr": TP_PERCENT / SL_PERCENT,
            "reason": (
                "EMA trend + price momentum bullish"
            )
        }

    if score_sell >= MIN_CONFIDENCE:

        entry = price

        sl = entry * (
            1 + SL_PERCENT / 100
        )

        tp = entry * (
            1 - TP_PERCENT / 100
        )

        return {
            "signal": "SELL",
            "confidence": score_sell,
            "symbol": symbol,
            "timeframe": timeframe,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "rr": TP_PERCENT / SL_PERCENT,
            "reason": (
                "EMA trend + price momentum bearish"
            )
        }

    return {
        "signal": "NO TRADE",
        "confidence": max(
            score_buy,
            score_sell
        ),
        "symbol": symbol,
        "timeframe": timeframe,
        "entry": price,
        "reason": "Signal confidence below threshold"
    }


def get_engine_status():

    return {
        "engine": "ONLINE",
        "mode": "LIVE",
        "live_trading": True,
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "signal": "READY"
    }
