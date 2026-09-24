from fastapi import FastAPI,File,UploadFile,WebSocket
from google.genai import types

__all__=["receive_audio"]

async def receive_audio(session,websocket: WebSocket):
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
