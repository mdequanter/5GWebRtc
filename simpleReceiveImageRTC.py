import asyncio
import cv2
import logging
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import VideoFrame
from websocket_signaling import WebSocketSignaling  # ✅ Gebruik aangepaste WebSocket Signaling
import time

# Logging instellen
logging.basicConfig(level=logging.INFO)

SIGNALING_SERVER = "ws://94.111.36.87:9000"  # ✅ Jouw bestaande signaling server
TARGET_WIDTH, TARGET_HEIGHT = 640, 480  # Consistente weergavegrootte


class DummyVideoTrack(MediaStreamTrack):
    """ Dummy video track om WebRTC offer te laten werken. """

    kind = "video"

    def __init__(self):
        super().__init__()
        self.start_time = time.time()
        self.frame_count = 0

    async def recv(self):
        """ Lege zwarte frame verzenden als dummy video track. """
        frame = VideoFrame(width=640, height=480, format="rgb24")
        frame.pts, frame.time_base = self.next_timestamp()
        return frame

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
        """ Converteert WebRTC-frame naar OpenCV-afbeelding en toont het. """
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

        # Overlay FPS
        cv2.putText(image, f"FPS: {self.fps_display}", (10, 470),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2, cv2.LINE_AA)

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
    
    configuration = RTCConfiguration(iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")])
    signaling = WebSocketSignaling(SIGNALING_SERVER)  # ✅ Gebruik bestaande signaling server
    pc = RTCPeerConnection(configuration)
  

    pc.addTransceiver("video", direction="recvonly", codec_preferences=["video/VP8"])

  
    receiver = VideoReceiver()



    # ✅ Dummy video track toevoegen om een correct offer te maken
    dummy_video_track = DummyVideoTrack()
    pc.addTrack(dummy_video_track)

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
                        logging.error(f"❌ Fout bij video-ontvangst: {e}", exc_info=True)

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

        await asyncio.sleep(10)  # Laat de verbinding open om video te ontvangen

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
