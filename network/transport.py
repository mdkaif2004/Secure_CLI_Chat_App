import asyncio
import websockets
import json
import logging

class TransportLayer:
    def __init__(self, uri="ws://localhost:8765"):
        self.uri = uri
        self.websocket = None
        self.on_message_callback = None
        self.on_peer_found_callback = None
        self.on_peer_lost_callback = None

    async def connect(self, room_code: str):
        try:
            self.websocket = await websockets.connect(self.uri)
            await self.websocket.send(json.dumps({
                "type": "JOIN",
                "room": room_code
            }))
            # Start listening loop
            asyncio.create_task(self.listen())
            return True
        except Exception as e:
            # logging.error(f"Connection failed: {e}") 
            return False

    async def listen(self):
        try:
            async for message in self.websocket:
                # Determine if it's a control message or data blob
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if msg_type == "PEER_FOUND":
                        if self.on_peer_found_callback:
                            self.on_peer_found_callback()
                    elif msg_type == "PEER_LEFT":
                        if self.on_peer_lost_callback:
                            self.on_peer_lost_callback()
                    elif msg_type == "SIGNAL":
                         # Handshake signal (e.g. public key)
                         if self.on_message_callback:
                             await self.on_message_callback(data)
                    else:
                        # Maybe raw encrypted blob? 
                        # For simplicity, we wrap everything in JSON envelopes in this prototype
                        pass
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            if self.on_peer_lost_callback:
                self.on_peer_lost_callback()

    async def send_signal(self, payload: dict):
        if self.websocket:
            wrapped = {"type": "SIGNAL", **payload}
            await self.websocket.send(json.dumps(wrapped))

    async def send_encrypted_blob(self, blob: str):
        # We send the encrypted string (base64 encoded usually) inside a signal for now
        # or as a separate type.
        if self.websocket:
            await self.websocket.send(json.dumps({
                "type": "SIGNAL",
                "payload": blob,
                "kind": "MSG" 
            }))

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
