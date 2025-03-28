import asyncio
import cv2
import logging
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, VideoStreamTrack, RTCSessionDescription
from av import VideoFrame
from websocket_signaling import WebSocketSignaling
import time
from aiortc.codecs import get_capabilities
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO)

SIGNALING_SERVER = "ws://94.111.36.87:9000"

capture = cv2.VideoCapture(0)
if not capture.isOpened():
    raise RuntimeError("❌ Kan de camera niet openen!")

WIDTH, HEIGHT = 640, 480

class CameraStreamTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.start_time = time.time()
        self.frame_count = 0
        logging.info("✅ Video track is toegevoegd aan peer connection!")

    def processFrame(self, frame):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        cv2.putText(frame, f"Time: {timestamp}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Resolution: {WIDTH}x{WIDTH}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return frame

    async def next_timestamp(self):
        self.frame_count += 1
        timestamp = int((time.time() - self.start_time) * 90000)
        return timestamp, 90000

    async def recv(self):
        while True:
            try:
                ret, frame = capture.read()
                if not ret:
                    logging.warning("⚠️ Kan geen frame ophalen! Probeer opnieuw...")
                    await asyncio.sleep(0.1)
                    continue

                frame = cv2.resize(frame, (WIDTH, HEIGHT))
                frame = self.processFrame(frame)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
                video_frame.pts, video_frame.time_base = await self.next_timestamp()

                # ✅ Timestamp meesturen via custom attribute (als workaround)
                setattr(video_frame, "timestamp_iso", datetime.now().isoformat())

                return video_frame

            except Exception as e:
                logging.error(f"❌ Fout in `recv()`: {e}")
                await asyncio.sleep(0.1)

async def run():
    configuration = RTCConfiguration(iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")])
    signaling = WebSocketSignaling(SIGNALING_SERVER)
    pc = RTCPeerConnection(configuration)

    transceiver = pc.addTransceiver("video", direction="sendonly")
    video_codecs = [c for c in get_capabilities("video").codecs if c.name == "VP8"]
    transceiver.setCodecPreferences(video_codecs)

    video_track = CameraStreamTrack()
    pc.addTrack(video_track)

    try:
        await signaling.connect()
        logging.info("✅ Verbonden met WebRTC Signaling Server... Wachten op een client...")

        while True:
            obj = await signaling.receive()
            if isinstance(obj, dict) and "sdp" in obj:
                logging.info("📡 WebRTC Client Verbonden! Start Streaming...")
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
