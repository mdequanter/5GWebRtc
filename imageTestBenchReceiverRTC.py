import asyncio
import cv2
import logging
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import VideoFrame
from websocket_signaling import WebSocketSignaling  # ✅ Gebruik aangepaste WebSocket Signaling
import time
import argparse

# Logging instellen
logging.basicConfig(level=logging.INFO)

# Set up argument parser
parser = argparse.ArgumentParser(
    description="Receive images via WebSocket and record network parameters."
)

parser.add_argument(
    "--signaling_server",
    type=str,
    default="ws://34.46.183.47:9000",
    help="WebSocket Signaling Server URL (default: ws://34.58.161.254:9000)"
)


args = parser.parse_args()

SIGNALING_SERVER = args.signaling_server

TARGET_WIDTH, TARGET_HEIGHT = 640, 480  # Consistente weergavegrootte


class DummyVideoTrack(MediaStreamTrack):
    """ Dummy video track om WebRTC offer te laten werken. """

    kind = "video"

    def __init__(self):
        super().__init__()
        self.start_time = time.time()
        self.frame_count = 0

    async def recv(self):
            try:
                frame = next(self.frames)
            except StopIteration:
                await asyncio.sleep(1)
                raise asyncio.CancelledError("✅ Alle frames zijn verzonden.")

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts, video_frame.time_base = await self.next_timestamp()

            # ✅ Voeg metadata toe aan frame
            width, height = video_frame.width, video_frame.height
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            metadata = {
                "setup_description": SIGNALING_SERVER,
                "frame_id": str(self.frame_count),
                "type": "test",
                "filename": "image.jpg",
                "timestamp": timestamp,
                "resolution": f"{width}x{height}",
                "jpeg_quality": "auto",
                "size_kb": "n/a"
            }
            video_frame.metadata = metadata

            if self.frame_count % 30 == 0:
                logging.info(f"📡 Verzonden frame #{self.frame_count}")
            await asyncio.sleep(FRAME_INTERVAL)
            return video_frame
    def next_timestamp(self):
        """ Genereert een correcte timestamp voor het frame. """
        self.frame_count += 1
        timestamp = int((time.time() - self.start_time) * 90000)
        return timestamp, 90000  # 90 kHz tijdsbase

class VideoReceiver:
    """ Klasse voor het ontvangen en tonen van WebRTC-videostream. """
    
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

        metadata = getattr(frame, 'metadata', {})

        # ✅ Overlay van metadata op het scherm
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
    """ Wacht tot de ICE-verbinding correct tot stand komt. """
    for _ in range(10):  # Geef maximaal 10 seconden om verbinding te maken
        if pc.iceConnectionState in ["connected", "completed"]:
            logging.info("✅ ICE-verbinding tot stand gebracht!")
            return True
        await asyncio.sleep(1)
    logging.error("❌ ICE-verbinding is mislukt!")
    return False


async def run():
    """ Verbindt met de WebRTC-server en toont video. """
    
    #configuration = RTCConfiguration(iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")])

    configuration = RTCConfiguration(iceServers=[
        RTCIceServer(urls="stun:34.46.183.47:3478"),  # ← jouw VM IP
        RTCIceServer(
            urls=["turn:34.46.183.47:3478?transport=udp"],
            username="unused",
            credential="J0eS3cret123"
        )
    ])


    signaling = WebSocketSignaling(SIGNALING_SERVER)  # ✅ Gebruik bestaande signaling server
    pc = RTCPeerConnection(configuration)
    receiver = VideoReceiver()
    dummy_video_track = DummyVideoTrack()
    pc.addTrack(dummy_video_track)

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
                        continue
                        logging.info(f"❌ Fout bij video-ontvangst: {e}", exc_info=True)

            asyncio.create_task(receive_video())
    try:
        await signaling.connect()
        logging.info("✅ Verbonden met WebRTC Signaling Server... Verstuur offer naar sender...")

        # ✅ Nu kan een offer correct worden gecreëerd
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await signaling.send({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})

        # ✅ Wachten op antwoord van de sender (server)
        obj = await signaling.receive()
        if isinstance(obj, dict) and "sdp" in obj:
            await pc.setRemoteDescription(RTCSessionDescription(sdp=obj["sdp"], type=obj["type"]))

        # ✅ Wachten tot ICE is verbonden
        if not await wait_for_ice(pc):
            raise Exception("ICE-verbinding mislukt!")

        logging.info("✅ WebRTC-verbinding is succesvol tot stand gekomen!")

        # await asyncio.sleep(30)  # Laat de verbinding open om video te ontvangen
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
