import asyncio
import json
import random
import websockets

SIGNALING_SERVER = "ws://94.111.36.87:9000"  # Vervang door jouw server-IP

async def send_messages():
    async with websockets.connect(SIGNALING_SERVER) as websocket:
        print(f"✅ Verbonden met Signaling Server: {SIGNALING_SERVER}")

        counter = 0
        while True:
            message = {
                "type": "test",
                "data": f"Willekeurig bericht {counter} - {random.randint(1000, 9999)}"
            }
            await websocket.send(json.dumps(message))
            print(f"📡 Verzonden: {message}")
            counter += 1
            await asyncio.sleep(2)  # Wacht 2 seconden voor het volgende bericht

asyncio.run(send_messages())
