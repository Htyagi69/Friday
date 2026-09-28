
import asyncio
from zoneinfo import ZoneInfo
from prisma import Prisma
from datetime import datetime, timedelta, timezone


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

