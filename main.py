import os
import json
import asyncio
import websockets
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

DERIV_APP_ID = os.getenv("DERIV_APP_ID")
FAST_AUTOTRADE = os.getenv("FAST_AUTOTRADE")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WEBSOCKET_URL = "wss://ws.deriv.com/websockets/v3?app_id=" + DERIV_APP_ID


@app.get("/ping")
async def ping():
    return {"status": "✅ main.py v2.2.1 running", "websocket_url": WEBSOCKET_URL}


@app.post("/webhook")
async def receive_signal(request: Request):
    payload = await request.json()
    print(f"📩 Webhook received: {payload}")

    signal = payload.get("signal")
    instrument = payload.get("instrument")
    amount = payload.get("amount", 1)
    durations = payload.get("durations", [60])
    score_tag = payload.get("score_tag", "UNRATED")

    if not signal or not instrument:
        return {"error": "Missing required fields: signal, instrument"}

    for duration in durations:
        await execute_trade(signal, instrument, amount, duration, score_tag)

    return {"status": "✅ Signal processed"}


async def execute_trade(signal, instrument, amount, duration, score_tag):
    contract_type = "CALL" if signal.upper() == "BUY" else "PUT"

    # ✅ Flattened payload with proposal: 1 at root level
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

    try:
        async with websockets.connect(WEBSOCKET_URL) as ws:
            # Authenticate with FAST_AUTOTRADE token
            await ws.send(json.dumps({
                "authorize": FAST_AUTOTRADE
            }))
            auth_response = await ws.recv()
            print(f"🔐 Auth response: {auth_response}")

            # Send trade proposal
            await ws.send(json.dumps(proposal_payload))
            proposal_response = await ws.recv()
            print(f"📥 Proposal Response: {proposal_response}")

            # Send Telegram alert
            await send_telegram_alert(
                f"📊 Signal: {signal} | {instrument} | {duration}s\n💵 Amount: ${amount}\n🏷️ Score: {score_tag}\n📬 Proposal Response: {proposal_response}"
            )

    except Exception as e:
        print(f"❌ ERROR: {e}")
        await send_telegram_alert(f"❌ ERROR during trade execution:\n{e}")


async def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            print(f"📤 Telegram status: {response.status_code} | {response.text}")
    except Exception as e:
        print(f"❌ Telegram send error: {e}")
