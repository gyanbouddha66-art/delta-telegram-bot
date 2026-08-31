import os
import time
import hmac
import hashlib
import json
import requests


# ============================================================
# GH DELTA API
# REAL TRADING
# ============================================================

BASE_URL = "https://api.india.delta.exchange"


# ============================================================
# AUTH SIGNATURE
# ============================================================

def _credentials():

    api_key = os.getenv("DELTA_API_KEY", "").strip()
    api_secret = os.getenv("DELTA_API_SECRET", "").strip()

    if not api_key or not api_secret:
        return None, None

    return api_key, api_secret


def _request(
    method,
    path,
    params=None,
    body=None,
    authenticated=False
):

    params = params or {}
    body = body or {}

    query_string = ""

    if params:

        query_string = "?" + "&".join(
            f"{k}={v}"
            for k, v in params.items()
        )

    payload = ""

    if body:

        payload = json.dumps(
            body,
            separators=(",", ":")
        )

    timestamp = str(int(time.time()))

    if authenticated:

        api_key, api_secret = _credentials()

        if not api_key or not api_secret:

            return {
                "success": False,
                "error": "Delta credentials missing"
            }

        signature_data = (
            method.upper()
            + timestamp
            + path
            + query_string
            + payload
        )

        signature = hmac.new(
            api_secret.encode("utf-8"),
            signature_data.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "api-key": api_key,
            "timestamp": timestamp,
            "signature": signature,
            "User-Agent": "GH-Delta-Trading-Bot",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    else:

        headers = {
            "User-Agent": "GH-Delta-Trading-Bot",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    try:

        response = requests.request(
            method.upper(),
            BASE_URL + path,
            params=params,
            data=payload,
            headers=headers,
            timeout=30
        )

        try:
            data = response.json()
        except:
            data = {
                "raw": response.text
            }

        if not response.ok:

            return {
                "success": False,
                "http_status": response.status_code,
                "error": data
            }

        return data

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# LIVE PRICE
# ============================================================

def get_live_price(symbol):

    result = _request(
        "GET",
        f"/v2/tickers/{symbol}"
    )

    if not result.get("success"):

        return {
            "success": False,
            "error": result.get("error")
        }

    ticker = result.get(
        "result",
        {}
    )

    price = (
        ticker.get("close")
        or ticker.get("mark_price")
        or ticker.get("spot_price")
    )

    if price is None:

        return {
            "success": False,
            "error": "Live price unavailable"
        }

    return {
        "success": True,
        "symbol": symbol,
        "price": float(price),
        "ticker": ticker
    }


# ============================================================
# PRODUCT
# ============================================================

def get_product(symbol):

    result = _request(
        "GET",
        f"/v2/products/{symbol}"
    )

    if not result.get("success"):

        return {
            "success": False,
            "error": result.get("error")
        }

    product = result.get(
        "result",
        {}
    )

    return {
        "success": True,
        "product": product
    }


# ============================================================
# CANDLES
# ============================================================

def get_candles(
    symbol,
    timeframe="1m",
    limit=200
):

    timeframe = str(timeframe).lower()

    minutes_map = {
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "2h": 120,
        "4h": 240,
        "6h": 360,
        "1d": 1440
    }

    if timeframe not in minutes_map:

        return {
            "success": False,
            "error": f"Unsupported timeframe: {timeframe}"
        }

    minutes = minutes_map[timeframe]

    end = int(time.time())

    start = end - (
        minutes * 60 * (limit + 10)
    )

    result = _request(
        "GET",
        "/v2/history/candles",
        params={
            "resolution": timeframe,
            "symbol": symbol,
            "start": start,
            "end": end
        }
    )

    if not result.get("success"):

        return {
            "success": False,
            "error": result.get("error")
        }

    candles = result.get(
        "result",
        []
    )

    candles = sorted(
        candles,
        key=lambda x: x.get("time", 0)
    )

    if len(candles) > limit:

        candles = candles[-limit:]

    return {
        "success": True,
        "candles": candles
    }


# ============================================================
# BALANCE
# ============================================================

def get_delta_balances():

    result = _request(
        "GET",
        "/v2/wallet/balances",
        authenticated=True
    )

    if not result.get("success", False):

        return result

    balances = result.get(
        "result",
        []
    )

    return {
        "success": True,
        "http_status": 200,
        "balances": balances
    }


# ============================================================
# CURRENT POSITION
# ============================================================

def get_position(product_id):

    result = _request(
        "GET",
        "/v2/positions",
        params={
            "product_id": product_id
        },
        authenticated=True
    )

    if not result.get("success"):

        return result

    position = result.get(
        "result",
        {}
    )

    return {
        "success": True,
        "position": position,
        "size": float(
            position.get("size", 0) or 0
        )
    }


# ============================================================
# PLACE REAL MARKET ORDER
# ============================================================

def place_market_order(
    symbol,
    side,
    size,
    stop_loss=None,
    take_profit=None
):

    side = str(side).lower()

    if side not in ("buy", "sell"):

        return {
            "success": False,
            "error": "Side must be buy or sell"
        }

    if float(size) <= 0:

        return {
            "success": False,
            "error": "Order size must be greater than zero"
        }

    product_result = get_product(symbol)

    if not product_result.get("success"):

        return product_result

    product = product_result["product"]

    product_id = product.get("id")

    if not product_id:

        return {
            "success": False,
            "error": "Product ID unavailable"
        }

    body = {
        "product_id": int(product_id),
        "product_symbol": symbol,
        "size": int(size),
        "side": side,
        "order_type": "market_order"
    }

    # ========================================================
    # BRACKET TP / SL
    # ========================================================

    if stop_loss is not None:

        body[
            "bracket_stop_loss_price"
        ] = str(stop_loss)

    if take_profit is not None:

        body[
            "bracket_take_profit_price"
        ] = str(take_profit)

    body[
        "bracket_stop_trigger_method"
    ] = "last_traded_price"

    result = _request(
        "POST",
        "/v2/orders",
        body=body,
        authenticated=True
    )

    return result


# ============================================================
# TEST DELTA AUTH
# ============================================================

def test_delta():

    result = get_delta_balances()

    if result.get("success"):

        return {
            "success": True,
            "stage": "authenticated_request",
            "http_status": 200,
            "message": "Delta authentication OK"
        }

    return result
