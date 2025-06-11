import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

DERIV_TOKEN = os.getenv("FAST_AUTOTRADE")  # ← USE THIS TOKEN
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_CHAT_ID")
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "10")
TRADE_DURATION = os.getenv("TRADE_DURATION", "1")

@app.route("/", methods=["GET"])
def index():
    return "Webhook is live."

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print("🔍 RAW BODY RECEIVED:", data)

        signal = data.get('signal')
        instrument = data.get('instrument')

        print("📩 Parsed JSON:", {"signal": signal, "instrument": instrument})

        if signal and instrument:
            print(f"✔️ Triggering {signal} for {instrument}...")
            # TEMP PLACEHOLDER for Deriv trade
            deriv_response = {"status": 405}
            print("🧾 Deriv response placeholder:", deriv_response)

            # Telegram Alert
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            message = (
                f"🚨 *Trade Executed*\n"
                f"*Signal:* {signal}\n"
                f"*Pair:* {instrument}\n"
                f"*Time:* `{timestamp}`"
            )

            tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            tg_data = {
                "chat_id": TELEGRAM_USER_ID,
                "text": message,
                "parse_mode": "Markdown"
            }

            tg_response = requests.post(tg_url, json=tg_data)
            print("📲 Telegram alert sent:", tg_response.status_code, tg_response.text)

            return jsonify({"status": "success", "message": {"result": f"{signal} order for {instrument} sent"}}), 200
        else:
            return jsonify({"status": "error", "message": "Missing signal or instrument"}), 400

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
