import sys
import asyncio
import json
import websockets
import time
import cv2
import numpy as np
import base64
import csv
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

SIGNALING_SERVER = "ws://94.111.36.87:9000"
if len(sys.argv) > 1:
    SIGNALING_SERVER = sys.argv[1]

AES_KEY = b'C\x03\xb6\xd2\xc5\t.Brp\x1ce\x0e\xa4\xf6\x8b\xd2\xf6\xb0\x8a\x9c\xd5D\x1e\xf4\xeb\x1d\xe6\x0c\x1d\xff '

video_writer = None
current_resolution = None

# CSV-bestand voorbereiden
timestamp_label = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"stream_log.csv"
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["timestamp", "filename", "resolution", "jpeg_quality", "size_kb", "compression_time_ms", "encryption_time_ms", "fps"])

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

def init_video_writer(resolution):
    global video_writer
    if video_writer is not None:
        video_writer.release()

    width, height = resolution
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    filename = f"recording_{width}x{height}.avi"
    video_writer = cv2.VideoWriter(filename, fourcc, 30.0, (width, height))
    print(f"🎥 Opname gestart: {filename}")

async def receive_messages():
    global current_resolution, video_writer

    async with websockets.connect(SIGNALING_SERVER) as websocket:
        print(f"✅ Verbonden met Signaling Server: {SIGNALING_SERVER}")

        message_count = 0
        last_time = time.time()
        fps_display = 0

        while True:
            try:
                message = await websocket.recv()
            except websockets.exceptions.ConnectionClosed:
                print("🔌 Verbinding gesloten.")
                break

            message_json = json.loads(message)
            decrypted_data = decrypt_data(message_json["data"])
            np_arr = np.frombuffer(decrypted_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            width, height = map(int, message_json["resolution"].split("x"))
            if current_resolution != (width, height):
                current_resolution = (width, height)
                init_video_writer(current_resolution)

            frame = cv2.resize(frame, (width, height))

            message_count += 1
            current_time = time.time()
            elapsed_time = current_time - last_time
            if elapsed_time >= 1.0:
                fps_display = message_count
                message_count = 0
                last_time = current_time

            overlay = frame.copy()
            cv2.putText(overlay, f"Time: {message_json['timestamp']}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(overlay, f"Resolution: {message_json['resolution']}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(overlay, f"Size: {message_json['size_kb']} KB", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(overlay, f"Comp. Time: {message_json['compression_time_ms']} ms", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(overlay, f"Encryption: {message_json['encryption_time_ms']} ms", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(overlay, f"JPEG Quality: {message_json['jpeg_quality']}%", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 255), 2)
            cv2.putText(overlay, f"Receiver FPS: {fps_display}", (10, 210), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)

            if video_writer:
                video_writer.write(overlay)

            # ⬇️ CSV logging
            with open(csv_filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    message_json["timestamp"],
                    message_json.get("filename", ""),
                    message_json["resolution"],
                    message_json["jpeg_quality"],
                    message_json["size_kb"],
                    message_json["compression_time_ms"],
                    message_json["encryption_time_ms"],
                    fps_display
                ])

            cv2.imshow("Live Stream met Overlay", overlay)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    if video_writer:
        video_writer.release()
    cv2.destroyAllWindows()

    # 📊 Genereer visualisatie
# Start
asyncio.run(receive_messages())
