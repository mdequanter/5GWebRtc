import sys
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

SIGNALING_SERVER = "ws://94.111.36.87:9000"

if len(sys.argv) > 1:
    SIGNALING_SERVER = sys.argv[1]

TARGET_WIDTH, TARGET_HEIGHT = 640, 480

AES_KEY = b'C\x03\xb6\xd2\xc5\t.Brp\x1ce\x0e\xa4\xf6\x8b\xd2\xf6\xb0\x8a\x9c\xd5D\x1e\xf4\xeb\x1d\xe6\x0c\x1d\xff '

# 🎥 AVI VideoWriter met XVID codec
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter('output.avi', fourcc, 20.0, (TARGET_WIDTH, TARGET_HEIGHT))

def decrypt_data(encrypted_base64):
    encrypted_data = base64.b64decode(encrypted_base64)
    iv = encrypted_data[:16]
    encrypted_bytes = encrypted_data[16:]

    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()

    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    decrypted_bytes = unpadder.update(decrypted_padded) + unpadder.finalize()
    
    return decrypted_bytes

async def receive_messages():
    global out
    async with websockets.connect(SIGNALING_SERVER) as websocket:
        print(f"✅ Verbonden met Signaling Server: {SIGNALING_SERVER}")

        message_count = 0
        last_time = time.time()
        fps_display = 0

        while True:
            message = await websocket.recv()
            message_json = json.loads(message)
            decrypted_data = decrypt_data(message_json["data"])
            np_arr = np.frombuffer(decrypted_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is not None:
                frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))

                # 🎥 Sla het originele frame op (zonder overlays)
                out.write(frame.copy())

                # 🎯 FPS berekening
                message_count += 1
                current_time = time.time()
                elapsed_time = current_time - last_time

                if elapsed_time >= 1.0:
                    fps_display = message_count
                    message_count = 0
                    last_time = current_time

                # ➕ Overlay enkel voor weergave
                fps_text = f"FPS op ontvanger: {fps_display}"
                cv2.putText(frame, f"Time: {message_json['timestamp']}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Resolution: {message_json['resolution']}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Size: {round(message_json['size_kb'], 2)} KB", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Comp. Time: {round(message_json['compression_time_ms'], 2)} ms", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Encryption time AES: {round(message_json['encryption_time_ms'], 2)} ms", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, fps_text, (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2, cv2.LINE_AA)

                cv2.imshow("Ontvangen Afbeelding", frame)

                # ❌ Stoppen met opnemen via 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("🛑 Opname gestopt door gebruiker.")
                    break

    # 🧹 Resources netjes afsluiten
    out.release()
    cv2.destroyAllWindows()

asyncio.run(receive_messages())
