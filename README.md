# Updated README: Jarvis Desktop (no website)

This branch implements a Siri-like local desktop assistant for Windows 11.
It provides an always-on wake-word listener and a small desktop GUI (no website).

Run the GUI assistant:
1. Clone & checkout phase-one-mvp branch
2. Create virtualenv and install dependencies
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-porcupine.txt  # if using Porcupine
   pip install pystray pillow

3. Configure .env (copy .env.example and set values)
   - OLLAMA_URL (e.g., http://localhost:11434)
   - API_TOKEN
   - PORCUPINE_KEYWORD_PATH and PORCUPINE_LIBRARY_PATH (if using wake word)

4. Run:
   python jarvis_gui.py
   or double-click run_gui.bat

Notes:
- The GUI shows status, transcripts, and assistant replies. A system tray icon is shown if pystray is available.
- The assistant uses Porcupine for wake-word detection if you provide a .ppn keyword file. Otherwise, use the fallback hotkey mode (press Enter in the console window).
- No web dashboard is required to run the assistant. The FastAPI files remain in the repo for optional mobile control but are not necessary for the desktop GUI.
