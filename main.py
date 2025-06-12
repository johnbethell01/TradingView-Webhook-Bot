import os
import asyncio
import json
from fastapi import FastAPI, Request
import httpx
import websockets

app = FastAPI()

# Load env vars
DERIV_TOKEN = os.getenv("FAST_AUTOTRADE")
DERIV_APP_ID = os.getenv("DERIV_APP_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WEBSOCKET_URL = f"wss://ws.deriv.com/websockets/v3?app_id={DERIV_APP_ID}"

@app.get("/ping")
async def ping():
    return {
        "status": "✅ main.py v2.2.2 running",
        "websocket_url": WEBSOCKET_URL,
    }

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("📩 Webhook received:", data)

    signal = data.get("signal")
    instrument = data.get("instrument")
    amount = data.get("amount", 1)
    durations = data.get("durations", [60])
    score_tag = data.get("score_tag", "N/A")

    if not all([signal, instrument, amount]):
        return {"error": "Missing required fields"}

    for duration in durations:
        asyncio.create_task(
            execute_trade(signal, instrument, amount, duration, score_tag)
        )

    return {"status": "OK", "message": "Trade tasks started"}

async def execute_trade(signal, instrument, amount, duration, score_tag):
    print(f"✔️ Triggering {signal} for {instrument} at duration {duration}s")

    try:
        async with websockets.connect(WEBSOCKET_URL) as ws:
            # Authenticate
            auth_payload = {"authorize": DERIV_TOKEN}
            await ws.send(json.dumps(auth_payload))
            auth_response = await ws.recv()
            print("🔐 Auth response:", json.loads(auth_response))

            contract_type = "CALL" if signal == "BUY" else "PUT"

            # Flattened proposal payload
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

            await ws.send(json.dumps(proposal_payload))
            proposal_response = await ws.recv()
            print("📥 Proposal Response:", json.loads(proposal_response))

            await send_telegram_alert(signal, instrument, amount, duration, score_tag, proposal_response)

    except Exception as e:
        print(f"❌ ERROR: {e}")

async def send_telegram_alert(signal, instrument, amount, duration, score_tag, proposal_response):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return

    message = (
        f"🚨 *FAST TRADE ALERT*\n"
        f"*Signal:* {signal}\n"
        f"*Instrument:* {instrument}\n"
        f"*Amount:* ${amount}\n"
        f"*Duration:* {duration}s\n"
        f"*Score:* {score_tag}\n\n"
        f"*Proposal Response:*\n```{json.dumps(json.loads(proposal_response), indent=2)}```"
    )

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(telegram_url, json=payload)
            print(f"📤 Telegram status: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Telegram send error: {e}")
