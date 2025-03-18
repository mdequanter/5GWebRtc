import asyncio
import cv2
import logging
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, VideoStreamTrack, RTCSessionDescription
from av import VideoFrame
from websocket_signaling import WebSocketSignaling  # ✅ Gebruik aangepaste WebSocket Signaling
import time
from aiortc.codecs import get_capabilities

# Logging instellen
logging.basicConfig(level=logging.INFO)

SIGNALING_SERVER = "ws://94.111.36.87:9000"  # ✅ Jouw bestaande signaling server

# Open de camera
# capture = cv2.VideoCapture(0)
capture = cv2.VideoCapture(0)

if not capture.isOpened():
    raise RuntimeError("❌ Kan de camera niet openen!")

# Instellingen voor resolutie
WIDTH, HEIGHT = 640, 480
#capture.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
#capture.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)


class CameraStreamTrack(VideoStreamTrack):
    """ WebRTC VideoStream die frames van de camera haalt en verzendt. """


    
    def __init__(self):
        super().__init__()
        self.start_time = time.time()
        self.frame_count = 0  # ✅ Zorg ervoor dat frame_count correct is gedefinieerd
        logging.info("✅ Video track is toegevoegd aan peer connection!")

    async def next_timestamp(self):
        """ Genereert een correcte timestamp voor het frame. """
        self.frame_count += 1
        timestamp = int((time.time() - self.start_time) * 90000)
        return timestamp, 90000  # 90 kHz tijdsbase        

    async def recv(self):
        """ Leest een frame van de camera en stuurt het naar de client. """
        logging.error("Start lezen frames")

        ret, frame = capture.read()
        if not ret:
            logging.error("❌ Kan geen frame ophalen van de camera!")
            raise RuntimeError("❌ Kan geen frame ophalen van de camera!")

        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  

        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts, video_frame.time_base = await self.next_timestamp()

        #logging.info("📡 Frame gegenereerd en verzonden naar client")  # ✅ Nu wordt logging correct uitgevoerd
        return video_frame

async def run():
    """ Verbindt met de WebRTC signaling server en verstuurt video. """
    
    configuration = RTCConfiguration(iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")])
    signaling = WebSocketSignaling(SIGNALING_SERVER)  # ✅ Verbind met WebSocket Signaling Server
    pc = RTCPeerConnection(configuration)

    # ✅ Voeg de camera toe als een video-track
    #pc.addTransceiver("video", direction="sendonly")
    

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

                # Zet de Remote Description en stuur een antwoord (SDP)
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
