import asyncio
import cv2
import logging
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame

logging.basicConfig(level=logging.INFO)

TARGET_WIDTH, TARGET_HEIGHT = 640, 480  # Beeldresolutie aanpassen

class VideoReceiver:
    """ Klasse voor het ontvangen en tonen van WebRTC-videostream. """
    def __init__(self):
        self.fps_display = 0
        self.message_count = 0
        self.last_time = asyncio.get_event_loop().time()

    def process_frame(self, frame: VideoFrame):
        """ Converteert WebRTC-frame naar OpenCV-afbeelding en toont het. """
        image = frame.to_ndarray(format="rgb24")
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)  # WebRTC gebruikt RGB, OpenCV BGR
        image = cv2.resize(image, (TARGET_WIDTH, TARGET_HEIGHT))

        # FPS-berekening
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


async def run():
    """ Verbindt met WebRTC-server en toont video. """
    signaling = TcpSocketSignaling("94.111.36.87", 9000)  # Pas IP aan
    pc = RTCPeerConnection()
    receiver = VideoReceiver()

    @pc.on("track")
    def on_track(track):
        print(f"📡 Ontvangen video track: {track.kind}")

        if track.kind == "video":
            async def receive_video():
                while True:
                    frame = await track.recv()
                    receiver.process_frame(frame)

            asyncio.create_task(receive_video())

    await signaling.connect()
    print("✅ Verbonden met WebRTC Signaling Server... Wachten op video...")

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    await signaling.send(pc.localDescription)

    obj = await signaling.receive()
    if isinstance(obj, RTCSessionDescription):
        await pc.setRemoteDescription(obj)

    await pc.wait_for_connection_state("closed")
    await signaling.close()

if __name__ == "__main__":
    asyncio.run(run())
