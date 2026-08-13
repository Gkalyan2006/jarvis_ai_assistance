# Jarvis Desktop (Phase One) - Desktop-only (minimal install)

This branch provides a desktop-only, hands-free Jarvis assistant for Windows. It defaults to VOSK for wake-word detection and aims to be lightweight to speed up installs.

Minimal install (fast)
1. Create & activate venv (PowerShell):
   python -m venv .venv
   . .\.venv\Scripts\Activate.ps1

2. Install minimal dependencies (fast):
   pip install -r requirements-minimal.txt

3. Download & set up a VOSK model (small English model recommended):
   - https://alphacephei.com/vosk/models (e.g. vosk-model-small-en-us-0.15)
   - Unzip to a local folder, e.g. C:\models\vosk-model-small-en-us-0.15

4. Configure .env (copy .env.example -> .env) and set:
   WAKE_BACKEND=vosk
   VOSK_MODEL_PATH=C:\models\vosk-model-small-en-us-0.15
   VOSK_SAMPLE_RATE=16000
   OLLAMA_URL=http://localhost:11434
   API_TOKEN=<your_token>

5. Run the GUI:
   python jarvis_gui.py

Optional heavier features
- If you want Whisper-based transcription, GPU acceleration, or async DB enhancements, install optional packages:
  pip install -r requirements-optional.txt

Notes
- The minimal install avoids heavy ML wheels and large model downloads. VOSK is used for wake-word and can also be used for command transcription if desired.
- If you want me to switch the full transcription pipeline from faster-whisper to VOSK (so you never need faster-whisper), say "switch stt to vosk" and I'll update the code and push.
