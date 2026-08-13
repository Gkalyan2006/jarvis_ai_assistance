"""
Ollama HTTP client wrapper (phase-one-mvp)
Replaces reliance on the Ollama CLI by calling the HTTP API at /api/chat.
Reads OLLAMA_URL and OLLAMA_MODEL from environment variables.
"""
import os
import requests


class OllamaClient:
    def __init__(self, base_url: str | None = None, default_model: str | None = None):
        # Read from env if not provided
        self.base_url = (base_url or os.getenv('OLLAMA_URL', 'http://localhost:11434')).rstrip('/')
        self.default_model = default_model or os.getenv('OLLAMA_MODEL', 'qwen3:8b')

    def chat(self, prompt: str, model: str | None = None) -> str:
        """Send a single-message chat request to Ollama HTTP API (/api/chat).

        Returns the assistant reply text on success, or a concise error string on failure.
        Does not print or log API tokens.
        """
        model = model or self.default_model
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        headers = {}
        # If an API token is provided in env, send it as a bearer token but do NOT log it.
        token = os.getenv('API_TOKEN') or os.getenv('OLLAMA_API_TOKEN') or os.getenv('HF_TOKEN')
        if token:
            headers['Authorization'] = f"Bearer {token}"

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # Preferred new Ollama response shape: { "message": { "content": "..." } }
            if isinstance(data, dict):
                msg = data.get('message')
                if isinstance(msg, dict) and 'content' in msg:
                    content = msg['content']
                    if isinstance(content, str):
                        return content
                    return str(content)

                # Fallback: older shape with choices -> message -> content
                if 'choices' in data and isinstance(data['choices'], list) and len(data['choices']) > 0:
                    choice = data['choices'][0]
                    if isinstance(choice, dict):
                        # choice.message.content
                        ch_msg = choice.get('message')
                        if isinstance(ch_msg, dict) and 'content' in ch_msg:
                            return ch_msg['content']
                        # choice.content
                        if 'content' in choice:
                            return choice['content']

                # Another fallback: output key
                if 'output' in data:
                    return data['output']

            # Last resort: return the raw JSON string
            return str(data)

        except requests.exceptions.RequestException as e:
            # Network/HTTP errors — return a concise message (no tokens)
            return f"Ollama HTTP error: {e}"
        except Exception as e:
            return f"Ollama error: {e}"
