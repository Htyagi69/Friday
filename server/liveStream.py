import asyncio
from conversation.conversation import ConversationManager
from fastapi import FastAPI,File,UploadFile,APIRouter,WebSocket,WebSocketDisconnect
from tools.get_session import get_Sessions
from tools.google_client import client
from tools.geminiResponse import sendget_gemini_response,create_config
from tools.receive_audio import receive_audio

router=APIRouter()

@router.websocket("/ws/live")
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
                audio_task = asyncio.create_task(receive_audio(session,websocket,manager))
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
