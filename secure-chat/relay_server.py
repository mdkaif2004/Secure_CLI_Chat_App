import asyncio
import websockets
import json
import logging
from collections import defaultdict

# Configure logging (No plaintext logs in production, but needed for relay debug)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

rooms = defaultdict(set)

async def handler(websocket):
    current_room = None
    try:
        # 1. Wait for JOIN message
        message = await websocket.recv()
        data = json.loads(message)
        
        if data.get('type') != 'JOIN':
            await websocket.close(code=1002, reason="Protocol Error")
            return

        room_code = data.get('room')
        if not room_code:
            await websocket.close(code=1002, reason="Missing Room Code")
            return

        # 2. Enforce 2-Peer Limit
        if len(rooms[room_code]) >= 2:
            await websocket.close(code=4000, reason="Room Full")
            return

        # 3. Join Room
        rooms[room_code].add(websocket)
        current_room = room_code
        logging.info(f"Client joined room {room_code}. Total: {len(rooms[room_code])}")

        # Notify peers
        if len(rooms[room_code]) == 2:
            for ws in rooms[room_code]:
                await ws.send(json.dumps({"type": "PEER_FOUND"}))

        # 4. Relay Loop
        async for msg in websocket:
            # Broadcast to OTHER peer in room
            # In a real 2-peer strict system, we just send to the other socket.
            for ws in rooms[room_code]:
                if ws != websocket:
                    await ws.send(msg)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if current_room:
            rooms[current_room].discard(websocket)
            logging.info(f"Client left room {current_room}. Total: {len(rooms[current_room])}")
            # If anyone leaves, we should probably kill the session for the other too (Strict Mode)
            # For this prototype, we'll notify the remaining peer
            for ws in rooms[current_room]:
                await ws.send(json.dumps({"type": "PEER_LEFT"}))
            
            if not rooms[current_room]:
                del rooms[current_room]

async def main():
    print("Starting Secure Chat Relay on 0.0.0.0:8765")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
