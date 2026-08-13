# Jarvis Desktop (Phase One) - Desktop-only

This branch implements a Siri-like local desktop assistant for Windows 11. It is
fully desktop-focused and does not include a web dashboard or web API.

What's included
- jarvis_gui.py — Desktop GUI with system tray support (VOSK wake-word by default)
- jarvis_service.py — Console service (also uses selected wake backend)
- app/wake/vosk_wake.py — VOSK wake-word backend
- app/stt/whisper_stt.py — faster-whisper microphone recording & transcription
- app/llm/ollama_client.py — Ollama client wrapper (HTTP + CLI fallback)
- app/tts/tts.py — pyttsx3 TTS wrapper
- app/automation/windows_automation.py — open apps / run commands helpers
- app/db/init_db.py — SQLite activity logging

Removed
- FastAPI web dashboard and API are removed from this branch to provide a
  purely desktop/hands-free assistant. If you want the web UI back, I can
  reintroduce it in a separate branch or on request.

Quick start (Windows)
1. Clone & checkout phase-one-mvp
   git clone https://github.com/Gkalyan2006/jarvis_ai_assistance.git
   cd jarvis_ai_assistance
   git checkout phase-one-mvp

2. Create & activate venv (PowerShell):
   python -m venv .venv
   . .\.venv\Scripts\Activate.ps1

3. Install dependencies:
   pip install -r requirements.txt
   pip install vosk sounddevice

4. Download & set up VOSK model (see app/wake/README_VOSK.md)
   - set VOSK_MODEL_PATH in .env
   - set WAKE_BACKEND=vosk

5. Configure .env and run the GUI:
   - copy .env.example to .env and set OLLAMA_URL, API_TOKEN, VOSK_MODEL_PATH
   - python jarvis_gui.py

If you want the web API restored or a separate minimal HTTP control endpoint,
let me know and I will add it as an optional module in another branch.
