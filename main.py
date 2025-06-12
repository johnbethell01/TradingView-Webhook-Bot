import os
import json
import asyncio
import websockets
import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List

# Environment variables
DERIV_TOKEN = os.getenv("FAST_AUTOTRADE")
DERIV_APP_ID = os.getenv("DERIV_APP_ID", "24180")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBSOCKET_URL = f"wss://ws.deriv.com/websockets/v3?app_id={DERIV_APP_ID}"

app = FastAPI()

class SignalRequest(BaseModel):
    signal: str
    instrument: str
    amount: float
    durations: List[int]
    score_tag: str = "FAST-SIGNAL"

async def send_telegram_message(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                print(f"⚠️ Telegram failed: {response.text}")
    except Exception as e:
        print(f"⚠️ Telegram error: {str(e)}")

async def execute_trade(signal: str, instrument: str, amount: float, duration: int):
    print(f"🚀 Executing {signal.upper()} on {instrument} for {duration}s")
    try:
        async with websockets.connect(WEBSOCKET_URL) as ws:
            await ws.send(json.dumps({"authorize": DERIV_TOKEN}))
            auth_response = await ws.recv()
            print(f"🔐 Auth Response: {auth_response}")

            contract_type = "CALL" if signal.upper() == "BUY" else "PUT"
            proposal = {
                "proposal": 1,
                "amount": amount,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": duration,
                "duration_unit": "s",
                "symbol": instrument
            }
            print(f"📤 Sending Proposal: {proposal}")
            await ws.send(json.dumps(proposal))
            proposal_response = await ws.recv()
            print(f"📥 Proposal Response: {proposal_response}")

            parsed = json.loads(proposal_response)
            if "proposal" in parsed and "id" in parsed["proposal"]:
                contract_id = parsed["proposal"]["id"]
                buy_payload = {
                    "buy": contract_id,
                    "price": amount
                }
                print(f"🟢 Placing Order: {buy_payload}")
                await ws.send(json.dumps(buy_payload))
                buy_response = await ws.recv()
                print(f"✅ Buy Response: {buy_response}")
                await send_telegram_message(f"✅ Order placed: {buy_response}")
            else:
                error_msg = parsed.get("error", {}).get("message", "Unknown proposal error")
                print(f"❌ Proposal error: {error_msg}")
                await send_telegram_message(f"❌ Proposal error: {error_msg}")
    except Exception as e:
        print(f"❌ Trade execution error @ {duration}s: {str(e)}")
        await send_telegram_message(f"❌ Trade execution error @ {duration}s: {str(e)}")

@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    print(f"📩 Webhook received: {data}")
    try:
        payload = SignalRequest(**data)
        tasks = [execute_trade(payload.signal, payload.instrument, payload.amount, d) for d in payload.durations]
        await asyncio.gather(*tasks)
        return {"status": "✅ Webhook handled", "durations": payload.durations}
    except Exception as e:
        print(f"❌ Webhook processing error: {str(e)}")
        return {"status": "❌ Error", "message": str(e)}

@app.get("/")
async def root():
    return {"status": "✅ main.py v2.3 running", "websocket_url": WEBSOCKET_URL}

@app.get("/ping")
async def ping():
    return {"status": "pong", "version": "v2.3"}
    
    if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

