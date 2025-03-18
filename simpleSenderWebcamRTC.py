import asyncio
import cv2
import logging
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
from websocket_signaling import WebSocketSignaling  # ✅ Gebruik aangepaste WebSocket Signaling

# Logging instellen
logging.basicConfig(level=logging.INFO)

# Signaling server
SIGNALING_SERVER = "ws://94.111.36.87:9000"  # ✅ Jouw bestaande signaling server

# Open de camera
capture = cv2.VideoCapture(0)
if not capture.isOpened():
    raise RuntimeError("❌ Kan de camera niet openen!")

# Instellingen voor resolutie
WIDTH, HEIGHT = 640, 480
capture.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)


class CameraStreamTrack(VideoStreamTrack):
    """ WebRTC VideoStream die frames van de camera haalt en verzendt. """
    
    def __init__(self):
        super().__init__()

    async def recv(self):
        ret, frame = capture.read()
        if not ret:
            logging.error("❌ Kan geen frame ophalen van de camera!")
            raise RuntimeError("❌ Kan geen frame ophalen van de camera!")

        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  

        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts, video_frame.time_base = self.next_timestamp()
        return video_frame


async def run():
    """ Verbindt met de WebRTC signaling server en verstuurt video. """
    
    signaling = WebSocketSignaling(SIGNALING_SERVER)  # ✅ Verbind met WebSocket Signaling Server
    pc = RTCPeerConnection()

    # Voeg de camera toe als een video-track
    video_track = CameraStreamTrack()
    pc.addTrack(video_track)

    try:
        # Maak verbinding met de signaling server
        await signaling.connect()
        logging.info("✅ Verbonden met WebRTC Signaling Server... Wachten op een client...")

        while True:
            obj = await signaling.receive()
            if isinstance(obj, RTCSessionDescription):
                logging.info("📡 WebRTC Client Verbonden! Start Streaming...")

                # Zet de Remote Description en stuur een antwoord (SDP)
                await pc.setRemoteDescription(obj)
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                await signaling.send(pc.localDescription)

            elif obj is None:
                break

    except Exception as e:
        logging.error(f"❌ Fout opgetreden: {e}")

    finally:
        # Sluit de WebRTC-verbinding correct af
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
