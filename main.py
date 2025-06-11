import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# === ENV Vars ===
DERIV_TOKEN = os.environ.get("FAST_AUTOTRADE")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        print("📥 Incoming webhook received...")
        data = request.get_json(force=True)
        print("🔍 RAW BODY:", data)

        signal = data.get("signal")
        instrument = data.get("instrument")

        if not signal or not instrument:
            raise ValueError("Missing signal or instrument")

        print(f"📩 Parsed: signal={signal}, instrument={instrument}")

        # === Send Trade to Deriv ===
        ws_url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
        print("🌐 Connecting to Deriv...")

        import websocket
        import threading
        import time

        def send_order():
            ws = websocket.WebSocket()
            ws.connect(ws_url)

            # Authorize
            ws.send(json.dumps({"authorize": DERIV_TOKEN}))
            auth_response = ws.recv()
            print("🔑 Auth Response:", auth_response)

            # Place Order
            proposal = {
                "buy": "1",
                "price": 1,
                "parameters": {
                    "amount": 1,
                    "basis": "stake",
                    "contract_type": "CALL" if signal == "BUY" else "PUT",
                    "currency": "USD",
                    "duration": 60,
                    "duration_unit": "s",
                    "symbol": instrument
                }
            }
            ws.send(json.dumps(proposal))
            result = ws.recv()
            print("🧾 Deriv Response:", result)
            ws.close()

        threading.Thread(target=send_order).start()

        # === Send Telegram Message ===
        telegram_msg = f"🚨 Trade Executed\n<b>Signal:</b> {signal}\n<b>Pair:</b> {instrument}\n<code>{request.headers.get('Date')}</code>"
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(telegram_url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": telegram_msg,
            "parse_mode": "HTML"
        })

        print("📲 Telegram Status:", response.status_code, response.text)

        return jsonify({"message": {"result": f"{signal} order for {instrument} sent"}, "status": "success"})

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({"message": {"error": str(e)}, "status": "error"}), 500
