import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from conversation.conversation import ConversationManager
from tools.get_session import get_Sessions
from tools import google_client
from tools.geminiResponse import ( create_config, sendget_gemini_response)
from tools.receive_audio import receive_audio


router = APIRouter()
logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3.1-flash-live-preview"

INITIAL_RECONNECT_DELAY = 1
MAX_RECONNECT_DELAY = 10


def is_quota_or_auth_error(error: Exception) -> bool:
    """Return True only for errors that may justify rotating API keys."""
    message = str(error).lower()

    indicators = (
        "resource_exhausted",
        "quota",
        "429",
        "api key",
        "api_key_invalid",
        "unauthenticated",
        "authentication",
        "permission_denied",
        "403",
    )

    return any(indicator in message for indicator in indicators)


async def cancel_tasks(*tasks: asyncio.Task) -> None:
    """Cancel and await unfinished tasks to prevent orphaned receivers."""
    for task in tasks:
        if not task.done():
            task.cancel()

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


@router.websocket("/ws/live")
async def live_stream(websocket: WebSocket):
    await websocket.accept()

    manager = ConversationManager()

    session_context = ""
    temp_messages = []
    reconnect_delay = INITIAL_RECONNECT_DELAY
    browser_disconnected = False

    print("🔥 BROWSER CONNECTED")

    try:
        # Load conversation titles once for the initial connection.
        session_history = await get_Sessions()

        while not browser_disconnected:
            response_task = None
            audio_task = None
            switch_task = None
            should_switch_session = False

            try:
                # Read the module's current client on each connection.
                # This avoids retaining a stale client if google_client
                # replaces its module-level client during key rotation.
                gemini_client = google_client.client

                config = create_config(
                    manager,
                    session_history,
                    session_context,
                )

                print("🔌 Connecting to Gemini Live...")

                async with gemini_client.aio.live.connect(
                    model=GEMINI_MODEL,
                    config=config,
                ) as session:

                    manager.gemini_session = session
                    print("✅ Gemini Live connected")

                    response_task = asyncio.create_task(
                        sendget_gemini_response(
                            manager,
                            session,
                            websocket,
                            temp_messages,
                        ),
                        name="friday-gemini-response",
                    )

                    audio_task = asyncio.create_task(
                        receive_audio(
                            session,
                            websocket,
                            manager,
                        ),
                        name="friday-browser-input",
                    )

                    switch_task = asyncio.create_task(
                        manager.watch_session_switch(),
                        name="friday-session-switch",
                    )

                    tasks = [
                        response_task,
                        audio_task,
                        switch_task,
                    ]

                    try:
                        done, pending = await asyncio.wait(
                            tasks,
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        # A conversation switch should replace the Gemini
                        # session while keeping the browser WebSocket alive.
                        if switch_task in done:
                            exception = (
                                switch_task.exception()
                                if not switch_task.cancelled()
                                else None
                            )

                            if exception:
                                raise exception

                            session_context = (
                                manager.pending_context or ""
                            )

                            should_switch_session = True
                            print("🔄 Switching Friday conversation")

                        else:
                            # A response or input task ended. Surface errors
                            # so the outer loop can handle/reconnect.
                            for task in done:
                                if task.cancelled():
                                    continue

                                exception = task.exception()

                                if exception is not None:
                                    raise exception

                            # Some response loops return normally after a
                            # Gemini disconnect. Recreate the Live session.
                            print(
                                "⚠️ A Friday session task ended. "
                                "Reconnecting to Gemini..."
                            )

                    finally:
                        # Never leave multiple tasks reading from or writing
                        # to an old session after its context closes.
                        await cancel_tasks(*tasks)

                    manager.gemini_session = None

                # Reset backoff after a successful connection or switch.
                if should_switch_session:
                    reconnect_delay = INITIAL_RECONNECT_DELAY
                    continue

                # A task ended without an exception, so reconnect with a
                # short delay rather than spinning in a tight loop.
                reconnect_delay = INITIAL_RECONNECT_DELAY

            except WebSocketDisconnect:
                print("👋 Browser disconnected")
                browser_disconnected = True
                break

            except asyncio.CancelledError:
                print("🛑 Friday WebSocket task cancelled")
                raise

            except Exception as error:
                manager.gemini_session = None

                print(
                    f"❌ Gemini session error: "
                    f"{type(error).__name__}: {error}"
                )

                if is_quota_or_auth_error(error):
                    print("🔑 Possible quota/auth error; rotating key")

                    try:
                        # This function must update google_client.client
                        # if the key/client is actually changed.
                        google_client.rotate_keys()
                    except Exception as rotation_error:
                        print(
                            "❌ API key rotation failed:",
                            rotation_error,
                        )

                else:
                    print(
                        "⚠️ Session disconnected; "
                        "this does not automatically mean quota was exceeded."
                    )

                print(
                    f"⏳ Retrying in {reconnect_delay} second(s)..."
                )

                await asyncio.sleep(reconnect_delay)

                reconnect_delay = min(
                    reconnect_delay * 2,
                    MAX_RECONNECT_DELAY,
                )

    except WebSocketDisconnect:
        print("👋 Browser disconnected")

    except asyncio.CancelledError:
        raise

    except Exception as error:
        print(
            f"❌ Friday connection error: "
            f"{type(error).__name__}: {error}"
        )

    finally:
        manager.gemini_session = None

        # Clean up any camera/screen tasks managed by your manager,
        # if those methods exist in your implementation.
        try:
            await cancel_tasks(
                *[
                    task
                    for task in (
                        getattr(manager, "camera_task", None),
                        getattr(manager, "camera_sender_task", None),
                        getattr(manager, "screen_task", None),
                    )
                    if isinstance(task, asyncio.Task)
                ]
            )
        except Exception as cleanup_error:
            print("⚠️ Cleanup warning:", cleanup_error)

        print("🔒 Friday WebSocket connection closed")













# import asyncio
# from conversation.conversation import ConversationManager
# from fastapi import FastAPI,File,UploadFile,APIRouter,WebSocket,WebSocketDisconnect
# from tools.get_session import get_Sessions
# from tools.google_client import client, rotate_keys
# from tools.geminiResponse import sendget_gemini_response,create_config
# from tools.receive_audio import receive_audio

# router=APIRouter()

# @router.websocket("/ws/live")
# async def live_stream(websocket: WebSocket):
#     await websocket.accept()

#     manager=ConversationManager()
#     print("🔥 BROWSER CONNECTED")
#     try:
#         session_history=await get_Sessions()
#         tempMessages=[]
#         session_context = ""
#         while True:
#            config=create_config(manager,session_history,session_context)
#            try:
#                async with client.aio.live.connect(
#                   model="gemini-3.1-flash-live-preview",
#                   config=config
#                   ) as session:
#                     manager.gemini_session=session
#                     response=asyncio.create_task(
#                        sendget_gemini_response(manager,session,websocket,tempMessages)
#                     )
#                     audio_task = asyncio.create_task(receive_audio(session,websocket,manager))
#                     switch_task = asyncio.create_task(manager.watch_session_switch())
#                     done, pending = await asyncio.wait(
#                         [
#                             response,
#                             audio_task,
#                             switch_task
#                         ],
#                         return_when=asyncio.FIRST_COMPLETED
#                     )
#                     if switch_task in done:
#                         print(" Session switch detected")
#                         session_context = (manager.pending_context)
#                         # print(" New context:",session_context)
#                         # Cancel old Gemini tasks
#                         response.cancel()
#                         audio_task.cancel()
    
#                         await asyncio.gather(
#                             response,
#                             audio_task,
#                             return_exceptions=True
#                         )
#                         continue
    
#                     for task in pending:
#                         task.cancel()
    
#                     await asyncio.gather(
#                         *pending,
#                         return_exceptions=True
#                     )
    
#                     for task in done:
#                         if task is not switch_task:
#                             exception = task.exception()
#                             if exception:
#                                 raise exception
#                     break
#            except Exception as e:
#                error = str(e)
           
#                print(f"❌ Gemini session error: {error}")
#                if ( "RESOURCE_EXHAUSTED" in error or "429" in error or "quota" in error.lower() or "API key" in error or "authentication" in error.lower() or "permission" in error.lower()):
#                    rotate_keys()
#                    print("🔄 Gemini quota/auth error → switching key...")
#                    continue
           
#                # Normal disconnect / internal session failure
#                print("⚠️ Gemini session disconnected.")
#                break
#     except WebSocketDisconnect:
#          print("Browser disconnected")

#     except Exception as e:
#          print(f"Audio sending error: {e}")

#     finally:
#         print('Connection Closed')



#                 #    except Exception as e:
#                 # print(f"❌ Gemini session error: {e}")
#                 # rotate_keys()
#                 # print(" Retrying Gemini Live with next key...")

#                 # continue
