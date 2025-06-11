import os
import json
from flask import Flask, request, jsonify
import requests
from websocket import create_connection

app = Flask(__name__)

# === ENVIRONMENT VARIABLES ===
DERIV_TOKEN = os.getenv("FAST_AUTOTRADE")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === DEBUG ===
print("🛠️ DEBUG: DERIV_TOKEN =", DERIV_TOKEN)

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
            # === CONNECT TO DERIV ===
            ws = create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089")

            # === AUTHORIZE ===
            auth_payload = {"authorize": DERIV_TOKEN}
            print("📤 Sending Auth Payload to Deriv:", auth_payload)

            ws.send(json.dumps(auth_payload))
            auth_response = json.loads(ws.recv())
            print("📥 Auth Response:", auth_response)

            if "error" in auth_response:
                raise Exception(f"Authorization failed: {auth_response['error']['message']}")

            # === BUILD PROPOSAL ===
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

            ws.send(json.dumps({"proposal": proposal}))
            proposal_response = json.loads(ws.recv())
            print("📥 Proposal Response:", proposal_response)

            if "error" in proposal_response:
                raise Exception(f"Proposal failed: {proposal_response['error']['message']}")

            # === BUY CONTRACT ===
            proposal_id = proposal_response["proposal"]["id"]
            ws.send(json.dumps({"buy": proposal_id, "price": float(amount)}))
            buy_response = json.loads(ws.recv())
            print("✅ Buy Response:", buy_response)

            ws.close()

        # === TELEGRAM NOTIFY ===
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
