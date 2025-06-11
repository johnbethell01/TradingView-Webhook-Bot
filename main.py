import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Environment variables
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DERIV_API_URL = "https://api.deriv.com/binary"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        raw_data = request.data.decode("utf-8")
        print(f"🔍 RAW BODY RECEIVED: {raw_data}")

        data = request.get_json(force=True)
        print(f"📩 Parsed JSON: {data}")

        signal = data.get("signal")
        instrument = data.get("instrument", "frxBTCUSD").strip()

        if not signal or not instrument:
            return jsonify({"status": "error", "message": "Missing signal or instrument"}), 400

        print(f"✔️ Triggering {signal} for {instrument}...")

        if signal.upper() == "BUY":
            contract_type = "CALL"
        elif signal.upper() == "SELL":
            contract_type = "PUT"
        else:
            return jsonify({"status": "error", "message": "Invalid signal type"}), 400

        deriv_payload = {
            "buy": 1,
            "price": 1,
            "parameters": {
                "amount": 1,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": 1,
                "duration_unit": "m",
                "symbol": instrument
            },
            "passthrough": {},
            "req_id": 1
        }

        headers = {
            "Authorization": f"Bearer {DERIV_TOKEN}",
            "Content-Type": "application/json"
        }

        deriv_response = requests.post(DERIV_API_URL, json=deriv_payload, headers=headers)
        print(f"📬 Deriv HTTP Status: {deriv_response.status_code}")
        print(f"🧾 Deriv Full Response: {deriv_response.text}")

        # Telegram notification
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            telegram_message = (
                f"🚨 <b>Trade Executed</b>\n"
                f"<b>Signal:</b> {signal.upper()}\n"
                f"<b>Pair:</b> {instrument}\n"
                f"<code>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</code>"
            )
            telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            telegram_data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": telegram_message,
                "parse_mode": "HTML"
            }
            tg_resp = requests.post(telegram_url, json=telegram_data)
            print(f"📲 Telegram alert sent: {tg_resp.status_code} {tg_resp.text}")

        return jsonify({"status": "success", "message": {"result": f"{signal.upper()} order for {instrument} sent"}})

    except Exception as e:
        print(f"❌ ERROR sending trade: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
