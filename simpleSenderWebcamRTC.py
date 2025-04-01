import asyncio
import logging
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, VideoStreamTrack, RTCSessionDescription
from aiortc.codecs import get_capabilities
from av import VideoFrame
from websocket_signaling import WebSocketSignaling
import time
import argparse
import cv2

# Logging instellen
logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description="WebRTC Webcam Sender")
parser.add_argument(
    "--signaling_server",
    type=str,
    default="ws://34.46.183.47:9000",
    help="WebSocket Signaling Server URL (default: ws://34.58.161.254:9000)"
)
args = parser.parse_args()
SIGNALING_SERVER = args.signaling_server

WIDTH, HEIGHT = 640, 480

# Open webcam (voeg CAP_DSHOW toe indien nodig op Windows)
capture = cv2.VideoCapture(0)
if not capture.isOpened():
    raise RuntimeError("❌ Kan de camera niet openen!")

class CameraStreamTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self):
        super().__init__()
        self.start_time = time.time()
        self.frame_count = 0
        logging.info("✅ Video track is toegevoegd aan peer connection!")

    async def next_timestamp(self):
        self.frame_count += 1
        timestamp = int((time.time() - self.start_time) * 90000)
        return timestamp, 90000

    async def recv(self):
        while True:
            ret, frame = capture.read()
            if not ret:
                logging.warning("⚠️ Geen frame van camera!")
                await asyncio.sleep(0.1)
                continue

            frame = cv2.resize(frame, (WIDTH, HEIGHT))
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            cv2.putText(frame, f"Time: {timestamp}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Resolution: {WIDTH}x{HEIGHT}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts, video_frame.time_base = await self.next_timestamp()

            if self.frame_count % 30 == 0:
                logging.info(f"📡 Verzonden frame #{self.frame_count}")

            return video_frame

async def run():
    configuration = RTCConfiguration(iceServers=[
        RTCIceServer(urls="stun:34.46.183.47:3478"),
        RTCIceServer(
            urls=["turn:34.46.183.47:3478?transport=udp"],
            username="unused",
            credential="J0eS3cret123"
        )
    ])

    signaling = WebSocketSignaling(SIGNALING_SERVER)
    pc = RTCPeerConnection(configuration)

    @pc.on("icecandidate")
    def on_icecandidate(event):
        if event.candidate:
            logging.info(f"🧊 Sender ICE-candidate: {event.candidate}")

    transceiver = pc.addTransceiver("video", direction="sendonly")
    video_codecs = [c for c in get_capabilities("video").codecs if c.name == "VP8"]
    transceiver.setCodecPreferences(video_codecs)

    pc.addTrack(CameraStreamTrack())

    try:
        await signaling.connect()
        logging.info("✅ Verbonden met WebRTC Signaling Server... Wachten op client...")

        while True:
            obj = await signaling.receive()
            if isinstance(obj, dict) and "sdp" in obj:
                logging.info("📡 WebRTC Client Verbonden! Start streaming...")
                await pc.setRemoteDescription(RTCSessionDescription(sdp=obj["sdp"], type=obj["type"]))
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                await signaling.send({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})
            elif obj is None:
                break

    except Exception as e:
        logging.error(f"❌ Fout opgetreden: {e}")

    finally:
        logging.info("🛑 WebRTC verbinding sluiten...")
        await pc.close()
        await signaling.close()
        capture.release()
        logging.info("✅ Camera vrijgegeven en WebRTC gestopt.")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("🛑 Handmatige onderbreking. Programma wordt afgesloten.")
        capture.release()
