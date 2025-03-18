import asyncio
import cv2
import json
import logging
import os
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame

logging.basicConfig(level=logging.INFO)

# Open de camera
capture = cv2.VideoCapture(0)

# Instellingen voor resolutie
width, height = 640, 480
capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)


class CameraStreamTrack(VideoStreamTrack):
    """ Een WebRTC-videostream die frames van de camera haalt. """
    def __init__(self):
        super().__init__()

    async def recv(self):
        ret, frame = capture.read()
        if not ret:
            raise RuntimeError("❌ Kan geen frame ophalen van de camera!")

        frame = cv2.resize(frame, (width, height))  # Zorg ervoor dat de resolutie correct is
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # OpenCV gebruikt BGR, maar WebRTC gebruikt RGB

        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts, video_frame.time_base = self.next_timestamp()
        return video_frame


async def run():
    """ Start een WebRTC server en wacht op een verbinding. """
    signaling = TcpSocketSignaling("0.0.0.0", 9000)  # Gebruik een TCP-signaling server
    pc = RTCPeerConnection()

    # Voeg de camera toe als video-track
    pc.addTrack(CameraStreamTrack())

    await signaling.connect()
    print("✅ Wachten op een WebRTC client...")

    while True:
        obj = await signaling.receive()
        if isinstance(obj, RTCSessionDescription):
            print("📡 WebRTC verbinding ontvangen...")

            await pc.setRemoteDescription(obj)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            await signaling.send(pc.localDescription)

        elif obj is None:
            break

    await pc.close()
    await signaling.close()


if __name__ == "__main__":
    asyncio.run(run())
