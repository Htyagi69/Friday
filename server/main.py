from fastapi import FastAPI,File,UploadFile
from fastapi.middleware.cors import CORSMiddleware
from LiveAssistant import AudioLoop

app=FastAPI()

audio=AudioLoop()

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


@app.post("/response")
async def audiores(audio_file:UploadFile=File(...)):
    print(f"Recieved file:{audio_file}")
    res=await audio.receive_audio(audio_file)
    return {"message":res} 