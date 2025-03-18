import asyncio
import json
import websockets
import time

SIGNALING_SERVER = "ws://94.111.36.87:9000"  # Replace with your server IP

async def receive_messages():
    async with websockets.connect(SIGNALING_SERVER) as websocket:
        print(f"✅ Connected to Signaling Server: {SIGNALING_SERVER}")

        message_count = 0
        last_time = time.time()

        while True:
            message = await websocket.recv()
            message_count += 1  # ✅ Increment message count
            #print(f"📥 Received: {message}")

            # ✅ Calculate FPS (messages per second)
            current_time = time.time()
            elapsed_time = current_time - last_time

            if elapsed_time >= 1.0:
                print(f"⚡ FPS: {message_count} messages/sec")
                message_count = 0
                last_time = current_time

            # ✅ Send an ACK back to the sender
            #ack_message = json.dumps({"type": "ack", "data": "ACK"})
            #await websocket.send(ack_message)
            #print(f"📡 ACK sent: {ack_message}")

asyncio.run(receive_messages())
