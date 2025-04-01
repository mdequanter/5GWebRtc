import asyncio
import cv2
import logging
import json
import time
import argparse
from datetime import datetime


from aiortc import (
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
    MediaStreamTrack,
)
from av import VideoFrame
from websocket_signaling import WebSocketSignaling  # ✅ Gebruik aangepaste WebSocket Signaling

# Logging instellen
logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description="Receive images via WebSocket and record network parameters.")
parser.add_argument(
    "--signaling_server",
    type=str,
    default="ws://34.46.183.47:9000",
    help="WebSocket Signaling Server URL"
)
args = parser.parse_args()
SIGNALING_SERVER = args.signaling_server
TARGET_WIDTH, TARGET_HEIGHT = 640, 480

offset_time = 0.0

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

        # FPS berekening
        self.message_count += 1
        current_time = asyncio.get_event_loop().time()
        elapsed_time = current_time - self.last_time

        if elapsed_time >= 1.0:
            self.fps_display = self.message_count
            self.message_count = 0
            self.last_time = current_time

        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        cv2.putText(image, f"Time: {timestamp_str}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)


        cv2.putText(image, f"FPS: {self.fps_display}", (10, 90),
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


async def time_sync(signaling):
    request_tx = datetime.now()
    await signaling.send(json.dumps({
        "type": "SingleTimeSync",
        "requestTxTime": request_tx.isoformat()
    }))

    response = await signaling.receive()
    response_data = json.loads(response)

    response_rx = datetime.now()
    response_tx = datetime.fromisoformat(response_data["responseTxTime"])
    request_tx_remote = datetime.fromisoformat(response_data["requestTxTime"])
    round_trip = (response_rx - request_tx).total_seconds()
    turn_around = (response_tx - request_tx_remote).total_seconds()
    delay = ((round_trip - turn_around) / 2)*1000
    return delay

async def run():

    global offset_ms

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
    receiver = VideoReceiver()
    pc.addTrack(DummyVideoTrack())

    @pc.on("connectionstatechange")
    async def on_connection_state_change():
        logging.info(f"🔗 WebRTC status veranderd: {pc.connectionState}")

    @pc.on("datachannel")
    def on_datachannel(channel):
        logging.info(f"📡 Datachannel ontvangen: {channel.label}")

        @channel.on("message")
        def on_message(message):
            try:
                data = json.loads(message)
                frame_id = data.get("frame_id")
                timestamp = data.get("timestamp")
                resolution = data.get("resolution")
                print(f"📦 Ontvangen metadata - Frame ID: {frame_id}, Tijd: {timestamp}, Resolutie: {resolution}")
            except Exception as e:
                logging.warning(f"⚠️ Kan bericht niet decoderen: {e}")

    @pc.on("track")
    def on_track(track):
        logging.info(f"📡 Ontvangen video track: {track.kind}")
        if track.kind == "video":
            async def receive_video():
                while True:
                    try:
                        frame = await track.recv()
                        receiver.process_frame(frame)
                    except Exception:
                        continue
            asyncio.create_task(receive_video())

    try:
        await signaling.connect()
        logging.info("✅ Verbonden met WebRTC Signaling Server... Verstuur offer naar sender...")



        offset_ms = await time_sync(signaling)
               
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        print ("send offer ...................")
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
