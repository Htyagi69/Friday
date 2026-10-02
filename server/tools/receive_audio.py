import asyncio
import base64
import json

from fastapi import FastAPI,File,UploadFile,WebSocket
from google.genai import types

__all__=["receive_audio"]

async def receive_audio(session,websocket: WebSocket,manager):
    while True:
        message = await websocket.receive()
        if message.get("bytes") is not None:
            audio_bytes = message["bytes"]
            if not audio_bytes:
                continue
            await session.send_realtime_input(
                audio=types.Blob(
                    data=audio_bytes,
                    mime_type="audio/pcm;rate=16000"
                )
            )
        elif message.get("text") is not None:
            data=json.loads(message["text"])
            if data.get("type")=="camera_frame":
                frame_bytes=base64.b64decode(data["data"])
                if manager.camera_queue.full():
                    try:
                        manager.camera_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                await manager.camera_queue.put({
                    "mime_type": "image/jpeg",
                    "data": frame_bytes
                })

            elif data.get("type")=="screen_frame":
                frame_bytes=base64.b64decode(data["data"])
                if manager.screen_queue.full():
                    try:
                        manager.screen_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                await manager.screen_queue.put({
                    "mime_type": "image/jpeg",
                    "data": frame_bytes
                })