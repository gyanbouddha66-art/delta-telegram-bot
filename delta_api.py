import os
import ccxt


def get_delta():
    api_key = os.getenv("DELTA_API_KEY")
    api_secret = os.getenv("DELTA_API_SECRET")

    if not api_key or not api_secret:
        return None

    exchange = ccxt.delta(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        }
    )

    return exchange


def test_delta():
    exchange = get_delta()

    if exchange is None:
        return {
            "success": False,
            "message": "Delta credentials not configured"
        }

    try:
        exchange.load_markets()

        balance = exchange.fetch_balance()

        return {
            "success": True,
            "message": "Delta authentication OK"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Delta authentication error: {e}"
        }
