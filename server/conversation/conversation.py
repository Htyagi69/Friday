import asyncio
import io
from zoneinfo import ZoneInfo
import PIL.Image
import cv2
import mss
from prisma import Prisma
from datetime import datetime, timedelta, timezone
from tools.screen_share import send_screen_frames
from tools.camera_access import send_camera_frames


db= Prisma()

__all__=["ConversationManager","db"]
IST = ZoneInfo("Asia/Kolkata")

class ConversationManager:
       def __init__(self):
                 self.active_session_id=None
                 self.gemini_session=None
                 self.switch_event=asyncio.Event()
                 self.pending_context = ""
                 self.title_generated=False
                 self.camera_queue=asyncio.Queue(maxsize=1)
                 self.screen_queue=asyncio.Queue(maxsize=1)
                 self.camera_task=None
                 self.screen_task=None
                 self.camera_sender_task=None
                 self.screen_sender_task=None
       
       async def create_session(self,title):
           session=await db.session.create(
               data={"title":title}
           )
           self.active_session_id=str(session.id)
           return self.active_session_id
       
       async def set_reminder(self,title,message,schedule_type,delay_seconds=None,local_datetime=None):
        now = datetime.now(timezone.utc)
        if schedule_type == "relative":
              if delay_seconds is None or delay_seconds <= 0:
                 return {
                "success": False,
                "message": "A valid delay is required."
                }

              remind_at = now + timedelta(seconds=delay_seconds)
               
        elif schedule_type == "absolute":

           if not local_datetime:
               return {
                "success": False,
                "message": "A reminder date and time is required."
               }

           local_time = datetime.fromisoformat(local_datetime)
           if local_time.tzinfo is not None:
            return {
                "success": False,
                "message": "Provide local IST time without timezone."
            }

           remind_at = local_time.replace(tzinfo=IST).astimezone(timezone.utc)
   
           if remind_at <= now:
               return {
                   "success": False,
                   "message": "The reminder time must be in the future."
               }

        else:
            return {
            "success": False,
            "message": "Invalid schedule type."
            }

        reminder = await db.reminder.create(
           data={
            "userId": "Tony Stark",
            "title": title,
            "message": message,
            "remindAt": remind_at
            }
          )

        from tools.backgroundWorker import add_reminder_to_queue

        await add_reminder_to_queue(reminder)

        return {
        "success": True,
        "message": f"Reminder scheduled: {title}",
        "remindAt": remind_at.isoformat()
         }
            
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


       def _get_screen(self):
          with mss.mss() as sct:
            monitor=sct.monitors[0]
    
            screenshot=sct.grab(monitor)
            img=PIL.Image.frombytes(
                "RGB",
                screenshot.size,
                screenshot.rgb
            )
    
            img.thumbnail((1920,1080))
            img_io=io.BytesIO()
            img.save(
                img_io,
                format="JPEG",
                quality=70
            )
            img_bytes=img_io.getvalue()
    
            return{
                "mime_type":"image/jpeg",
                "data":img_bytes
            }
       


       def _get_frame(self,cap):
           ret,frame=cap.read()
       
           if not ret:
               return None
       
           frame_rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
       
           img=PIL.Image.fromarray(frame_rgb)
       
           img.thumbnail((1024,1024))
           img_io=io.BytesIO()
           img.save(
               img_io,
               format="JPEG",
               quality=80
           )
           image_bytes=img_io.getvalue()
       
           return{
               "mime_type":"image/jpeg",
               "data":image_bytes
           }


       async  def _screen_loop(self):
            print("Starting Screen Share") 

            try:
                 while True:
                      frame=await asyncio.to_thread(self._get_screen)

                      if self.screen_queue.full():
                           try:
                                self.screen_queue.get_nowait()
                           except asyncio.QueueEmpty:
                                pass

                      await self.screen_queue.put(frame)
                      await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                print("Screen Share Stopped")
            except Exception as e:
                  print(f"❌ Screen error: {type(e).__name__}: {e}")

       async  def _camera_loop(self):
            print("Starting Camera")
            cap=await asyncio.to_thread(cv2.VideoCapture,0)

            if not cap.isOpened():
                 print("Unable to open cameera")
                 return    

            try:
                 while True:
                      frame=await asyncio.to_thread(self._get_frame,cap)
                      if frame is  None:
                         await asyncio.sleep(0.1)
                         continue

                      if self.camera_queue.full():
                           try:
                                self.camera_queue.get_nowait()
                           except asyncio.QueueEmpty:
                                pass

                      await self.camera_queue.put(frame)
                      await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                print("Camera task stopped")
            except Exception as e:
                print(f" Camera loop error: {type(e).__name__}: {e}")
            finally:
                 cap.release()
                 print("camera closed")

       async def start_camera(self,session):
          if self.camera_task and not self.camera_task.done():
               return{
                    "success":True,
                    "message":"Camera already active"
               }
          self.camera_task=asyncio.create_task(self._camera_loop())
          self.camera_sender_task=asyncio.create_task(
               send_camera_frames(self,session)
          )
          return{
               "success":True,
               "message":"Camera started, you can see the user's surroundings"
          }
       
       async def stop_camera(self):
          if self.camera_task and not self.camera_task.done():
               self.camera_task.cancel()
               await asyncio.gather(
                    self.camera_task,
                    return_exceptions=True
               )
          self.camera_task=None
          if self.camera_sender_task and not self.camera_sender_task.done():
               self.camera_sender_task.cancel()
               await asyncio.gather(
                    self.camera_sender_task,
                    return_exceptions=True
               )
          self.camera_sender_task=None
          while not self.camera_queue.empty():
              try:
                  self.camera_queue.get_nowait()
              except asyncio.QueueEmpty:
                  break
      
          print(" Camera stopped")
          return{
                "success":True,
                "message":"Camera stopped"
               }
       
       async def get_screen(self,session):
            if self.screen_task and not self.screen_task.done():
                  return{
                        "success":True,
                        "message":"Screen already shared"
                     }
            self.screen_task=asyncio.create_task(self._screen_loop())
            self.screen_sender_task=asyncio.create_task(
                  send_screen_frames(self,session)
            )
            print("Screen Started Shairing")

            return{
               "success":True,
               "message":"screen Sharing started, you can see the device screen"
          }
       
       async def stop_screen_share(self):
          if self.screen_task and not self.screen_task.done():
               self.screen_task.cancel()
               await asyncio.gather(
                    self.screen_task,
                    return_exceptions=True
               )
          self.screen_task=None

          while not self.screen_queue.empty():
              try:
                  self.screen_queue.get_nowait()
              except asyncio.QueueEmpty:
                  break
      
          print(" screen Share stopped")
          return{
                "success":True,
                "message":"Screen Share stopped"
               }