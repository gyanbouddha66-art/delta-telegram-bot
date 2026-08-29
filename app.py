from flask import Flask, jsonify
import os

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "system": "GH AI TRADING",
        "status": "ONLINE",
        "mode": "TEST"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "OK"
    })


@app.route("/status")
def status():
    return jsonify({
        "server": "ONLINE",
        "live_trading": False
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port
    )
