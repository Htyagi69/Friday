import asyncio
from datetime import datetime,timezone
from uuid import UUID
from conversation.conversation import db
from notification.webPush import send_notification

reminder_queue=asyncio.PriorityQueue()
reminder_wakeup=asyncio.Event()

async def send_reminder(reminder_title,reminder_message):
        print(f"sending  ={reminder_title}:{reminder_message}")
        device=await db.devicetoken.find_first()
        if not device:
            print("❌ No FCM device token found")
            return False
        send_notification(
             device.token,
             reminder_title,
             reminder_message
        )
        return True

async def add_reminder_to_queue(reminder):
     await reminder_queue.put((
          reminder.remindAt,
          str(reminder.id),
          reminder.title,
          reminder.message)
     )
     reminder_wakeup.set()
     print(f"new reminder Queued")
    

async def load_reminders_fromdb():
     reminders=await db.reminder.find_many(
          where={"completed":False}
     )
     for reminder in reminders:
        await reminder_queue.put(
             (
               reminder.remindAt,
               str(reminder.id),
               reminder.title,
               reminder.message
               )
            )
        
async def reminder_worker():
    while True:
       try:
           remind_at,reminder_id,reminder_title,reminder_message=await reminder_queue.get()
           print(f"{reminder_title}  :  {reminder_message} :  at {remind_at}  :  having Id= {reminder_id}")
    
           if remind_at.tzinfo is not None:
                now=datetime.now(timezone.utc)
           else:
                now=datetime.now()
           wait_time=(remind_at - now).total_seconds()
           print(f"Timer : {wait_time}")
           if wait_time>0:
               try:
                    await asyncio.wait_for(reminder_wakeup.wait(),timeout=wait_time)
                    reminder_wakeup.clear()
                    await reminder_queue.put((remind_at,reminder_id,reminder_title,reminder_message))
                    continue
               except asyncio.TimeoutError:
                    pass
           sent=await send_reminder(reminder_title,reminder_message)

           if sent:
                await db.reminder.update(
                    where={"id":reminder_id},
                    data={"completed":True}
                )
                print("queue",reminder_queue)

       except Exception as e:
            print(f"Error in reminder_worker: {e}")






# import asyncio
# from datetime import datetime,timezone
# from uuid import UUID
# from conversation.conversation import db
# from notification.webPush import send_notification

# reminder_queue=asyncio.PriorityQueue()
# reminder_wakeup=asyncio.Event()

# async def send_reminder(reminder_title,reminder_message):
#         print(f"sending  ={reminder_title}:{reminder_message}")
#         device=await db.devicetoken.find_first()
#         if not device:
#             print("❌ No FCM device token found")
#             return False
#         send_notification(
#              device.token,
#              reminder_title,
#              reminder_message
#         )
#         return True

# async def add_reminder_to_queue(reminder):
#      await reminder_queue.put((
#           reminder.remindAt,
#           str(reminder.id),
#           reminder.title,
#           reminder.message)
#      )
#      reminder_wakeup.set()
#      print(f"new reminder Queued")
    

# async def load_reminders_fromdb():
#      reminders=await db.reminder.find_many(
#           where={"completed":False}
#      )
#      for reminder in reminders:
#         await reminder_queue.put(
#              (
#                reminder.remindAt,
#                str(reminder.id),
#                reminder.title,
#                reminder.message
#                )
#             )
        
# async def reminder_worker():
#     while True:
#         try:
#             if reminder_queue.empty():
#                  reminder_wakeup.clear()
#                  if reminder_queue.empty():
#                      await reminder_wakeup.wait()
#                  continue
#             remind_at,reminder_id,reminder_title,reminder_message=await reminder_queue.get()
#             print(remind_at,reminder_message,reminder_title)
#             now=datetime.now(timezone.utc)
#             if remind_at.tzinfo is None:
#                  remind_at=remind_at.replace(
#                       tzinfo=timezone.utc
#                  )
#             wait_seconds=(remind_at-now).total_seconds()
#             if wait_seconds>0:
#                  reminder_wakeup.clear()
#                  if not reminder_queue.empty():
#                       await reminder_queue.put((remind_at,reminder_id,reminder_title,reminder_message))
#                       continue

#                  try:
#                       await asyncio.wait_for(
#                            reminder_wakeup.wait(),
#                            timeout=wait_seconds
#                       )
#                       await reminder_queue.put((remind_at,reminder_id,reminder_title,reminder_message))
#                       continue
#                  except asyncio.TimeoutError:
#                       pass
#             print(f"🔔 Reminder due: {reminder_title}")
#             sent=await send_reminder(reminder_title,reminder_message)
#             if sent:
#                  await db.reminder.update(
#                       where={"id":UUID(reminder_id)},
#                       data={"completed":True}
#                  )
#                  print(f"✅ Reminder completed: {reminder_title}")
#             else: 
#              await asyncio.sleep(10)
#              await reminder_queue.put((remind_at,reminder_id,reminder_title,reminder_message))
#         except asyncio.CancelledError:
#              raise
        
#         except Exception as e:
#              print("❌ Reminder worker error:", e)

