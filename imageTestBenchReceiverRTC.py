import asyncio
import cv2
import logging
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import VideoFrame
from websocket_signaling import WebSocketSignaling
import time
import argparse
import json

# Logging instellen
logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description="Receive images via WebRTC and display metadata.")
parser.add_argument(
    "--signaling_server",
    type=str,
    default="ws://34.46.183.47:9000",
    help="WebSocket Signaling Server URL (default: ws://34.46.183.47:9000)"
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
        # Lege zwarte frame (wordt niet echt gebruikt)
        frame = VideoFrame(width=TARGET_WIDTH, height=TARGET_HEIGHT, format="rgb24")
        frame.pts, frame.time_base = self.next_timestamp()
        await asyncio.sleep(1 / 30)
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
        self.latest_metadata = {}

    def handle_metadata(self, json_str):
        try:
            self.latest_metadata = json.loads(json_str)
        except Exception as e:
            print(f"⚠️ Kan metadata niet verwerken: {e}")

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

        metadata = self.latest_metadata
        overlay_lines = [
            f"FPS: {self.fps_display}",
            f"Frame ID: {metadata.get('frame_id', '-')}",
            f"Time: {metadata.get('timestamp', '-')}",
            f"Resolution: {metadata.get('resolution', '-')}",
            f"Filename: {metadata.get('filename', '-')}",
            f"Quality: {metadata.get('jpeg_quality', '-')}",
            f"Size: {metadata.get('size_kb', '-')} KB",
            f"Setup: {metadata.get('setup_description', '-')[:30]}"
        ]

        for i, line in enumerate(overlay_lines):
            cv2.putText(image, line, (10, 30 + i*30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)

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
    receiver = VideoReceiver()

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
    dummy_video_track = DummyVideoTrack()
    pc.addTrack(dummy_video_track)

    @pc.on("connectionstatechange")
    async def on_connection_state_change():
        logging.info(f"🔗 WebRTC status veranderd naar {pc.connectionState}")

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
                        logging.info(f"❌ Fout bij video-ontvangst: {e}")
                        break
            asyncio.create_task(receive_video())

    @pc.on("datachannel")
    def on_datachannel(channel):
        logging.info(f"📨 DataChannel geopend: {channel.label}")

        @channel.on("message")
        def on_message(message):
            receiver.handle_metadata(message)

    try:
        await signaling.connect()
        logging.info("✅ Verbonden met WebRTC Signaling Server... Verstuur offer naar sender...")

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await signaling.send({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})

        obj = await signaling.receive()
        if isinstance(obj, dict) and "sdp" in obj:
            await pc.setRemoteDescription(RTCSessionDescription(sdp=obj["sdp"], type=obj["type"]))

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
