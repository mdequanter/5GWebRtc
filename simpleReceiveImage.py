import asyncio
import json
import websockets
import time
import cv2
import numpy as np
import base64
import sys


SIGNALING_SERVER = "ws://heliwi.duckdns.org:9000"  # Vervang door je server IP
if len(sys.argv) > 1:
    SIGNALING_SERVER = sys.argv[1]



TARGET_WIDTH, TARGET_HEIGHT = 640, 480  # Ensure consistent display size

async def receive_messages():
    async with websockets.connect(SIGNALING_SERVER) as websocket:
        print(f"✅ Connected to Signaling Server: {SIGNALING_SERVER}")

        message_count = 0
        last_time = time.time()
        fps_display = 0  # Variable to store the latest FPS value

        while True:
            message = await websocket.recv()
            message_json = json.loads(message)  # Parse JSON data
            #print (message_json)  # Uncomment to debug received JSON

            image_data = base64.b64decode(message_json["data"])
            np_arr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            # ✅ Ensure the image is always 640x480
            if frame is not None:
                frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))

            # ✅ FPS calculation
            message_count += 1
            current_time = time.time()
            elapsed_time = current_time - last_time

            if elapsed_time >= 1.0:
                fps_display = message_count  # Store FPS value to display on frame
                #print(f"⚡ FPS: {fps_display} images/sec")
                message_count = 0
                last_time = current_time

            # ✅ Overlay FPS text on the frame
            if frame is not None:
                fps_text = f"FPS on receiver: {fps_display}"
                cv2.putText(frame, fps_text, (10, 470), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2, cv2.LINE_AA)

                # Show the frame with FPS overlay
                cv2.imshow("Received Image", frame)
                cv2.waitKey(1)  # Required for OpenCV updates

asyncio.run(receive_messages())
