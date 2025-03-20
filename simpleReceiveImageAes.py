import asyncio
import json
import websockets
import time
import cv2
import numpy as np
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

SIGNALING_SERVER = "ws://94.111.36.87:9000"  # Vervang door je server IP
SIGNALING_SERVER = "ws://192.168.1.29:9000"  # Vervang door je server IP


TARGET_WIDTH, TARGET_HEIGHT = 640, 480  # Consistente afmetingen

# Gebruik de vooraf gegenereerde AES-256 sleutel
AES_KEY = b'C\x03\xb6\xd2\xc5\t.Brp\x1ce\x0e\xa4\xf6\x8b\xd2\xf6\xb0\x8a\x9c\xd5D\x1e\xf4\xeb\x1d\xe6\x0c\x1d\xff '

def decrypt_data(encrypted_base64):
    """Decrypt AES-256 CBC versleutelde base64-gegevens"""
    encrypted_data = base64.b64decode(encrypted_base64)
    iv = encrypted_data[:16]  # Eerste 16 bytes zijn de IV
    encrypted_bytes = encrypted_data[16:]

    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()

    # Verwijder PKCS7 padding
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    decrypted_bytes = unpadder.update(decrypted_padded) + unpadder.finalize()
    
    return decrypted_bytes  # Geeft originele afbeelding bytes terug

async def receive_messages():
    async with websockets.connect(SIGNALING_SERVER) as websocket:
        print(f"✅ Verbonden met Signaling Server: {SIGNALING_SERVER}")

        message_count = 0
        last_time = time.time()
        fps_display = 0  # Opslag van laatste FPS waarde

        while True:
            message = await websocket.recv()
            message_json = json.loads(message)  # Parse JSON data
            
            # 📌 Decrypt versleutelde afbeelding
            decrypted_data = decrypt_data(message_json["data"])

            # 📌 Decodeer naar afbeelding
            np_arr = np.frombuffer(decrypted_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            # ✅ Zorg ervoor dat de afbeelding altijd 640x480 is
            if frame is not None:
                frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))

            # ✅ FPS-berekening
            message_count += 1
            current_time = time.time()
            elapsed_time = current_time - last_time

            if elapsed_time >= 1.0:
                fps_display = message_count  # Sla FPS-waarde op
                message_count = 0
                last_time = current_time

            # ✅ Overlay FPS tekst op frame
            if frame is not None:
                fps_text = f"FPS op ontvanger: {fps_display}"
                cv2.putText(frame, fps_text, (10, 470), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2, cv2.LINE_AA)

                # Toon de afbeelding met FPS-overlay
                cv2.imshow("Ontvangen Afbeelding", frame)
                cv2.waitKey(1)  # Nodig voor OpenCV updates

asyncio.run(receive_messages())
