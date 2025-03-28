import asyncio
import cv2
import logging
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import VideoFrame
from websocket_signaling import WebSocketSignaling
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)

SIGNALING_SERVER = "ws://94.111.36.87:9000"
TARGET_WIDTH, TARGET_HEIGHT = 640, 480

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

        # Extract timestamp
        timestamp_meta = frame.metadata.get("timestamp", None)
        if timestamp_meta:
            try:
                sent_time = datetime.fromisoformat(timestamp_meta)
                now = datetime.now()
                latency_ms = (now - sent_time).total_seconds() * 1000
                cv2.putText(image, f"Latency: {latency_ms:.2f} ms", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            except:
                pass

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
    configuration = RTCConfiguration(iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")])
    signaling = WebSocketSignaling(SIGNALING_SERVER)
    pc = RTCPeerConnection(configuration)
    receiver = VideoReceiver()
    dummy_video_track = DummyVideoTrack()
    pc.addTrack(dummy_video_track)

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            async def receive_video():
                while True:
                    try:
                        frame = await track.recv()
                        receiver.process_frame(frame)
                    except Exception as e:
                        continue
            asyncio.create_task(receive_video())

    try:
        await signaling.connect()
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await signaling.send({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})
        obj = await signaling.receive()
        if isinstance(obj, dict) and "sdp" in obj:
            await pc.setRemoteDescription(RTCSessionDescription(sdp=obj["sdp"], type=obj["type"]))
        if not await wait_for_ice(pc):
            raise Exception("ICE-verbinding mislukt!")
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        logging.error(f"❌ Fout opgetreden: {e}")
    finally:
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
