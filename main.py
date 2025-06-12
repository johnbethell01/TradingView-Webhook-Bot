import os
import json
import asyncio
from fastapi import FastAPI, Request
import websockets

app = FastAPI()

# ENV VARS
DERIV_TOKEN = os.getenv("FAST_AUTOTRADE")
DERIV_APP_ID = os.getenv("DERIV_APP_ID")
WEBSOCKET_URL = f"wss://ws.deriv.com/websockets/v3?app_id={DERIV_APP_ID}"

# 🟢 Root endpoint to prevent Render shutdown on GET /
@app.get("/")
async def root():
    return {"status": "✅ Service alive at root /"}

# 🟢 Ping endpoint for health checks
@app.get("/ping")
async def ping():
    return {"status": "✅ v2.2.4 live", "websocket_url": WEBSOCKET_URL}

# 🟢 Webhook to receive alerts
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        print("📩 Webhook received:", data)

        signal = data.get("signal")
        instrument = data.get("instrument")
        amount = data.get("amount", 1)
        durations = data.get("durations", [60])
        score_tag = data.get("score_tag", "N/A")

        if not all([signal, instrument, amount]):
            return {"error": "Missing fields in webhook"}

        for d in durations:
            print(f"⏳ Starting trade task: {signal} {instrument} {d}s")
            await execute_trade(signal, instrument, amount, d, score_tag)

        return {"status": "✅ Webhook handled", "durations": durations}

    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"error": str(e)}

# 🟢 Core trade execution logic
async def execute_trade(signal, instrument, amount, duration, score_tag):
    try:
        print(f"🚀 Executing {signal.upper()} on {instrument} for {duration}s")

        async with websockets.connect(WEBSOCKET_URL) as ws:
            # Step 1: Authenticate
            auth_payload = {"authorize": DERIV_TOKEN}
            await ws.send(json.dumps(auth_payload))
            auth_response = await ws.recv()
            print("🔐 Auth Response:", json.loads(auth_response))

            # Step 2: Proposal payload
            contract_type = "CALL" if signal.upper() == "BUY" else "PUT"
            proposal_payload = {
                "proposal": 1,
                "amount": amount,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": duration,
                "duration_unit": "s",
                "symbol": instrument
            }

            print("📤 Sending Proposal:", proposal_payload)
            await ws.send(json.dumps(proposal_payload))
            proposal_response = await ws.recv()
            print("📥 Proposal Response:", json.loads(proposal_response))

    except Exception as e:
        print(f"❌ Trade execution error @ {duration}s: {e}")
