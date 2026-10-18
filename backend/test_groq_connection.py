import os
import json
import httpx
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv('GROQ_API_KEY')
MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-specdec')

if not API_KEY:
    print('GROQ_API_KEY not set in environment.')
    exit(1)

payload = {
    'model': MODEL,
    'messages': [{'role': 'user', 'content': 'Hello'}],
    'temperature': 0.0,
}

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json',
}

url = 'https://api.groq.com/openai/v1/chat/completions'

try:
    response = httpx.post(url, json=payload, headers=headers, timeout=10.0)
    print('Status code:', response.status_code)
    print('Response body:')
    print(response.text)
except Exception as e:
    print('Error during request:', e)
