from flask import Flask, request, jsonify
import json
import os
import requests
from datetime import datetime

app = Flask(__name__)

# ENV VARS
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        raw_data = request.data.decode("utf-8")
        print("🔍 RAW BODY RECEIVED:", raw_data)

        data = json.loads(raw_data)
        print("📩 Parsed JSON:", data)

        signal = data.get("signal")
        instrument = data.get("instrument")
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        print(f"✔️ Triggering {signal} for {instrument}...")

        # Prepare trade payload
        trade_payload = {
            "buy": 1,
            "price": 10,
            "parameters": {
                "contract_type": signal.upper(),
                "symbol": instrument,
                "duration": 1,
                "duration_unit": "m",
                "amount": 10,
                "basis": "stake",
                "currency": "USD"
            },
            "req_id": 1
        }

        deriv_headers = {
            "Authorization": f"Bearer {DERIV_TOKEN}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            url="https://api.deriv.com/binary",
            headers=deriv_headers,
            json=trade_payload
        )

        print(f"📬 Deriv HTTP Status: {response.status_code}")
        print(f"🧾 Deriv Full Response: {response.text}")

        # Send Telegram message
        telegram_msg = (
            f"🚨 Trade Executed\n"
            f"Signal: *{signal.upper()}*\n"
            f"Pair: *{instrument}*\n"
            f"Time: `{timestamp} UTC`"
        )

        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        tg_payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": telegram_msg,
            "parse_mode": "Markdown"
        }

        tg_response = requests.post(tg_url, json=tg_payload)
        print("📲 Telegram alert sent:", tg_response.status_code, tg_response.text)

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
