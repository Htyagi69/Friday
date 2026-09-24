from conversation.conversation import db

__all__=["get_sessions"]

async def get_Sessions():
   try:
      sessions=await db.session.find_many()
      return [
          {
              "title":session.title,
              "id":str(session.id),
              "createdAt":{session.createdAt},
          } for session in sessions
      ]
    #   print(sessionHistory)

   except Exception as e:
       print("error",e)
       return
