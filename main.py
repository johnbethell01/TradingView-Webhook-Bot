import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    signal = data.get('signal')
    instrument = data.get('instrument')

    if signal and instrument:
        response = execute_trade(signal, instrument)
        return jsonify({"status": "success", "message": response}), 200
    else:
        return jsonify({"status": "error", "message": "Invalid data received"}), 400

def execute_trade(signal, instrument):
    token = os.getenv("DERIV_TOKEN")
    amount = os.getenv("TRADE_AMOUNT")
    duration = os.getenv("TRADE_DURATION")

    endpoint = "https://api.deriv.com/binary"
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "buy": "1",
        "price": amount,
        "parameters": {
            "amount": amount,
            "basis": "stake",
            "contract_type": "CALL" if signal == "BUY" else "PUT",
            "currency": "USD",
            "duration": duration,
            "duration_unit": "m",
            "symbol": instrument
        }
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers)
        print(f"✔️ Sent {signal} trade to Deriv for {instrument}")
        print("📦 Payload:", payload)
        print("🧾 Deriv response:", response.text)
        return response.json()
    except Exception as e:
        print("❌ ERROR sending trade:", str(e))
        return {"error": str(e)}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
