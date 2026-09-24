import os
from google import genai

__all__=["client"]

client=genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
