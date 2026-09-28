import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from conversation.conversation import db
from liveStream import router as live_stream_router
from notification.webPush import send_notification
from conversation.conversation import db
from tools.backgroundWorker import (load_reminders_fromdb,reminder_worker)

load_dotenv()

@asynccontextmanager
async def lifespan(app:FastAPI):
    await  db.connect()
    await load_reminders_fromdb()
    reminder_task=asyncio.create_task(reminder_worker())
    try:
       yield
    finally:
       reminder_task.cancel()
       try:
           await reminder_task
       except asyncio.CancelledError:
           pass
       await db.disconnect()

app=FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to your specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
@app.get("/")
def read():
    return "Hello from uv ok" 

@app.post("/test-notify")
async def testNotification():
    device=await db.devicetoken.find_first()
    if not device:
         return {
            "success": False,
            "message": "No FCM token found"
        }
    message_id=send_notification(
        device.token,
        "Friday",
        "Jarvis Back Online,Sir 🎉"
    )
    return { 
        "success": True,
        "Message":message_id
        }

@app.post("/register-device")
async def register_device(data:dict):
    token=data["token"]
    # print("FCM Token",token)
    if not token:
        return {
            "success": False,
            "message": "FCM token missing"
        }

    await db.devicetoken.upsert(
             where={
                "token": token
            },
            data={
                "create":{
                "userId":"Tony Stark",
                "token":token
                },
                "update":{}
            })

    return {"success":True}

app.include_router(live_stream_router)