import requests
import subprocess
import json

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url.rstrip('/')

    def chat(self, prompt: str, model: str = "qwen3:8b") -> str:
        # Try HTTP API
        try:
            url = f"{self.base_url}/chat"
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
            r = requests.post(url, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            # Ollama HTTP returns a 'choices' structure similar to others
            if isinstance(data, dict):
                # best-effort extraction
                if 'choices' in data and len(data['choices'])>0:
                    return data['choices'][0].get('message', {}).get('content', '')
                if 'output' in data:
                    return data['output']
            return str(data)
        except Exception:
            # Fallback to CLI
            try:
                p = subprocess.run(["ollama", "chat", model, "-p", prompt], capture_output=True, text=True, timeout=60)
                return p.stdout.strip() or p.stderr.strip()
            except Exception as e:
                return f"Ollama error: {e}"
