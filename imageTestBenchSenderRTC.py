import asyncio
import logging
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, VideoStreamTrack, RTCSessionDescription
from aiortc.codecs import get_capabilities
from av import VideoFrame
from websocket_signaling import WebSocketSignaling
import time
import argparse
import cv2
import os
from PIL import Image
import numpy as np
import json

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description="WebRTC Image Folder Sender")
parser.add_argument(
    "--signaling_server",
    type=str,
    default="ws://34.46.183.47:9000",
    help="WebSocket Signaling Server URL (default: ws://34.46.183.47:9000)"
)
args = parser.parse_args()
SIGNALING_SERVER = args.signaling_server

IMAGE_FOLDER = "test_images"
JPEG_QUALITIES = [20,25,30,35,40,45,50,55,60,65,70,75,80,85,90]
SECONDS_PER_QUALITY = 5
FPS = 20
FRAME_INTERVAL = 1 / FPS
FRAMES_PER_QUALITY = SECONDS_PER_QUALITY * FPS

class ImageFolderStreamTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self, data_channel):
        super().__init__()
        self.data_channel = data_channel
        self.image_files = sorted([
            f for f in os.listdir(IMAGE_FOLDER)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ])
        if not self.image_files:
            raise RuntimeError("❌ Geen afbeeldingen gevonden in 'test_images/'!")
        self.frames = self._generate_frames()
        self.start_time = time.time()
        self.frame_count = 0

    def _generate_frames(self):
        for image_file in self.image_files:
            image_path = os.path.join(IMAGE_FOLDER, image_file)
            frame = cv2.imread(image_path)
            if frame is None:
                continue
            height, width = frame.shape[:2]
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            for quality in JPEG_QUALITIES:
                encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                _, enc_frame = cv2.imencode('.jpg', frame_rgb, encode_params)
                img_array = cv2.imdecode(enc_frame, cv2.IMREAD_COLOR)
                resized = cv2.resize(img_array, (width, height))
                for _ in range(FRAMES_PER_QUALITY):
                    yield resized, image_file, width, height, quality

    async def next_timestamp(self):
        self.frame_count += 1
        timestamp = int((time.time() - self.start_time) * 90000)
        return timestamp, 90000

    async def recv(self):
        try:
            frame, image_file, width, height, quality = next(self.frames)
        except StopIteration:
            await asyncio.sleep(1)
            raise asyncio.CancelledError("✅ Alle frames zijn verzonden.")

        self.frame_count += 1
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        # ✅ Stuur metadata via data channel
        if self.data_channel and self.data_channel.readyState == "open":
            metadata = {
                "setup_description": SIGNALING_SERVER,
                "frame_id": str(self.frame_count),
                "type": "test",
                "filename": image_file,
                "timestamp": timestamp,
                "resolution": f"{width}x{height}",
                "jpeg_quality": str(quality),
                "size_kb": "n/a"
            }
            self.data_channel.send(json.dumps(metadata))
            logging.info(f"📤 Metadata verzonden: {metadata}")
        else:
            logging.warning("Datachannel not open")

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts, video_frame.time_base = await self.next_timestamp()

        if self.frame_count % 1000 == 0:
            logging.info(f"📡 Verzonden frame #{self.frame_count}")
        await asyncio.sleep(FRAME_INTERVAL)
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
            logging.info(f"🧊 ICE-candidate: {event.candidate}")

    transceiver = pc.addTransceiver("video", direction="sendonly")
    video_codecs = [c for c in get_capabilities("video").codecs if c.name == "VP8"]
    transceiver.setCodecPreferences(video_codecs)

    data_channel = pc.createDataChannel("metadata")
    pc.addTrack(ImageFolderStreamTrack(data_channel))

    try:
        await signaling.connect()
        logging.info("✅ Verbonden met signaling server. Wacht op client...")

        while True:
            obj = await signaling.receive()
            if isinstance(obj, dict) and "sdp" in obj:
                await pc.setRemoteDescription(RTCSessionDescription(sdp=obj["sdp"], type=obj["type"]))
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                await signaling.send({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})
                logging.info("🚀 WebRTC verbinding opgezet en streaming gestart.")
            elif obj is None:
                break

    except Exception as e:
        logging.error(f"❌ Fout: {e}")

    finally:
        logging.info("🛑 Verbinding sluiten...")
        await pc.close()
        await signaling.close()
        logging.info("✅ Gesloten.")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("🛑 Onderbroken door gebruiker.")
