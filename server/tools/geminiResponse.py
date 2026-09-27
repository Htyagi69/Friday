from google.genai import types
from fastapi import FastAPI,File,UploadFile,WebSocket,WebSocketDisconnect
from conversation.conversation import db
from tools.get_session_title import get_session_title

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
set_reminder_tool = types.FunctionDeclaration(
    name="set_reminder",
    description="set the reminder for future by storing it in databse",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title": types.Schema(
                type=types.Type.STRING,
                description="The exact title for reminder."
            ),
            "message": types.Schema(
                type=types.Type.STRING,
                description="information about reminder"
            ),
            "timeStamp": types.Schema(
                type=types.Type.STRING,
                description="The time at which reminder should remind."
            )
        },
        required=["title","message","timeStamp"]
    )
)

initial_limit=4

__all__=["sendget_gemini_response","create_config"]

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
               elif function_call.name == "set_reminder":
                    title = function_call.args.get("title")
                    message = function_call.args.get("message")
                    timeStamp = function_call.args.get("timeStamp")
                    # print(" Requested session:", title)
                    result = await manager.set_reminder(title,message,timeStamp)
                    # print(" Switch result:", result)
                    await session.send_tool_response(
                        function_responses=[
                            types.FunctionResponse(
                                name="set_reminder",
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
                await websocket.send_text(user_transcript)
                await websocket.send_text(jarvis_transcript)
                user_transcript=""
                jarvis_transcript=""
            
            # if(message.session_resumption_update):
            #     update=(message.session_resumption_update)


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
                    switch_session_tool,set_reminder_tool
                ]
            )
        ],
           input_audio_transcription=types.AudioTranscriptionConfig(),
           output_audio_transcription=types.AudioTranscriptionConfig()
   
       )
   return config