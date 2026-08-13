@echo off
REM Run Jarvis GUI (Windows)
setlocal
if not exist .env (
  echo Please copy .env.example to .env and set OLLAMA_URL and API_TOKEN
)
python jarvis_gui.py
