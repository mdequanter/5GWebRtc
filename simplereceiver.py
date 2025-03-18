import asyncio
import websockets

SIGNALING_SERVER = "ws://94.111.36.87:9000"  # Vervang door jouw server-IP

async def receive_messages():
    async with websockets.connect(SIGNALING_SERVER) as websocket:
        print(f"✅ Verbonden met Signaling Server: {SIGNALING_SERVER}")

        while True:
            message = await websocket.recv()
            print(f"📥 Ontvangen: {message}")

asyncio.run(receive_messages())
