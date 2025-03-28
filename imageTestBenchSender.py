import sys
import asyncio
import json
import websockets
import time
import cv2
import base64
import io
import os
from PIL import Image
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import argparse
from datetime import datetime

# Set up argument parser
parser = argparse.ArgumentParser(
    description="Send images via WebSocket and record network parameters."
)

parser.add_argument(
    "--signaling_server",
    type=str,
    default="ws://heliwi.duckdns.org:9000",
    help="WebSocket Signaling Server URL (default: ws://heliwi.duckdns.org:9000)"
)

parser.add_argument(
    "--description",
    type=str,
    default="Local Wifi 5G",
    help="Description of the test setup (default: 'Local Wifi 5G')"
)

args = parser.parse_args()

SIGNALING_SERVER = args.signaling_server
setupDescription = f"{args.description} - {SIGNALING_SERVER}"

print(f"Started: {setupDescription}")

# AES-256 key (32 bytes)
# Don't forget to change this key for real situations!!!
AES_KEY = b'C\x03\xb6\xd2\xc5\t.Brp\x1ce\x0e\xa4\xf6\x8b\xd2\xf6\xb0\x8a\x9c\xd5D\x1e\xf4\xeb\x1d\xe6\x0c\x1d\xff '

# Settings
IMAGE_FOLDER = "test_images"
JPEG_QUALITIES = [20,25,30,35,40,45,50,55,60,65,70,75,80,85,90]
# JPEG_QUALITIES = [20]
SECONDS_PER_QUALITY = 5
FPS = 40
FRAMES_PER_QUALITY = SECONDS_PER_QUALITY * FPS
FRAME_INTERVAL = 1 / FPS

def encrypt_data(plain_bytes):
    encrypt_start_time = time.time()

    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(plain_bytes) + padder.finalize()

    encrypted = encryptor.update(padded) + encryptor.finalize()
    encryption_time = (time.time() - encrypt_start_time) * 1000

    return base64.b64encode(iv + encrypted).decode("utf-8"), encryption_time

async def send_images():
    async with websockets.connect(SIGNALING_SERVER, max_size=None) as websocket:
        print(f"✅ Connected to Signaling Server: {SIGNALING_SERVER}")

        message = await websocket.recv()
        data = json.loads(message)

        if data["type"] == "SingleTimeSync":
            request_tx_time = data["requestTxTime"]
            response_tx_time = datetime.now().isoformat()

            await websocket.send(json.dumps({
                "type": "SingleTimeSyncResponse",
                "requestTxTime": request_tx_time,
                "responseTxTime": response_tx_time
            }))


        image_files = sorted([
            f for f in os.listdir(IMAGE_FOLDER)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ])

        if not image_files:
            print("❌ No images found in test_images/")
            return

        frame_id = 0

        for image_file in image_files:
            image_path = os.path.join(IMAGE_FOLDER, image_file)
            frame = cv2.imread(image_path)

            if frame is None:
                print(f"⚠️ Error reading: {image_file}")
                continue

            height, width = frame.shape[:2]
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            print(f"🚀 Start streaming: {image_file} ({width}x{height})")

            for quality in JPEG_QUALITIES:
                print(f"🎯 JPEG quality: {quality}% ({SECONDS_PER_QUALITY} sec @ {FPS} FPS)")
                for _ in range(FRAMES_PER_QUALITY):
                    frame_id += 1
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    #if frame_id % 500 == 0:
                    #    print (f"frame {frame_id} : {timestamp}")
                    # Compression
                    compressed_io = io.BytesIO()
                    compress_start = time.time()
                    pil_image.save(compressed_io, format="JPEG", quality=quality)
                    compress_time = (time.time() - compress_start) * 1000
                    compressed_bytes = compressed_io.getvalue()
                    size_kb = len(compressed_bytes) / 1024

                    # Encryption
                    encrypted_data, encryption_time = encrypt_data(compressed_bytes)

                    # Message to send
                    message = {
                        "setup_description": setupDescription,
                        "frame_id": frame_id,
                        "type": "test",
                        "filename": image_file,
                        "timestamp": timestamp,
                        "resolution": f"{width}x{height}",
                        "jpeg_quality": quality,
                        "size_kb": round(size_kb, 2),
                        "compression_time_ms": round(compress_time, 5),
                        "encryption_time_ms": round(encryption_time, 5),
                        "data": encrypted_data
                    }

                    await websocket.send(json.dumps(message))
                    await asyncio.sleep(FRAME_INTERVAL)

        print(f"✅ All images and quality levels sent. Total frames: {frame_id}")

# Start the async loop
try:
    asyncio.run(send_images())
except KeyboardInterrupt:
    print("⏹️ Stopped by user.")
