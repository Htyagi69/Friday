from google import genai
from conversation.conversation import ConversationManager
from tools.google_client import client

__all__=["get_session_title"]

async  def get_session_title(manager:ConversationManager,messages:list):
       prompt = f"""
       Generate a short title for this conversation.
       
       User,Assistant:
       {messages}
       
       Rules:
       - Maximum 5 words
       - No quotes
       - No punctuation
       - Describe the main topic
       - Do not use "conversation", "chat", or "session"
       """
       
       response = await client.aio.models.generate_content(
               model="gemini-2.5-flash",
               contents=prompt
           )
       title= response.text.strip()
       sessionId=await manager.create_session(title)
       return sessionId