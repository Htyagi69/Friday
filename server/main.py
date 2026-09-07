import asyncio
from typing import Any
from fastapi import FastAPI,File,UploadFile,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
import os
from uuid import uuid4
from prisma import Prisma
from prisma.models import Session,Messages
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

db=Prisma()

@asynccontextmanager
async def lifespan(app:FastAPI):
    await  db.connect()
    yield
    await db.disconnect()

app=FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to your specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client=genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


async def get_Sessions():
   try:
      sessions=await db.session.find_many()
      return [
          {
              "title":session.title,
          } for session in sessions
      ]
    #   print(sessionHistory)

   except Exception as e:
       print("error",e)
       return


def create_config(session_history):
   config = types.LiveConnectConfig(
           response_modalities=["AUDIO"],
           system_instruction=types.Content(
               parts=[
                   types.Part(
                        text=f"""
   You are Friday, a helpful voice assistant.
   
   Keep your responses natural and conversational.
   Speak clearly and concisely.
   
   The user has these previous conversations:
   
   --- SESSION HISTORY ---
   {session_history}
   --- END SESSION HISTORY ---
   
   If the user asks about a previous conversation, use the
   session names to identify which conversation they are referring to.
   
   Do not mention internal session IDs to the user.
   """
                   )
               ]
           ),
           input_audio_transcription=types.AudioTranscriptionConfig(),
           output_audio_transcription=types.AudioTranscriptionConfig()
   
       )
   return config
   

@app.get("/")
def read():
    return "Hello from uv ok" 

@app.post("/sessions")
async def create_session():
       session_id=uuid4()

       session=await db.session.create(
           data={
               "title":"New Conversation"
           })
       return {
           "sessionId":str(session.id)
       }

async def sendget_gemini_response(session,websocket:WebSocket,session_id:str,tempMessages:list,title_generated:bool):
    """
    Continuously receive messages from Gemini.

    IMPORTANT:
    We don't use:
        async for message in session.receive()

    for the lifetime of the connection because receive()
    can terminate after turn_complete in some SDK versions.

    Instead, keep receiving directly.
    """
    user_transcript=""
    jarvis_transcript=""

    while True:
        try:
            message=await session._receive();
        except Exception as e:
            print("session Error",e)
            break

        if message is None:
            print("Gemini returned None")
            break
        server_content=message.server_content

        if  server_content:
            if server_content.input_transcription:
                text=server_content.input_transcription.text

                if text:
                    user_transcript+=text
            if server_content.output_transcription:
                text=server_content.output_transcription.text

                if text:
                    jarvis_transcript+=text

            if(message.server_content.model_turn):
                parts=(message.server_content.model_turn.parts)
    
                if parts:
                    for part in parts:
                        if part.inline_data:
                            audio_bytes=part.inline_data.data
                            await websocket.send_bytes(audio_bytes)
            
            if(message.server_content.turn_complete):
                print("Turn Complete")
                print("User:",user_transcript)
                print("Jarvis:",jarvis_transcript)
                if not title_generated:
                 if user_transcript.strip() or jarvis_transcript.strip(): 
                   tempMessages.append({
                      "User":user_transcript,
                      "Jarvis":jarvis_transcript,
                  })
                if len(tempMessages)==4:
                    await get_session_title(tempMessages,session_id)
                    title_generated=True
                if user_transcript.strip():
                    user_msg=await db.messages.create(
                        data={
                          "sessionId":session_id,
                          "role":"user",
                          "content":user_transcript 
                        }
                    )
                    print("user message saved",user_msg.id)
                if jarvis_transcript.strip():
                    jarvis_msg=await db.messages.create(
                        data={
                          "sessionId":session_id,
                          "role":"assistant",
                          "content":jarvis_transcript 
                        }
                    )
                    print("Jarvis message saved",jarvis_msg.id)
                # await websocket.send_json({
                    # "message":"Turn Complete",
                # })
                user_transcript=""
                jarvis_transcript=""
            
            if(message.session_resumption_update):
                update=(message.session_resumption_update)


async  def get_session_title(messages:list,sessionId:str):
       prompt = f"""
       Generate a short title for this conversation.
       
       User,Assistant:
       {messages}
       
       Rules:
       - Maximum 5 words
       - No quotes
       - No punctuation
       - Describe the main topic
       - Do not use "conversation", "chat", or "session"
       """
       
       title = await client.aio.models.generate_content(
               model="gemini-2.5-flash",
               contents=prompt
           )
       if title.text:
           await db.session.update(where={"id":sessionId},
           data={
               "title":title.text.strip()
           })


@app.websocket("/ws/live/{sessionId}")
async def live_stream(websocket: WebSocket,sessionId:str):
    await websocket.accept()
    print("🔥 BROWSER CONNECTED")
    try:
        session_history=await get_Sessions()
        config=create_config(session_history)
        tempMessages=[]
        title_generated=False
        async with client.aio.live.connect(
           model="gemini-3.1-flash-live-preview",
           config=config
           ) as session:
             response=asyncio.create_task(
                sendget_gemini_response(session,websocket,sessionId,tempMessages,title_generated)
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
                            mime_type="audio/pcm;rate=16000"))

    except WebSocketDisconnect:
         print("Browser disconnected")

    except Exception as e:
         print(f"Audio sending error: {e}")

    finally:
        print('Connection Closed')
