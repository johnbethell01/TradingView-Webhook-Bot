# main.py v2.1 (FIXED Deriv Auth with websocket-client)
import os
import json
from flask import Flask, request, jsonify
import requests
from websocket import create_connection

app = Flask(__name__)

# ENV VARIABLES
DERIV_TOKEN = os.getenv("FAST_AUTOTRADE")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Debug log for token load
print("🛠️ DEBUG: DERIV_TOKEN =", DERIV_TOKEN)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print(f"\U0001F50D RAW BODY RECEIVED: {data}")

        signal = data.get("signal")
        instrument = data.get("instrument")
        amount = data.get("amount", 1)
        durations = data.get("durations", [60])

        print(f"\U0001F4EC Parsed JSON: {data}")
        print(f"\u2714\ufe0f Triggering {signal} for {instrument}...")

        for duration in durations:
            # Connect to Deriv
            ws = create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089")
            
            # Authorize
            ws.send(json.dumps({"authorize": DERIV_TOKEN}))
            auth_res = json.loads(ws.recv())
            if "error" in auth_res:
                raise Exception(f"Authorization failed: {auth_res['error']['message']}")

            # Build proposal
            contract_type = "CALL" if signal.upper() == "BUY" else "PUT"
            proposal = {
                "amount": float(amount),
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": int(duration),
                "duration_unit": "s",
                "symbol": instrument
            }

            # Request proposal
            ws.send(json.dumps({"proposal": proposal}))
            proposal_res = json.loads(ws.recv())
            if "error" in proposal_res:
                raise Exception(f"Proposal failed: {proposal_res['error']['message']}")
            proposal_id = proposal_res["proposal"]["id"]

            # Execute contract
            ws.send(json.dumps({"buy": proposal_id, "price": float(amount)}))
            buy_res = json.loads(ws.recv())
            print(f"\U0001F4E6 Deriv response: {buy_res}")
            ws.close()

        # Send Telegram message
        msg = f"\ud83d\udea8 Trade Executed\n<b>Signal:</b> <b>{signal}</b>\n<b>Pair:</b> <b>{instrument}</b>\n<b>Time:</b> <code>{data.get('timestamp', 'N/A')}</code>"
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        telegram_payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }
        tg = requests.post(telegram_url, json=telegram_payload)
        print(f"\U0001F4F2 Telegram alert sent: {tg.status_code} {tg.text}")

        return jsonify({"status": "success", "message": f"{signal} order for {instrument} sent"})

    except Exception as e:
        print(f"\u274c ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/")
def index():
    return "FAST Webhook v2.1 is running."

if __name__ == "__main__":
    app.run(debug=True, port=10000, host="0.0.0.0")
