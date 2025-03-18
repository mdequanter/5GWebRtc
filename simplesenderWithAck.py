import asyncio
import json
import random
import websockets
import time

SIGNALING_SERVER = "ws://94.111.36.87:9000"  # Vervang door jouw server-IP


import cv2
import base64

# Load the image from disk
image_path = "random_image.jpg"  # Change to your image file path
image = cv2.imread(image_path)

# Encode the image as a JPG in memory
_, buffer = cv2.imencode(".jpg", image)

# Convert to base64
encoded_string = base64.b64encode(buffer).decode("utf-8")


async def send_messages():
    async with websockets.connect(SIGNALING_SERVER) as websocket:
        print(f"✅ Verbonden met Signaling Server: {SIGNALING_SERVER}")

        counter = 0
        while True:
            message = {
                "type": "test",
                "data": f"{encoded_string}"
            }
            
            # ✅ Start de tijdmeting voordat het bericht wordt verstuurd
            start_time = time.time()
            await websocket.send(json.dumps(message))
            #print(f"📡 Verzonden: {message}")

            # ✅ Wacht op een ACK van de receiver
            #ack = await websocket.recv()

            # ✅ Bereken de latency in milliseconden
            #end_time = time.time()
            #latency_ms = (end_time - start_time) * 1000  # Omgerekend naar ms
            
            #print(f"📥 ACK ontvangen: {ack} | 🕒 Latency: {latency_ms/2:.2f} ms")

            counter += 1
            await asyncio.sleep(0.05)  # Wacht 2 seconden voor het volgende bericht

asyncio.run(send_messages())
