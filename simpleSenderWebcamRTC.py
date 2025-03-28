import asyncio
import cv2
import logging
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import VideoFrame
from websocket_signaling import WebSocketSignaling  # ✅ Gebruik aangepaste WebSocket Signaling
import time
import argparse
import numpy as np

# Logging instellen
logging.basicConfig(level=logging.INFO)

# Set up argument parser
parser = argparse.ArgumentParser(
    description="Receive images via WebSocket and record network parameters."
)

parser.add_argument(
    "--signaling_server",
    type=str,
    default="ws://34.58.161.254:9000",
    help="WebSocket Signaling Server URL (default: ws://34.58.161.254:9000)"
)

args = parser.parse_args()
SIGNALING_SERVER = args.signaling_server

TARGET_WIDTH, TARGET_HEIGHT = 640, 480  # Consistente weergavegrootte

class DummyVideoTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self):
        super().__init__()
        self.start_time = time.time()
        self.frame_count = 0

    async def recv(self):
        frame = VideoFrame(width=640, height=480, format="rgb24")
        frame.pts, frame.time_base = self.next_timestamp()
        return frame

    def next_timestamp(self):
        self.frame_count += 1
        timestamp = int((time.time() - self.start_time) * 90000)
        return timestamp, 90000

class VideoReceiver:
    def __init__(self):
        self.fps_display = 0
        self.message_count = 0
        self.last_time = asyncio.get_event_loop().time()

    def process_frame(self, frame: VideoFrame):
        image = frame.to_ndarray(format="rgb24")
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        image = cv2.resize(image, (TARGET_WIDTH, TARGET_HEIGHT))

        self.message_count += 1
        current_time = asyncio.get_event_loop().time()
        elapsed_time = current_time - self.last_time

        if elapsed_time >= 1.0:
            self.fps_display = self.message_count
            self.message_count = 0
            self.last_time = current_time

        cv2.putText(image, f"FPS: {self.fps_display}", (10, 470),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2, cv2.LINE_AA)

        cv2.imshow("WebRTC Video Stream", image)
        cv2.waitKey(1)

async def wait_for_ice(pc):
    for _ in range(10):
        if pc.iceConnectionState in ["connected", "completed"]:
            logging.info("✅ ICE-verbinding tot stand gebracht!")
            return True
        await asyncio.sleep(1)
    logging.error("❌ ICE-verbinding is mislukt!")
    return False

async def run():
    configuration = RTCConfiguration(iceServers=[
        RTCIceServer(urls="stun:34.58.161.254:3478"),
        RTCIceServer(
            urls=["turn:34.58.161.254:3478?transport=udp"],
            username="unused",
            credential="J0eS3cret123"
        )
    ])

    signaling = WebSocketSignaling(SIGNALING_SERVER)
    pc = RTCPeerConnection(configuration)
    receiver = VideoReceiver()

    @pc.on("connectionstatechange")
    async def on_connection_state_change():
        logging.info(f"🔗 WebRTC status veranderd")

    @pc.on("track")
    def on_track(track):
        logging.info(f"📡 Ontvangen video track: {track.kind}")
        if track.kind == "video":
            async def receive_video():
                while True:
                    try:
                        frame = await track.recv()
                        receiver.process_frame(frame)
                    except Exception as e:
                        logging.warning(f"⚠️ Fout bij video-ontvangst: {e}", exc_info=True)
                        await asyncio.sleep(0.1)
            asyncio.create_task(receive_video())

    try:
        await signaling.connect()
        logging.info("✅ Verbonden met WebRTC Signaling Server... Verstuur offer naar sender...")

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await signaling.send({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})

        obj = await signaling.receive()
        if isinstance(obj, dict) and "sdp" in obj:
            if pc.signalingState == "have-local-offer":
                await pc.setRemoteDescription(RTCSessionDescription(sdp=obj["sdp"], type=obj["type"]))
            else:
                logging.warning("⚠️ Signaling state is niet 'have-local-offer', skipping setRemoteDescription")

        if not await wait_for_ice(pc):
            raise Exception("ICE-verbinding mislukt!")

        logging.info("✅ WebRTC-verbinding is succesvol tot stand gekomen!")

        while True:
            await asyncio.sleep(1)
    except Exception as e:
        logging.error(f"❌ Fout opgetreden: {e}")
    finally:
        logging.info("🛑 WebRTC verbinding sluiten...")
        await pc.close()
        await signaling.close()
        cv2.destroyAllWindows()
        logging.info("✅ WebRTC gestopt en venster gesloten.")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("🛑 Handmatige onderbreking. Programma wordt afgesloten.")
        cv2.destroyAllWindows()
