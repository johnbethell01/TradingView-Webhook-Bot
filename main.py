from flask import Flask, request, jsonify
import os
import requests
from datetime import datetime

app = Flask(__name__)

# Get secrets from Render environment variables
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ✅ Logging helper
def log(message):
    print(message, flush=True)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        log("📡 Webhook received")
        data = request.get_json(force=True)
        log(f"🔍 RAW BODY RECEIVED: {data}")

        signal = data.get("signal")
        instrument = data.get("instrument")
        amount = data.get("amount", 1)  # optional
        duration = data.get("duration", 1)  # optional

        if signal not in ["BUY", "SELL"] or not instrument:
            log("❌ Invalid or missing signal/instrument")
            return jsonify({"status": "error", "message": "Invalid signal or instrument"}), 400

        log(f"📩 Parsed JSON: {data}")
        log(f"✔️ Triggering {signal} for {instrument}...")

        # Send to Deriv
        deriv_url = "https://api.deriv.com/binary/v1/new_trade"
        deriv_payload = {
            "signal": signal,
            "instrument": instrument,
            "amount": amount,
            "duration": duration,
            "token": DERIV_TOKEN,
        }
        deriv_response = requests.post(deriv_url, json=deriv_payload)
        log(f"📬 Deriv HTTP Status: {deriv_response.status_code}")
        log(f"🧾 Deriv Full Response: {deriv_response.text}")

        # Send to Telegram
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        telegram_message = f"🚨 *Trade Executed*\n*Signal:* {signal}\n*Pair:* {instrument}\n*Time:* `{now}`"
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        telegram_payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": telegram_message,
            "parse_mode": "Markdown"
        }
        telegram_response = requests.post(telegram_url, json=telegram_payload)
        log(f"📲 Telegram alert sent: {telegram_response.status_code} {telegram_response.text}")

        return jsonify({"status": "success", "message": {"result": f"{signal} order for {instrument} sent"}})

    except Exception as e:
        log(f"🔥 Exception: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
