import os
import json
import asyncio
import websockets
from flask import Flask, request, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

DERIV_TOKEN = os.getenv("FAST_AUTOTRADE")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "1")

async def send_trade_ws(signal_type, symbol, duration):
    async with websockets.connect("wss://ws.derivws.com/websockets/v3") as ws:
        await ws.send(json.dumps({
            "authorize": DERIV_TOKEN
        }))
        await ws.recv()

        proposal = {
            "buy": 1,
            "price": float(TRADE_AMOUNT),
            "parameters": {
                "amount": float(TRADE_AMOUNT),
                "basis": "stake",
                "contract_type": "CALL" if signal_type == "BUY" else "PUT",
                "currency": "USD",
                "duration": int(duration),
                "duration_unit": "m",
                "symbol": symbol
            },
            "passthrough": {
                "duration": duration
            },
            "req_id": 1
        }

        await ws.send(json.dumps(proposal))
        response = await ws.recv()
        print(f"🧾 Deriv WebSocket Response ({duration}m):", response)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        raw_data = request.data.decode("utf-8")
        print("🔍 RAW BODY RECEIVED:", raw_data)

        data = json.loads(raw_data)
        signal = data.get("signal", "").upper()
        instrument = data.get("instrument", "")

        print("📩 Parsed JSON:", data)

        if signal not in ["BUY", "SELL"] or not instrument:
            return jsonify({"error": "Invalid signal or instrument"}), 400

        print(f"✔️ Triggering {signal} for {instrument}...")

        # Launch 1m, 3m, and 5m trades asynchronously
        asyncio.run(send_trade_ws(signal, instrument, 1))
        asyncio.run(send_trade_ws(signal, instrument, 3))
        asyncio.run(send_trade_ws(signal, instrument, 5))

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        telegram_message = (
            f"🚨 Trade Executed\n"
            f"*Signal:* {signal}\n"
            f"*Pair:* {instrument}\n"
            f"*Time:* `{now}`"
        )

        send_telegram(telegram_message)
        return jsonify({"status": "success", "message": {"result": f"{signal} order for {instrument} sent"}})

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({"status": "error", "message": {"error": str(e)}}), 500

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_USER_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        print("📲 Telegram alert sent:", response.status_code, response.text)
    except Exception as e:
        print("❌ Telegram Error:", e)

if __name__ == "__main__":
    app.run(debug=True)
