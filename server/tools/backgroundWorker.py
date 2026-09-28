import asyncio
from datetime import datetime,timezone
from uuid import UUID
from conversation.conversation import db
from notification.webPush import send_notification

reminder_queue=asyncio.PriorityQueue()
reminder_wakeup=asyncio.Event()

async def send_reminder(reminder_userId,reminder_title,reminder_message):
        print(f"sending to {reminder_userId}  ={reminder_title}:{reminder_message}")
        devices=await db.devicetoken.find_many(
          where={"userId":reminder_userId}
        )
        if not devices:
            print("❌ No FCM device token found for",reminder_userId)
            success= False
        for device in devices:
           try:
               print(f" Sending notification to device: {device.id}")
               send_notification(
                    device.token,
                    reminder_title,
                    reminder_message
               )
               success =True
           except Exception as e:
                print(f"❌ Notification failed for device {device.id}: {e}")
        return success

async def add_reminder_to_queue(reminder):
     await reminder_queue.put((
          reminder.remindAt,
          str(reminder.id),
          reminder.userId,
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
               reminder.userId,
               reminder.title,
               reminder.message
               )
            )
        
async def reminder_worker():
    while True:
       try:
           remind_at,reminder_id,reminder_userId,reminder_title,reminder_message=(await reminder_queue.get())
           print(f"{reminder_title}  :  {reminder_message} :  at {remind_at}  :  having Id= {reminder_id}")
    
           if remind_at.tzinfo is None:
               remind_at = remind_at.replace(tzinfo=timezone.utc)
           else:
               remind_at = remind_at.astimezone(timezone.utc) 
           now = datetime.now(timezone.utc)

           wait_time=(remind_at - now).total_seconds()
           print(f"Timer : {wait_time}")
           if wait_time>0:
               try:
                    await asyncio.wait_for(reminder_wakeup.wait(),timeout=wait_time)
                    reminder_wakeup.clear()
                    await reminder_queue.put((remind_at,reminder_id,reminder_userId,reminder_title,reminder_message))
                    reminder_queue.task_done()
                    continue
               except asyncio.TimeoutError:
                    pass
           sent=await send_reminder(reminder_userId,reminder_title,reminder_message)

           if sent:
                await db.reminder.update(
                    where={"id":reminder_id},
                    data={"completed":True}
                )
                print("queue",reminder_queue)
           else:
                print(f"❌ Reminder notification failed: {reminder_id}")

           reminder_queue.task_done()

       except Exception as e:
            print(f"Error in reminder_worker: {e}")






