from google.genai import types
from fastapi import FastAPI,File,UploadFile,WebSocket,WebSocketDisconnect
from conversation.conversation import db
from tools.email_reader import get_unread_emails
from tools.get_session_title import get_session_title


nativeSpeakers={
    "Puck"      :     "United States (American)Upbeat, sharp, witty, and energetic",
    "Charon"    :     "United States (American)Deep, mysterious, and informative",
    "Kore"      :     "United States (American)Warm, friendly, and firm",
    "Fenrir"    :     "United States (American)Strong, confident, and excitable",
    "Aoede"     :     "United States (American)Clear, melodic, and breezy",
    "Zephyr"    :     "United States (American)Bright and animated",
    "Orus"      :     "United States (American)Firm and structured",
    "Autonoe"   :     "United States (American)Bright and engaging",
    "Umbriel"   :     "United States (American)Easy-going and relaxed",
    "Erinome"   :     "United States (American)Clear and precise",
    "Laomedeia" :     "United States (American)Upbeat and positive",
    "Schedar"   :     "United States (American)Even and balanced",
    "Achird"    :     "United States (American)Friendly and welcoming",
    "Capella"   :     "United Kingdom (British)Serene, clear, and higher-pitched",
    "Violet"    :     "United Kingdom (British)Formal, steady, and traditionally polite",
    "Calathea"  :     "Australia (Aussie)Bright, relaxed, and conversational"
}

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
get_camera_access_tool = types.FunctionDeclaration(
    name="start_camera",
    description="a function that opens up the camera of the device provide the screenshots of outside world",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
             "facing": types.Schema(
                       type=types.Type.STRING,
                       description="this field is decide the facingMode of camera either back or front"
                    )},
    )
)
stop_camera_access_tool = types.FunctionDeclaration(
    name="stop_camera",
    description="a function that closes the camera of the device",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={}
    )
)
get_screen_access_tool = types.FunctionDeclaration(
    name="get_screen",
    description="a function that helps to see the entire screen of the device",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={},
    )
)
stop_screen_share_tool = types.FunctionDeclaration(
    name="stop_screen_share",
    description="a function that closes screen Sharing",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={},
    )
)
email_summarizer_tool = types.FunctionDeclaration(
    name="get_unread_emails",
    description="fetching the unread emails based on demand and get the insight out of it",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "num_of_mails": types.Schema(
                type=types.Type.INTEGER,
                description="denotes the number of  mails to fetch"
            )
        },
        required=["num_of_mails"]
    )
)
set_reminder_tool = types.FunctionDeclaration(
    name="set_reminder",
    description="""
    Schedule a reminder for the user.

    The user's timezone is Asia/Kolkata (IST, UTC+05:30).

    For relative reminders:
    - Use schedule_type='relative'.
    - Set delay_seconds to the requested duration in seconds.
    - Examples: 1 minute = 60, 10 minutes = 600.
    - Do not calculate or guess the absolute timestamp.

    For clock-time reminders:
    - Use schedule_type='absolute'.
    - Set local_datetime to the requested date and time in
      YYYY-MM-DDTHH:MM:SS format, without a timezone suffix.
    - Interpret the date and time in Asia/Kolkata.
    - Example: 11:44 PM on September 27, 2026 is
      2026-09-27T23:44:00.

    Always use the current date when resolving today or tomorrow.
    Never invent a date or time if the request is ambiguous.
    """,
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
            "schedule_type": types.Schema(
                type= "STRING",
                enum= ["relative", "absolute"]
            ),
             "delay_seconds": types.Schema(
                type= "INTEGER",
                description= "Required for relative reminders."
             ),
             "local_datetime": types.Schema(
                type= "STRING",
                description= "Required for absolute reminders; local IST time."
             )
        },
        required=["title","message","schedule_type"]
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
                    schedule_type = function_call.args.get("schedule_type")
                    delay_seconds = function_call.args.get("delay_seconds")
                    local_datetime = function_call.args.get("local_datetime")
                    # print(" Requested session:", title)
                    result = await manager.set_reminder(title,message,schedule_type,delay_seconds,local_datetime)
                    # print("title:", title)
                    # print("message:", message)
                    # print("schedule_type:", schedule_type)
                    # print("delay_seconds:", delay_seconds)
                    # print("local_datetime:", local_datetime)
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
               elif function_call.name == "get_unread_emails":
                    total = function_call.args.get("num_of_mails")
                
                    print(" TOOL START")
                    print(" Requested mails:", total)
                
                    result = get_unread_emails(total)
                
                    print(" Gmail result received")
                    print(result)
                
                    print(" Sending tool response to Gemini...")
                
                    await session.send_tool_response(
                        function_responses=[
                            types.FunctionResponse(
                                name="get_unread_emails",
                                id=function_call.id,
                                response={
                                    "emails": result or "No unread emails found."
                                }
                            )
                        ]
                    )

                    print(" Tool response sent successfully")

               elif function_call.name == "start_camera":
                
                    print(" TOOL START")
                    facing=function_call.args.get("facing","front")
                    print(f"Requested camera: {facing}")
                    result =await manager.start_camera(websocket,session,facing)
                
                    print("camera_task initiated")
                    print(result)
                                
                    await session.send_tool_response(
                        function_responses=[
                            types.FunctionResponse(
                                name="start_camera",
                                id=function_call.id,
                                response=result
                            )
                        ]
                    )

                    print(" Tool response sent successfully")
               elif function_call.name == "get_screen":
                
                    print(" TOOL START")
                    result =await manager.get_screen(websocket,session)
                
                    print("screen Share initiated")
                    print(result)
                                
                    await session.send_tool_response(
                        function_responses=[
                            types.FunctionResponse(
                                name="get_screen",
                                id=function_call.id,
                                response=result
                            )
                        ]
                    )

                    print(" Tool response sent successfully")

               elif function_call.name == "stop_camera":
                
                    print(" TOOL START")
                    result =await manager.stop_camera(websocket)
                
                    print("camera_task cancel")
                    print(result)
                                
                    await session.send_tool_response(
                        function_responses=[
                            types.FunctionResponse(
                                name="stop_camera",
                                id=function_call.id,
                                response=result
                            )
                        ]
                    )

                    print(" Tool response sent successfully")
               elif function_call.name == "stop_screen_share":
                
                    print(" TOOL START")
                    result =await manager.stop_screen_share(websocket)
                
                    print("screen_task cancel")
                    print(result)
                                
                    await session.send_tool_response(
                        function_responses=[
                            types.FunctionResponse(
                                name="stop_screen_share",
                                id=function_call.id,
                                response=result
                            )
                        ]
                    )

                    print(" Tool response sent successfully")
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
           speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name="Zephyr"
            )
        )
    ),
          tools=[
            types.Tool(
                function_declarations=[
                    switch_session_tool,set_reminder_tool,email_summarizer_tool,get_camera_access_tool,stop_camera_access_tool,get_screen_access_tool,stop_screen_share_tool
                ]
            )
        ],
           input_audio_transcription=types.AudioTranscriptionConfig(),
           output_audio_transcription=types.AudioTranscriptionConfig()
   
       )
   return config