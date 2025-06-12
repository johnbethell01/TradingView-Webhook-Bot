from fastapi import FastAPI, Request
from pydantic import BaseModel
import asyncio
import websockets
import json
import os
import time
import httpx

app = FastAPI()

# Load environment variables
DERIV_API_TOKEN = os.getenv("FAST_AUTOTRADE")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBSOCKET_URL = "wss://ws.deriv.com/websockets/v3?app_id=24180"

class SignalRequest(BaseModel):
    signal: str
    instrument: str
    amount: float
    durations: list[int]
    score_tag: str = None

async def send_telegram_message(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"Telegram send error: {e}")

async def execute_trade(signal: str, instrument: str, amount: float, duration: int):
    print(f"🚀 Executing {signal.upper()} on {instrument} for {duration}s")
    try:
        async with websockets.connect(WEBSOCKET_URL) as ws:
            # Authorize
            await ws.send(json.dumps({"authorize": DERIV_API_TOKEN}))
            auth_response = await ws.recv()
            print(f"🔐 Auth Response: {auth_response}")

            # Choose contract type
            contract_type = "CALL" if signal.upper() == "BUY" else "PUT"

            # Request proposal
            await ws.send(json.dumps({
                "proposal": 1,
                "amount": amount,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": duration,
                "duration_unit": "s",
                "symbol": instrument,
                "product_type": "basic"
            }))
            proposal_response = await ws.recv()
            print(f"📥 Proposal Response: {proposal_response}")
            proposal_data = json.loads(proposal_response)

            if "error" in proposal_data:
                raise Exception(proposal_data["error"]["message"])

            proposal_id = proposal_data["proposal"]["id"]

            # Purchase contract
            await ws.send(json.dumps({
                "buy": proposal_id,
                "price": amount
            }))
            buy_response = await ws.recv()
            print(f"💰 Purchase Response: {buy_response}")

            await send_telegram_message(
                f"✅ Trade executed: {signal.upper()} {instrument} for {duration}s"
            )

    except Exception as e:
        print(f"❌ Trade execution error @ {duration}s: {e}")
        await send_telegram_message(
            f"❌ Trade error for {signal.upper()} {instrument} {duration}s: {e}"
        )

@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    print(f"📩 Webhook received: {data}")
    try:
        payload = SignalRequest(**data)
        tasks = [
            execute_trade(payload.signal, payload.instrument, payload.amount, d)
            for d in payload.durations
        ]
        await asyncio.gather(*tasks)
        return {"status": "✅ Webhook handled", "durations": payload.durations}
    except Exception as e:
        print(f"❌ Webhook processing error: {str(e)}")
        return {"status": "❌ Error", "message": str(e)}

@app.get("/")
async def root():
    return {
        "status": "✅ main.py v2.3 running",
        "websocket_url": WEBSOCKET_URL
    }

@app.get("/ping")
async def ping():
    return {"status": "pong", "version": "v2.3"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
