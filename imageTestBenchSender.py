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

time.sleep(5)   # Wacht 5 seconden om de server te starten


# WebSocket server
SIGNALING_SERVER = "ws://heliwi.duckdns.org:9000"
if len(sys.argv) > 1:
    SIGNALING_SERVER = sys.argv[1]

print(f"Signaling Server: {SIGNALING_SERVER}")

# AES-256 sleutel (32 bytes)
AES_KEY = b'C\x03\xb6\xd2\xc5\t.Brp\x1ce\x0e\xa4\xf6\x8b\xd2\xf6\xb0\x8a\x9c\xd5D\x1e\xf4\xeb\x1d\xe6\x0c\x1d\xff '

# Instellingen
IMAGE_FOLDER = "test_images"
JPEG_QUALITIES = [20,25,30,35,40,45,50,55,60,65,70,75,80,85,90]
SECONDS_PER_QUALITY = 5
FPS = 30
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
        print(f"✅ Verbonden met Signaling Server: {SIGNALING_SERVER}")

        image_files = sorted([
            f for f in os.listdir(IMAGE_FOLDER)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ])

        if not image_files:
            print("❌ Geen afbeeldingen gevonden in test_images/")
            return

        for image_file in image_files:
            image_path = os.path.join(IMAGE_FOLDER, image_file)
            frame = cv2.imread(image_path)

            if frame is None:
                print(f"⚠️ Fout bij inlezen: {image_file}")
                continue

            height, width = frame.shape[:2]
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            print(f"🚀 Start streaming: {image_file} ({width}x{height})")

            for quality in JPEG_QUALITIES:
                print(f"🎯 JPEG kwaliteit: {quality}% ({SECONDS_PER_QUALITY} sec @ {FPS} FPS)")
                for _ in range(FRAMES_PER_QUALITY):
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

                    # Compressie
                    compressed_io = io.BytesIO()
                    compress_start = time.time()
                    pil_image.save(compressed_io, format="JPEG", quality=quality)
                    compress_time = (time.time() - compress_start) * 1000
                    compressed_bytes = compressed_io.getvalue()
                    size_kb = len(compressed_bytes) / 1024

                    # Encryptie
                    encrypted_data, encryption_time = encrypt_data(compressed_bytes)

                    # Verzendbericht
                    message = {
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

        print("✅ Alle afbeeldingen en kwaliteitsniveaus verzonden.")

# Start de async loop
try:
    asyncio.run(send_images())
except KeyboardInterrupt:
    print("⏹️ Gestopt door gebruiker.")
