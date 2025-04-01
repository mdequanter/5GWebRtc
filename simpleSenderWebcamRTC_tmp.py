import asyncio
import logging
import json
import time
import argparse
import cv2
from datetime import datetime
from aiortc import (
    RTCConfiguration, RTCIceServer, RTCPeerConnection,
    VideoStreamTrack, RTCSessionDescription
)
from aiortc.codecs import get_capabilities
from av import VideoFrame
from websocket_signaling import WebSocketSignaling

# Logging
logging.basicConfig(level=logging.INFO)

# Argumenten
parser = argparse.ArgumentParser(description="WebRTC Webcam Sender")
parser.add_argument("--signaling_server", type=str, default="ws://34.46.183.47:9000",
                    help="WebSocket Signaling Server URL")
args = parser.parse_args()
SIGNALING_SERVER = args.signaling_server

# Resolutie
WIDTH, HEIGHT = 320, 240

# Webcam openen
capture = cv2.VideoCapture(0)
if not capture.isOpened():
    raise RuntimeError("❌ Kan de camera niet openen!")

class CameraStreamTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self, data_channel):
        super().__init__()
        self.start_time = time.time()
        self.frame_count = 0
        self.data_channel = data_channel
        logging.info("✅ Videotrack toegevoegd aan PeerConnection")

    async def next_timestamp(self):
        self.frame_count += 1
        return int((time.time() - self.start_time) * 90000), 90000

    async def recv(self):
        ret, frame = capture.read()
        if not ret:
            raise asyncio.CancelledError("❌ Kan geen frame lezen van camera.")

        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        cv2.putText(frame, f"Time: {timestamp_str}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts, video_frame.time_base = await self.next_timestamp()
        return video_frame

async def run(pc, signaling):
    data_channel = pc.createDataChannel("meta")

    @data_channel.on("open")
    def on_open():
        logging.info("📡 Datachannel 'meta' open")

    @data_channel.on("close")
    def on_close():
        logging.info("❌ Datachannel 'meta' gesloten")

    @pc.on("icecandidate")
    def on_icecandidate(event):
        if event.candidate:
            logging.info(f"🧊 ICE-candidate: {event.candidate}")

    @pc.on("datachannel")
    def on_datachannel(channel):
        logging.info(f"📡 Ontvangen datachannel: {channel.label}")
        @channel.on("open")
        def on_open(): logging.info(f"✅ '{channel.label}' open")
        @channel.on("close")
        def on_close(): logging.info(f"❌ '{channel.label}' gesloten")

    # Alleen video zenden
    transceiver = pc.addTransceiver("video", direction="sendonly")
    transceiver.setCodecPreferences([c for c in get_capabilities("video").codecs if c.name == "VP8"])
    pc.addTrack(CameraStreamTrack(data_channel))

    try:
        await signaling.connect()
        logging.info("🔗 Verbonden met signaling server, wachten op client...")

        # Init time sync (optioneel)
        data = json.loads(await signaling.receive())
        if data.get("type") == "SingleTimeSync":
            await signaling.send(json.dumps({
                "type": "SingleTimeSyncResponse",
                "requestTxTime": data["requestTxTime"],
                "responseTxTime": datetime.now().isoformat()
            }))
            logging.info("🕒 Tijd gesynchroniseerd")

        while True:
            obj = await signaling.receive()
            if isinstance(obj, dict) and "sdp" in obj:
                logging.info("✅ WebRTC Client verbonden. Start streaming...")
                await pc.setRemoteDescription(RTCSessionDescription(sdp=obj["sdp"], type=obj["type"]))
                await pc.setLocalDescription(await pc.createAnswer())
                await signaling.send({
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type
                })
            elif obj is None:
                break

    except Exception as e:
        logging.error(f"❌ Fout: {e}")
    finally:
        logging.info("🛑 Verbinding sluiten...")
        await pc.close()
        await signaling.close()
        capture.release()
        logging.info("✅ Camera vrijgegeven")

if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        config = RTCConfiguration(iceServers=[
            RTCIceServer(urls="stun:34.46.183.47:3478"),
            RTCIceServer(urls=["turn:34.46.183.47:3478?transport=udp"],
                         username="unused", credential="J0eS3cret123")
        ])
        pc = RTCPeerConnection(config)
        signaling = WebSocketSignaling(SIGNALING_SERVER)

        loop.run_until_complete(run(pc, signaling))

    except KeyboardInterrupt:
        logging.info("🛑 Onderbroken door gebruiker")
        capture.release()
