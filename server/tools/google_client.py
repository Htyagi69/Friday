import os
from google import genai

Gemini_keys = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY1")
]

Gemini_keys = [key for key in Gemini_keys if key]
current_key = 0

def rotate_keys():
    global current_key, client
    current_key = (current_key + 1) % len(Gemini_keys)
    client = genai.Client(api_key=Gemini_keys[current_key])
    print(f"Gemini key rotated to: {current_key + 1}")
    return client

client = genai.Client(api_key=Gemini_keys[current_key])