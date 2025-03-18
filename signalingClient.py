import asyncio
import websockets

async def test_client():
    async with websockets.connect("ws://192.168.68.2:9000") as websocket:
        await websocket.send("Hallo, Signaling Server!")
        print(await websocket.recv())

asyncio.run(test_client())
