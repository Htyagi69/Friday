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

switch_session_tool = types.FunctionDeclaration(
    name="switch_session",
    description="Switch to a previous conversation by its exact title.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title": types.Schema(
                type=types.Type.STRING,
                description="The exact title of the conversation to continue."
            )
        },
        required=["title"]
    )
)

client=genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

initial_limit=4

class ConversationManager:
       def __init__(self):
                 self.active_session_id=None
                 self.gemini_session=None
                 self.switch_event=asyncio.Event()
                 self.pending_context = ""
                 self.title_generated=False
       
       async def create_session(self,title):
           session=await db.session.create(
               data={"title":title}
           )
           self.active_session_id=str(session.id)
           return self.active_session_id
   
       async def switch_session(self,title):
               session=await db.session.find_first(
                    where={"title":title}
                )   
               if not session: 
                    return {
                    "success":False,
                    "message":f"session {title} not found"  
                    }
               self.active_session_id=str(session.id)
               print(f"🔄 Switching to session: "f"{session.title} ({self.active_session_id})")
               self.pending_context = await self.load_context(self.active_session_id)
               self.switch_event.set()

               return {
                    "success":True,
                    "message":f"Switched to {session.title}"
               }
   
       async def load_context(self,session_id):
              messages=await db.messages.find_many(
                  where={
                      "sessionId":session_id
                  },
                  take=20,
                  order={
                      "createdAt":'desc',
                  }
              )
              messages = list(reversed(messages))

              if not messages:
                  return ""
      
              conversation = []
      
              for message in messages:
                  conversation.append(
                      f"{message.role}: {message.content}"
                  )
      
              return "\n".join(conversation)
   
       async def save_message(self,role,content):
            if not self.active_session_id:
                  return

            if not content or not content.strip():
                    return

            message=await db.messages.create(
                    data={
                              "sessionId":self.active_session_id,
                              "role":role,
                              "content":content 
                         }
                        )
            print(f"{role} message saved",message.id)

       async def watch_session_switch(self):
            await self.switch_event.wait()
            self.switch_event.clear()
            print("Switching To:",self.active_session_id)


async def get_Sessions():
   try:
      sessions=await db.session.find_many()
      return [
          {
              "title":session.title,
              "id":str(session.id),
          } for session in sessions
      ]
    #   print(sessionHistory)

   except Exception as e:
       print("error",e)
       return


def create_config(manager,session_history,session_context=""):
   session_names = "\n".join(
        session["title"]
        for session in session_history
    )
   config = types.LiveConnectConfig(
           response_modalities=["AUDIO"],
           system_instruction=types.Content(
               parts=[
                   types.Part(
                      text=f"""
You are Friday, a helpful voice assistant.

Keep your responses natural and conversational.

Speak clearly and concisely.

Available previous conversations:

--- SESSIONS ---
{session_names}
--- END SESSIONS ---

Current conversation context:

--- CURRENT CONTEXT ---
{session_context}
--- END CURRENT CONTEXT ---

If the user asks to continue or go back to
another previous conversation, use the session
switching tool.

Do not mention internal session IDs.

Do not expose implementation details.
"""
                   )
               ]
           ),
          tools=[
            types.Tool(
                function_declarations=[
                    switch_session_tool
                ]
            )
        ],
           input_audio_transcription=types.AudioTranscriptionConfig(),
           output_audio_transcription=types.AudioTranscriptionConfig()
   
       )
   return config

 
@app.get("/")
def read():
    return "Hello from uv ok" 


async  def get_session_title(manager:ConversationManager,messages:list):
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
       
       response = await client.aio.models.generate_content(
               model="gemini-2.5-flash",
               contents=prompt
           )
       title= response.text.strip()
       sessionId=await manager.create_session(title)
       return sessionId

async def sendget_gemini_response(manager,session,websocket:WebSocket,tempMessages:list):
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

        if message.tool_call:
           print(" TOOL CALL:", message.tool_call)
           for function_call in message.tool_call.function_calls:
               if function_call.name == "switch_session":
                    title = function_call.args.get("title")
                    # print(" Requested session:", title)
                    result = await manager.switch_session(title)
                    # print(" Switch result:", result)
                    await session.send_tool_response(
                        function_responses=[
                            types.FunctionResponse(
                                name="switch_session",
                                id=function_call.id,
                                response=result
                            )
                        ]
                    )
           continue

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
                if not manager.title_generated:
                 if user_transcript.strip() or jarvis_transcript.strip(): 
                   tempMessages.append({
                      "user":user_transcript,
                      "jarvis":jarvis_transcript,
                  })
                     
                if len(tempMessages)==initial_limit:
                    sessionId=await get_session_title(manager,tempMessages)
                    manager.title_generated=True

                    #initial messages
                    for message in  tempMessages:
                         await db.messages.create(
                              data={
                                     "sessionId":sessionId,
                                     "role":"user",
                                     "content":message["user"] 
                                 }
                         )
                         await db.messages.create(
                              data={
                                     "sessionId":sessionId,
                                     "role":"jarvis",
                                     "content":message["jarvis"] 
                                 }
                         )

                if manager.title_generated and user_transcript:
                     await manager.save_message("user",user_transcript)
                if manager.title_generated and jarvis_transcript:
                     await manager.save_message("jarvis",jarvis_transcript)

                user_transcript=""
                jarvis_transcript=""
            
            # if(message.session_resumption_update):
            #     update=(message.session_resumption_update)


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

@app.websocket("/ws/live")
async def live_stream(websocket: WebSocket):
    await websocket.accept()

    manager=ConversationManager()
    print("🔥 BROWSER CONNECTED")
    try:
        session_history=await get_Sessions()
        tempMessages=[]
        session_context = ""
        while True:
           config=create_config(manager,session_history,session_context)
           
           async with client.aio.live.connect(
              model="gemini-3.1-flash-live-preview",
              config=config
              ) as session:
                manager.gemini_session=session
                response=asyncio.create_task(
                   sendget_gemini_response(manager,session,websocket,tempMessages)
                )
                audio_task = asyncio.create_task(receive_audio(session,websocket))
                switch_task = asyncio.create_task(manager.watch_session_switch())
                done, pending = await asyncio.wait(
                    [
                        response,
                        audio_task,
                        switch_task
                    ],
                    return_when=asyncio.FIRST_COMPLETED
                )
                if switch_task in done:
                    print(" Session switch detected")
                    session_context = (manager.pending_context)
                    # print(" New context:",session_context)
                    # Cancel old Gemini tasks
                    response.cancel()
                    audio_task.cancel()

                    await asyncio.gather(
                        response,
                        audio_task,
                        return_exceptions=True
                    )
                    continue

                for task in pending:
                    task.cancel()

                await asyncio.gather(
                    *pending,
                    return_exceptions=True
                )

                for task in done:
                    if task is not switch_task:
                        exception = task.exception()
                        if exception:
                            raise exception
                break

    except WebSocketDisconnect:
         print("Browser disconnected")

    except Exception as e:
         print(f"Audio sending error: {e}")

    finally:
        print('Connection Closed')




