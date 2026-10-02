import asyncio
from google.genai import types

async def send_camera_frames(manager,session):
    print("Camera sender started")
    try:
        while True:
            frame=await manager.camera_queue.get()
            if frame is None:
                continue
            print("Sending frame to Gemini")
            
            await session.send_realtime_input(
                video=types.Blob(
                 data=frame["data"],
                 mime_type=frame["mime_type"]
            ) 
            )

    except asyncio.CancelledError:
        print("camera sender stopped")
        raise
    except Exception as e:
        print(f"❌ Camera sender error: {type(e).__name__}: {e}")
        raise