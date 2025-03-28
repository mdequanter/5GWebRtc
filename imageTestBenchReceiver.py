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
import argparse
from datetime import datetime
from datetime import timedelta


no_message_timeout = 5

# Set up argument parser
parser = argparse.ArgumentParser(
    description="Receive images via WebSocket and record network parameters."
)

parser.add_argument(
    "--signaling_server",
    type=str,
    default="ws://heliwi.duckdns.org:9000",
    help="WebSocket Signaling Server URL (default: ws://heliwi.duckdns.org:9000)"
)


args = parser.parse_args()

SIGNALING_SERVER = args.signaling_server

subName = datetime.now().strftime("%Y%m%d_%H%M%S")
outputPath = f"testbench/{subName}"
os.makedirs(outputPath, exist_ok=True)


args = parser.parse_args()

AES_KEY = b'C\x03\xb6\xd2\xc5\t.Brp\x1ce\x0e\xa4\xf6\x8b\xd2\xf6\xb0\x8a\x9c\xd5D\x1e\xf4\xeb\x1d\xe6\x0c\x1d\xff '

video_writer = None
current_resolution = None

# CSV-bestand voorbereiden
timestamp_label = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"{outputPath}/stream_log.csv"
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["setup description","timestamp_receiver","timestamp_server", "filename","frame_id", "resolution", "jpeg_quality", "size_kb", "compression_time_ms", "encryption_time_ms", "fps","Mbits","latency_ms"])

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


async def time_sync(websocket):
    request_tx = datetime.now()
    await websocket.send(json.dumps({
        "type": "SingleTimeSync",
        "requestTxTime": request_tx.isoformat()
    }))

    response = await websocket.recv()
    response_data = json.loads(response)

    response_rx = datetime.now()
    response_tx = datetime.fromisoformat(response_data["responseTxTime"])
    request_tx_remote = datetime.fromisoformat(response_data["requestTxTime"])

    print (f"{response_tx} - {request_tx_remote} ")

    round_trip = (response_rx - request_tx).total_seconds()
    turn_around = (response_tx - request_tx_remote).total_seconds()
    delay = ((round_trip - turn_around) / 2)*1000
    return delay


async def receive_messages():
    global current_resolution, video_writer

    frameCounter = 0

    async with websockets.connect(SIGNALING_SERVER) as websocket:
        print(f"✅ Verbonden met Signaling Server: {SIGNALING_SERVER}")
        frameCounter+=1
        message_count = 0
        last_time = time.time()
        fps_display = 0

        offset_ms = await time_sync(websocket)
        print (f"Estimated offset timesync is: {offset_ms} ms")

        while True:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=no_message_timeout)
            except asyncio.TimeoutError:
                print("⏳ No data received after (timeout). Sluit af.")
                break

            message_json = json.loads(message)
            decrypted_data = decrypt_data(message_json["data"])
            np_arr = np.frombuffer(decrypted_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                continue


            received_dt = datetime.now()
            timestampCsv = received_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]            

            #if message_json['frame_id'] % 500 == 0:
            #    print (f"frame {message_json['frame_id']} : {timestampCsv}")
            

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

            MbitsPerSecond = round((message_json['size_kb'] * 8 * fps_display) / 1000, 4)

            sent_time = datetime.fromisoformat(message_json["timestamp"]) 
            sent_time += timedelta(milliseconds=offset_ms)

            frame_delay_ms = (received_dt - sent_time).total_seconds() * 1000

            overlay = frame.copy()
            cv2.putText(overlay, f"{message_json['setup_description']}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(overlay, f"Time: {message_json['timestamp']}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(overlay, f"Resolution: {message_json['resolution']}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(overlay, f"Size/Mbits: {message_json['size_kb']} KB - {MbitsPerSecond:.2f} Mb/s", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(overlay, f"Comp. Time: {message_json['compression_time_ms']} ms", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(overlay, f"Encryption: {message_json['encryption_time_ms']} ms", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(overlay, f"JPEG Quality: {message_json['jpeg_quality']}%", (10, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(overlay, f"Receiver FPS: {fps_display} - frame: {message_json['frame_id']} ", (10, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.putText(overlay, f"Frame delay: {frame_delay_ms:.3f} ms ", (10, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)


            if video_writer:
                video_writer.write(overlay)

            # ⬇️ CSV logging
            with open(csv_filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    message_json["setup_description"],
                    message_json["timestamp"],
                    timestampCsv,
                    message_json.get("filename", ""),
                    message_json["frame_id"],
                    message_json["resolution"],
                    message_json["jpeg_quality"],
                    message_json["size_kb"],
                    message_json["compression_time_ms"],
                    message_json["encryption_time_ms"],
                    fps_display,
                    MbitsPerSecond,
                    np.round(frame_delay_ms,3),

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
