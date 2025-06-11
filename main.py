from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Log raw data received
        raw_data = request.data.decode("utf-8")
        print("🔍 RAW BODY RECEIVED:", raw_data)

        # Parse JSON
        data = json.loads(raw_data)
        print("📩 Parsed JSON:", data)

        # Extract signal and instrument
        signal = data.get("signal")
        instrument = data.get("instrument")

        print(f"✔️ Triggering {signal} for {instrument}...")

        # Respond with simulated success
        return jsonify({
            "status": "success",
            "message": {
                "result": f"{signal} order for {instrument} sent"
            }
        })

    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({
            "status": "success",
            "message": {
                "error": str(e)
            }
        })

if __name__ == "__main__":
    app.run()
