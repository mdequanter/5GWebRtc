import asyncio
import json
import websockets

class WebSocketSignaling:
    """ WebRTC Signaling over WebSockets """

    def __init__(self, server_url):
        self.server_url = server_url
        self.websocket = None
        self.queue = asyncio.Queue()

    async def connect(self):
        """ Maakt verbinding met de WebSocket Signaling Server """
        try:
            self.websocket = await websockets.connect(self.server_url)
            asyncio.create_task(self._receive_messages())
            print(f"✅ Verbonden met {self.server_url}")
        except Exception as e:
            print(f"❌ Kan niet verbinden met signaling server: {e}")

    async def _receive_messages(self):
        """ Luistert naar inkomende berichten en slaat ze op in de queue """
        try:
            async for message in self.websocket:
                await self.queue.put(json.loads(message))
        except websockets.exceptions.ConnectionClosed:
            print("⚠ Signaling server heeft de verbinding gesloten.")

    async def send(self, message):
        """ Verstuur een bericht naar de signaling server """
        if self.websocket:
            await self.websocket.send(json.dumps(message))

    async def receive(self):
        """ Wacht op een bericht van de signaling server """
        return await self.queue.get()

    async def close(self):
        """ Verbreek de verbinding met de signaling server """
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
