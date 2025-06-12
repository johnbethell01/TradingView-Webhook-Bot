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

@app.get("/ping")
async def ping():
    return {"status": "✅ v2.2.3-dev live", "websocket": WEBSOCKET_URL}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        print("📩 Webhook Data:", data)

        signal = data.get("signal")
        instrument = data.get("instrument")
        amount = data.get("amount", 1)
        durations = data.get("durations", [60])
        score_tag = data.get("score_tag", "N/A")

        if not all([signal, instrument, amount]):
            return {"error": "Missing fields"}

        for d in durations:
            print(f"⏳ Starting trade task: {signal} {instrument} {d}s")
            await execute_trade(signal, instrument, amount, d, score_tag)

        return {"status": "✅ webhook handled"}

    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"error": str(e)}

async def execute_trade(signal, instrument, amount, duration, score_tag):
    try:
        print(f"🚀 Executing {signal} @ {instrument} for {duration}s...")

        async with websockets.connect(WEBSOCKET_URL) as ws:
            # 1. Auth
            auth_payload = {"authorize": DERIV_TOKEN}
            await ws.send(json.dumps(auth_payload))
            auth_response = await ws.recv()
            print("🔐 Auth:", json.loads(auth_response))

            # 2. Proposal
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
        print(f"❌ Trade error @ {duration}s: {e}")
