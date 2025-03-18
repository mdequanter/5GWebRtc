import asyncio
import cv2
import logging
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.signaling import WebSocketSignaling
from av import VideoFrame

logging.basicConfig(level=logging.INFO)

SIGNALING_SERVER = "ws://94.111.36.87:9000"  # ✅ Verbindt met jouw bestaande signaling server

# Open de camera
capture = cv2.VideoCapture(0)
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

        frame = cv2.resize(frame, (width, height))  
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  

        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts, video_frame.time_base = self.next_timestamp()
        return video_frame


async def run():
    """ Verbindt met de WebRTC signaling server en verstuurt video. """
    signaling = WebSocketSignaling(SIGNALING_SERVER)  # ✅ Gebruik bestaande signaling server
    pc = RTCPeerConnection()
    pc.addTrack(CameraStreamTrack())

    await signaling.connect()
    print("✅ Verbonden met WebRTC Signaling Server... Wachten op een client...")

    while True:
        obj = await signaling.receive()
        if isinstance(obj, RTCSessionDescription):
            print("📡 WebRTC Client Verbonden! Start Streaming...")

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
