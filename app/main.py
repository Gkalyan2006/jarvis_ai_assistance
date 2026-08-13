# Web API removed

The FastAPI-based web API and dashboard have been intentionally removed from this branch.
This repository now focuses on the desktop-only Jarvis assistant (jarvis_gui.py and jarvis_service.py),
which uses a local wake-word backend (VOSK by default), local STT/TTS, and local LLM (Ollama).

If you previously relied on the web endpoints, please migrate logic to a local client that
calls the assistant directly or re-add a small API layer in a separate branch.
