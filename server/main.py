import asyncio
from fastapi import FastAPI,File,UploadFile,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

app=FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to your specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client=genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(
            parts=[
                types.Part(
                     text=(
                    "You are a helpful voice assistant. "
                    "Keep your responses natural and conversational. "
                    "Speak clearly and concisely."
                )
                )
            ]
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig()

    )

@app.get("/")
def read():
    return "Hello from uv ok" 

async def sendget_gemini_response(session,websocket:WebSocket):
    """
    Continuously receive messages from Gemini.

    IMPORTANT:
    We don't use:
        async for message in session.receive()

    for the lifetime of the connection because receive()
    can terminate after turn_complete in some SDK versions.

    Instead, keep receiving directly.
    """
    while True:
        try:
            message=await session._receive();
        except Exception as e:
            print("session Error",e)
            break

        if message is None:
            print("Gemini returned None")
            break

        if(message.server_content and message.server_content.model_turn):
            parts=(message.server_content.model_turn.parts)

            if parts:
                for part in parts:
                    if part.inline_data:
                        audio_bytes=part.inline_data.data
                        await websocket.send_bytes(audio_bytes)
        
        if(message.server_content and message.server_content.turn_complete):
            print("Turn Complete")
            # await websocket.send_json({
                # "message":"Turn Complete",
            # })
        
        if(message.session_resumption_update):
            update=(message.session_resumption_update)

@app.websocket("/ws/live")
async def live_stream(websocket: WebSocket):
    await websocket.accept()
    print("🔥 BROWSER CONNECTED")
    try:
        async with client.aio.live.connect(
           model="gemini-3.1-flash-live-preview",
           config=config
           ) as session:
             
             response=asyncio.create_task(
                sendget_gemini_response(session,websocket)
             )

             while True:
                message=await websocket.receive()

                if(message.get("bytes") is not None):
                    audio_bytes=message["bytes"]

                    if not audio_bytes:
                        continue

                    await session.send_realtime_input(
                            audio=types.Blob(
                            data=audio_bytes,
                            mime_type="audio/pcm;rate=16000") )

    except WebSocketDisconnect:
         print("Browser disconnected")

    except Exception as e:
         print(f"Audio sending error: {e}")

    finally:
        print('Connection Closed')
