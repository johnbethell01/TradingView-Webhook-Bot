from flask import Flask, request, jsonify
import os
import asyncio
import websockets
import json
import datetime
import requests

app = Flask(__name__)

# === ENV VARIABLES ===
DERIV_TOKEN = os.getenv("FAST_AUTOTRADE")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DEFAULT_AMOUNT = os.getenv("TRADE_AMOUNT", "5")
DEFAULT_DURATION = os.getenv("TRADE_DURATION", "3")

# === WEBSOCKET DERIV EXECUTION ===
async def execute_deriv_trade(signal, instrument, amount, duration):
    uri = "wss://ws.deriv.com/websockets/v3"
    async with websockets.connect(uri) as ws:
        # 1. Authorize
        await ws.send(json.dumps({"authorize": DERIV_TOKEN}))
        auth_response = await ws.recv()
        auth_data = json.loads(auth_response)
        if auth_data.get("error"):
            return f"❌ AUTH ERROR: {auth_data['error']['message']}"

        # 2. Create trade proposal
        proposal = {
            "buy": 1,
            "price": int(amount),
            "parameters": {
                "amount": int(amount),
                "basis": "stake",
                "contract_type": "CALL" if signal == "BUY" else "PUT",
                "currency": "USD",
                "duration": int(duration),
                "duration_unit": "m",
                "symbol": instrument
            }
        }

        await ws.send(json.dumps(proposal))
        response = await ws.recv()
        result = json.loads(response)
        if result.get("error"):
            return f"❌ TRADE ERROR: {result['error']['message']}"
        return f"✅ Trade sent: {signal} {instrument}, ${amount} for {duration}m"

# === TELEGRAM SEND ===
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.status_code
    except Exception as e:
        return f"Telegram error: {str(e)}"

# === FLASK ROUTE ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print("🔍 RAW BODY RECEIVED:", data)

        signal = data.get("signal", "").upper()
        instrument = data.get("instrument", "frxBTCUSD")
        amount = data.get("amount", DEFAULT_AMOUNT)
        duration = data.get("duration", DEFAULT_DURATION)

        if signal not in ["BUY", "SELL"]:
            return jsonify({"error": "Invalid signal value"}), 400

        # Trigger async WebSocket trade
        result = asyncio.run(execute_deriv_trade(signal, instrument, amount, duration))
        print("🧾 Deriv response:", result)

        # Send Telegram confirmation
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        message = (
            f"🚨 *Trade Executed*\n"
            f"*Signal:* {signal}\n"
            f"*Amount:* ${amount}\n"
            f"*Duration:* {duration}m\n"
            f"*Pair:* {instrument}\n"
            f"*Time:* `{timestamp}`"
        )
        send_telegram_message(message)

        return jsonify({"status": "success", "result": result})

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

# === ENTRYPOINT ===
if __name__ == "__main__":
    app.run(port=10000)
