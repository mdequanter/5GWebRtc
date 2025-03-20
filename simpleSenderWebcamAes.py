import sys
import asyncio
import json
import websockets
import time
import cv2
import base64
import io
from PIL import Image
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import os

SIGNALING_SERVER = "ws://94.111.36.87:9000"  # Vervang door je server IP

if len(sys.argv) > 1:
    SIGNALING_SERVER = sys.argv[1]

print(f"Signaling Server: {SIGNALING_SERVER}")

# Definieer JPEG-kwaliteitsniveau
JPEG_QUALITY = 90

# Open de camera
capture = cv2.VideoCapture(0)
width = 640
height = 480

# AES-256 sleutel (moet 32 bytes zijn, hier een voorbeeld, verander dit voor veiligheid)
AES_KEY = b'C\x03\xb6\xd2\xc5\t.Brp\x1ce\x0e\xa4\xf6\x8b\xd2\xf6\xb0\x8a\x9c\xd5D\x1e\xf4\xeb\x1d\xe6\x0c\x1d\xff '

def encrypt_data(plain_text):
    """Versleutelt gegevens met AES-256 CBC en base64-encodeert de uitvoer."""
    # Start tijdmeting voor encryptie
    encrypt_start_time = time.time()

    iv = os.urandom(16)  # AES vereist een IV van 16 bytes
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # PKCS7 padding toepassen
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(plain_text) + padder.finalize()


    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # Einde tijdmeting voor encryptie
    encrypt_end_time = time.time()
    encryption_time_ms = (encrypt_end_time - encrypt_start_time) * 1000  # Omzetten naar ms

    return base64.b64encode(iv + encrypted_data).decode('utf-8'), encryption_time_ms  # IV meesturen voor decryptie

async def send_messages():
    async with websockets.connect(SIGNALING_SERVER) as websocket:
        print(f"✅ Verbonden met Signaling Server: {SIGNALING_SERVER}")

        while True:
            ret, frame = capture.read()
            if not ret:
                print("❌ Kan geen frame ophalen van de camera")
                continue

            # Frame resizen naar 640x480 pixels
            frame = cv2.resize(frame, (width, height))

            # Timestamp ophalen
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

            # OpenCV-frame converteren naar RGB voor Pillow
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            # Compressie met Pillow naar een in-memory JPEG
            compressed_image_io = io.BytesIO()
            start_time = time.time()
            pil_image.save(compressed_image_io, format="JPEG", quality=JPEG_QUALITY)
            end_time = time.time()

            # Compressed image bytes ophalen
            compressed_bytes = compressed_image_io.getvalue()
            compressed_size_kb = len(compressed_bytes) / 1024  # Omzetten naar KB
            compression_time_ms = (end_time - start_time) * 1000  # Omzetten naar ms

            # Oorspronkelijke afbeelding annoteren met metadata
            cv2.putText(frame, f"Time: {timestamp}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Resolution: {width}x{height}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Size: {round(compressed_size_kb, 2)} KB", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Comp. Time/Quality: {round(compression_time_ms, 2)} ms / {JPEG_QUALITY}%", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Annotated OpenCV frame opnieuw naar Pillow converteren
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            # Opnieuw comprimeren
            final_compressed_image_io = io.BytesIO()
            pil_image.save(final_compressed_image_io, format="JPEG", quality=JPEG_QUALITY)
            final_compressed_bytes = final_compressed_image_io.getvalue()

            # Gegevens versleutelen en encryptietijd meten
            encrypted_data, encryption_time_ms = encrypt_data(final_compressed_bytes)

            # JSON bericht samenstellen
            message = {
                "type": "test",
                "data": encrypted_data,  # Versleutelde afbeelding
                "timestamp": timestamp,
                "resolution": f"{width}x{height}",
                "size_kb": round(compressed_size_kb, 2),
                "compression_time_ms": round(compression_time_ms, 2),
                "encryption_time_ms": round(encryption_time_ms, 2)
            }

            # Verstuur versleuteld bericht via WebSocket
            await websocket.send(json.dumps(message))
            await asyncio.sleep(0.001)  # Even wachten voor het volgende frame

# Start de async loop
try:
    asyncio.run(send_messages())
except KeyboardInterrupt:
    print("⏹️ Stopt...")
    capture.release()
    cv2.destroyAllWindows()
