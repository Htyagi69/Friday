import asyncio
from prisma import Prisma

db= Prisma()

__all__=["ConversationManager","db"]

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

