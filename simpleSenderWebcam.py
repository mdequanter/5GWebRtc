import asyncio
import json
import websockets
import time
import cv2
import base64
import io
from PIL import Image

SIGNALING_SERVER = "ws://94.111.36.87:9000"  # Replace with your server IP

# Define JPEG quality level (adjustable)
JPEG_QUALITY = 90  # Adjust as needed (100 = best quality, 50 = balanced, 25 = max compression)

# Open the camera (0 is usually the default webcam)
capture = cv2.VideoCapture(0)
width = 640
height = 480

async def send_messages():
    async with websockets.connect(SIGNALING_SERVER) as websocket:
        print(f"✅ Connected to Signaling Server: {SIGNALING_SERVER}")
        
        while True:
            ret, frame = capture.read()
            if not ret:
                print("❌ Could not retrieve frame from the camera")
                continue

            # Resize to 640x480 pixels
            frame = cv2.resize(frame, (width, height))

            # Get timestamp
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

            # Convert OpenCV frame (with text) to PIL Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
            pil_image = Image.fromarray(frame_rgb)

            # Compress using Pillow to in-memory JPEG
            compressed_image_io = io.BytesIO()
            start_time = time.time()
            pil_image.save(compressed_image_io, format="JPEG", quality=JPEG_QUALITY)
            end_time = time.time()

            # Get compressed image bytes
            compressed_bytes = compressed_image_io.getvalue()
            compressed_size_kb = len(compressed_bytes) / 1024  # Convert to KB
            compression_time_ms = (end_time - start_time) * 1000  # Convert to milliseconds

            # Overlay metadata on the frame **BEFORE COMPRESSION**
            cv2.putText(frame, f"Time: {timestamp}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Resolution: {width}x{height}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Size: {round(compressed_size_kb, 2)} KB", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Comp. Time/Quality: {round(compression_time_ms, 2)} ms / {JPEG_QUALITY}%", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Convert annotated OpenCV frame to Pillow image again
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            # Recompress the frame (with text overlay) using Pillow
            final_compressed_image_io = io.BytesIO()
            pil_image.save(final_compressed_image_io, format="JPEG", quality=JPEG_QUALITY)
            final_compressed_bytes = final_compressed_image_io.getvalue()

            # Convert to base64
            encoded_string = base64.b64encode(final_compressed_bytes).decode("utf-8")

            # Add metadata to JSON message
            message = {
                "type": "test",
                "data": encoded_string,  # Now sending the compressed image from Pillow
                "timestamp": timestamp,
                "resolution": f"{width}x{height}",
                "size_kb": round(compressed_size_kb, 2),
                "compression_time_ms": round(compression_time_ms, 2)
            }

            # Send JSON message via WebSocket
            await websocket.send(json.dumps(message))
            await asyncio.sleep(0.001)  # Wait 50ms for the next frame

# Start the async loop
try:
    asyncio.run(send_messages())
except KeyboardInterrupt:
    print("⏹️ Stopping...")
    capture.release()
    cv2.destroyAllWindows()
