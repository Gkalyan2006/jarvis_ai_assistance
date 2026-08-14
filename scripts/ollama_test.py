"""
Small standalone Ollama connectivity test.
Usage: python scripts/ollama_test.py
Reads OLLAMA_URL and OLLAMA_MODEL from environment (falls back to defaults).
"""
import os
import requests
import json

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434').rstrip('/')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen3:8b')
API_TOKEN = os.getenv('API_TOKEN')

url = f"{OLLAMA_URL}/api/chat"
payload = {
    "model": OLLAMA_MODEL,
    "messages": [{"role": "user", "content": "Say hello in one sentence."}],
    "stream": False,
}

headers = {'Content-Type': 'application/json'}
if API_TOKEN:
    headers['Authorization'] = f"Bearer {API_TOKEN}"

print(f"Testing Ollama connectivity to: {url} (model={OLLAMA_MODEL})")
try:
    r = requests.post(url, json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    data = r.json()
    print("HTTP 200 OK — response received")
    # Try to extract message content
    if isinstance(data, dict):
        msg = data.get('message')
        if isinstance(msg, dict) and 'content' in msg:
            print("Assistant:", msg['content'])
        elif 'choices' in data and len(data['choices'])>0:
            ch = data['choices'][0]
            chmsg = ch.get('message') if isinstance(ch, dict) else None
            if isinstance(chmsg, dict) and 'content' in chmsg:
                print("Assistant:", chmsg['content'])
            elif 'content' in ch:
                print("Assistant:", ch['content'])
            else:
                print("Raw response:", json.dumps(data))
        else:
            print("Raw response:", json.dumps(data))
    else:
        print("Non-dict response:", data)
except requests.exceptions.RequestException as e:
    print("Request failed:", e)
except Exception as e:
    print("Error parsing response:", e)
