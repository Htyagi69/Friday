from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from conversation.conversation import db
from liveStream import router as live_stream_router
from notification.webPush import send_notification

load_dotenv()

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
 
@app.get("/")
def read():
    return "Hello from uv ok" 

@app.post("/test-notify")
def testNotification(token:str):
    message_id=send_notification(
        token,
        "Friday",
        "Jarvis Online,Sir 🎉"
    )
    return {"Message":message_id}

app.include_router(live_stream_router)