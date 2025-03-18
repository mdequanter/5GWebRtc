import asyncio
import websockets

clients = set()

async def signaling(websocket):  # ✅ Path toegevoegd
    clients.add(websocket)
    print(f"✅ Nieuwe client verbonden: {websocket.remote_address}")
    
    try:
        async for message in websocket:
            for client in clients:
                if client != websocket:
                    await client.send(message)
    except websockets.exceptions.ConnectionClosedError:
        print(f"⚠ Client {websocket.remote_address} heeft de verbinding verbroken.")
    finally:
        clients.remove(websocket)

async def start_server():
    print("🚀 WebSocket Signaling Server wordt gestart op ws://0.0.0.0:9000")
    async with websockets.serve(signaling, "0.0.0.0", 9000): 
        await asyncio.Future()  # Houd de server actief

if __name__ == "__main__":
    asyncio.run(start_server())
