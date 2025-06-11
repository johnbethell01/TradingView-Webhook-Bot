# main.py v2 (patched for websocket-client usage)
# Make sure 'websocket-client' is added to your requirements.txt

import os
import json
from flask import Flask, request, jsonify
import requests
from websocket import create_connection

app = Flask(__name__)

# Get variables from environment
DERIV_TOKEN = os.getenv("FAST_AUTOTRADE")
# Debug print to check if the token is correctly loaded
print("🛠️ DEBUG: DERIV_TOKEN =", DERIV_TOKEN)  # This will show the token value in your console
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print(f"🔍 RAW BODY RECEIVED: {data}")

        signal = data.get("signal")
        instrument = data.get("instrument")
        amount = data.get("amount", 1)
        durations = data.get("durations", [60])

        print(f"📬 Parsed JSON: {data}")
        print(f"✔️ Triggering {signal} for {instrument}...")

        for duration in durations:
            # Connect to Deriv WebSocket
            ws = create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089")

            # Authorize
            ws.send(json.dumps({"authorize": DERIV_TOKEN}))
            auth_response = json.loads(ws.recv())

            if "error" in auth_response:
                raise Exception(f"Authorization failed: {auth_response['error']['message']}")

            # Send contract request
            proposal = {
                "buy": 1,
                "price": amount,
                "parameters": {
                    "amount": amount,
                    "basis": "stake",
                    "contract_type": "CALL" if signal.upper() == "BUY" else "PUT",
                    "currency": "USD",
                    "duration": duration,
                    "duration_unit": "s",
                    "symbol": instrument,
                },
                "subscribe": 1
            }
            ws.send(json.dumps({"proposal": proposal["parameters"]}))
            proposal_response = json.loads(ws.recv())

            # Buy the contract
            ws.send(json.dumps({"buy": proposal_response["proposal"].get("id"), "price": amount}))
            buy_response = json.loads(ws.recv())

            print(f"📬 Deriv response: {buy_response}")
            ws.close()

        # Send Telegram Notification
        msg = f"🚨 Trade Executed\n<b>Signal:</b> <b>{signal}</b>\n<b>Pair:</b> <b>{instrument}</b>\n<b>Time:</b> <code>{data.get('timestamp', 'N/A')}</code>"
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        telegram_payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }
        tg_res = requests.post(telegram_url, json=telegram_payload)
        print(f"📲 Telegram alert sent: {tg_res.status_code} {tg_res.text}")

        return jsonify({"status": "success", "message": f"{signal} order for {instrument} sent"})

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/")
def index():
    return "FAST Webhook is running."

if __name__ == "__main__":
    app.run(debug=True, port=10000, host="0.0.0.0")
