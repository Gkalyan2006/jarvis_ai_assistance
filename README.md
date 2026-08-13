# Jarvis AI Assistance - Phase One (MVP)

This repository contains the Phase One scaffold for "Jarvis AI Assistance" — a Windows 11-targeted local assistant MVP.

What's included:
- FastAPI backend to coordinate STT, LLM (Ollama), TTS, automation, and logging
- Whisper (faster-whisper) based STT wrapper (microphone record demo)
- Ollama client wrapper (HTTP/Subprocess fallback)
- pyttsx3 TTS wrapper
- Windows automation helper (open apps, run shell commands, create files/folders)
- SQLite-based memory + activity logging
- Simple HTML dashboard

Prerequisites:
- Python 3.10+
- Ollama installed and Qwen3:8B (or another model) available locally
- On Windows: sounddevice + drivers for microphone

See README.md for setup & run instructions.
