from fastapi import FastAPI, Request
from pydantic import BaseModel
import asyncio
import websockets
import json
import os
import httpx

app = FastAPI()

# ENV Variables
DERIV_API_TOKEN = os.getenv("FAST_AUTOTRADE")  # ✅ Correct var name
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBSOCKET_URL = "wss://ws.deriv.com/websockets/v3?app_id=24180"

class WebhookData(BaseModel):
    signal: str
    instrument: str
    amount: float
    durations: list[int]
    score_tag: str = None

async def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"❌ Telegram error: {e}")

async def execute_trade(signal: str, symbol: str, amount: float, duration: int):
    print(f"🚀 Executing {signal.upper()} on {symbol} for {duration}s")
    try:
        async with websockets.connect(WEBSOCKET_URL) as ws:
            # Authorize
            await ws.send(json.dumps({"authorize": DERIV_API_TOKEN}))
            auth_response = await ws.recv()
            print("🔐 Auth Response:", auth_response)

            # Build contract type
            contract_type = "CALL" if signal.upper() == "BUY" else "PUT"

            # Send Proposal
            await ws.send(json.dumps({
                "proposal": 1,
                "amount": amount,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": duration,
                "duration_unit": "s",
                "symbol": symbol
            }))
            proposal_response = await ws.recv()
            print("📥 Proposal Response:", proposal_response)

            # Buy if valid
            proposal = json.loads(proposal_response)
            if "error" in proposal:
                await send_telegram(f"❌ Trade error @ {duration}s: {proposal['error']['message']}")
                return

            proposal_id = proposal["proposal"]["id"]
            await ws.send(json.dumps({"buy": proposal_id, "price": amount}))
            buy_response = await ws.recv()
            print("✅ Buy Response:", buy_response)
            await send_telegram(f"✅ Trade executed: {signal} {symbol} {duration}s")

    except Exception as e:
        print(f"❌ Trade execution error @ {duration}s: {e}")
        await send_telegram(f"❌ Trade execution error @ {duration}s: {e}")

@app.post("/webhook")
async def webhook(data: WebhookData):
    print("📩 Webhook received:", data.dict())
    tasks = [
        execute_trade(data.signal, data.instrument, data.amount, d)
        for d in data.durations
    ]
    await asyncio.gather(*tasks)
    return {"status": "✅ Webhook handled", "durations": data.durations}

@app.get("/ping")
def ping():
    return {"status": "✅ FAST Webhook Bot is alive"}
