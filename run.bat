@echo off
REM Run the FastAPI app (Windows)
setlocal
if not exist .env (
  echo Please copy .env.example to .env and set OLLAMA_URL and API_TOKEN
)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
