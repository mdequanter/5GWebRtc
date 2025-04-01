import asyncio
import logging
import json
import time
import argparse
import cv2
from datetime import datetime


from aiortc import (
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    VideoStreamTrack,
    RTCSessionDescription,
)
from aiortc.codecs import get_capabilities
from av import VideoFrame
from websocket_signaling import WebSocketSignaling

# Logging instellen
logging.basicConfig(level=logging.INFO)

# Argumenten parseren
parser = argparse.ArgumentParser(description="WebRTC Webcam Sender")
parser.add_argument(
    "--signaling_server",
    type=str,
    default="ws://34.46.183.47:9000",
    help="WebSocket Signaling Server URL"
)
args = parser.parse_args()
SIGNALING_SERVER = args.signaling_server

# Resolutie
WIDTH, HEIGHT = 640, 480

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
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

            # Annotatie op frame
            cv2.putText(frame, f"Time: {timestamp_str}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            #print (f"data channel: {self.data_channel.readyState}")

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts, video_frame.time_base = await self.next_timestamp()

            #if self.frame_count % 30 == 0:
            #    logging.info(f"📡 Verzonden frame #{self.frame_count}")

            return video_frame

async def run(pc,signaling):


    # Datachannel aanmaken
    data_channel = pc.createDataChannel("meta")

    @data_channel.on("open")
    def on_open():
        logging.info("📡 Datachannel 'meta' is open")

    @data_channel.on("close")
    def on_close():
        logging.info("❌ Datachannel 'meta' is gesloten")

    @pc.on("icecandidate")
    def on_icecandidate(event):
        if event.candidate:
            logging.info(f"🧊 ICE-candidate verzonden: {event.candidate}")


    @pc.on("datachannel")
    def on_datachannel(channel):
        logging.info(f"📡 Ontvangen datachannel op sender: {channel.label}")
        @channel.on("open")
        def on_open():
            logging.info(f"✅ Datachannel '{channel.label}' is open!")
        @channel.on("close")
        def on_close():
            logging.info(f"❌ Datachannel '{channel.label}' gesloten.")



    # Alleen video zenden
    transceiver = pc.addTransceiver("video", direction="sendonly")
    video_codecs = [c for c in get_capabilities("video").codecs if c.name == "VP8"]
    transceiver.setCodecPreferences(video_codecs)

    # Video + metadata toevoegen
    pc.addTrack(CameraStreamTrack(data_channel))
    
    try:
        await signaling.connect()
        logging.info("✅ Verbonden met WebRTC Signaling Server... Wachten op client...")

        message = await signaling.receive()
        data = json.loads(message)

        if data["type"] == "SingleTimeSync":
            request_tx_time = data["requestTxTime"]
            response_tx_time = datetime.now().isoformat()

            await signaling.send(json.dumps({
                "type": "SingleTimeSyncResponse",
                "requestTxTime": request_tx_time,
                "responseTxTime": response_tx_time
            }))

            print ("Timeresponse send")


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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # WebRTC configuratie
        configuration = RTCConfiguration(iceServers=[
            RTCIceServer(urls="stun:34.46.183.47:3478"),
            RTCIceServer(
                urls=["turn:34.46.183.47:3478?transport=udp"],
                username="unused",
                credential="J0eS3cret123"
            )
        ])

        pc = RTCPeerConnection(configuration)
        signaling = WebSocketSignaling(SIGNALING_SERVER)

        loop.run_until_complete(run(pc,signaling))
    except KeyboardInterrupt:
        logging.info("🛑 Handmatige onderbreking. Programma wordt afgesloten.")
        capture.release()
