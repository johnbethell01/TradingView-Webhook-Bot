from flask import Flask, request, jsonify
import json
import os
import requests

app = Flask(__name__)

DERIV_TOKEN = os.getenv("DERIV_TOKEN")
DERIV_API_URL = "https://api.deriv.com/websockets/v3"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        raw_data = request.data.decode("utf-8")
        print("🔍 RAW BODY RECEIVED:", raw_data)

        data = json.loads(raw_data)
        print("📩 Parsed JSON:", data)

        signal = data.get("signal")
        instrument = data.get("instrument")

        print(f"✔️ Triggering {signal} for {instrument}...")

        trade_payload = {
            "buy": 1,
            "price": 10,
            "parameters": {
                "contract_type": signal.upper(),   # BUY or SELL
                "symbol": instrument,
                "duration": 1,
                "duration_unit": "m",
                "amount": 10,
                "basis": "stake",
                "currency": "USD"
            },
            "req_id": 1
        }

        headers = {
            "Authorization": f"Bearer {DERIV_TOKEN}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            url="https://api.deriv.com/binary",
            headers=headers,
            json=trade_payload
        )

        print(f"📬 Deriv HTTP Status: {response.status_code}")
        print(f"🧾 Deriv Full Response: {response.text}")

        return jsonify({
            "status": "success",
            "message": {
                "result": f"{signal} order for {instrument} sent"
            }
        })

    except Exception as e:
        print("❌ ERROR sending trade:", str(e))
        return jsonify({
            "status": "error",
            "message": {
                "error": str(e)
            }
        })

if __name__ == "__main__":
    app.run()
