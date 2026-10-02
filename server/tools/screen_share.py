from google.genai import types

async def send_screen_frames(manager,session):
    print("Screen sender started")
    try:
        while True:
            frame=await manager.screen_queue.get()
            if frame is None:
                continue
            print("Sending frame to Gemini")
            
            await session.send_realtime_input(
                video=types.Blob(
                 data=frame["data"],
                 mime_type=frame["mime_type"]
            ) 
            )

    except Exception as e:
        print("Screen Sender Stopped")
        raise