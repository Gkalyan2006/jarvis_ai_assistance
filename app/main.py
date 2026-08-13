from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from .llm.ollama_client import OllamaClient
from .stt.whisper_stt import transcribe_from_microphone
from .tts.tts import speak_text
from .automation.windows_automation import run_command, open_app
from .db.init_db import init_db, log_activity

app = FastAPI(title="Jarvis AI Assistance - Phase One")

# mount static
app.mount("/static", StaticFiles(directory="./app/static"), name="static")

ollama = OllamaClient(os.getenv("OLLAMA_URL", "http://localhost:11434"))

@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/voice/transcribe")
async def api_transcribe():
    # records ~5s of mic audio and transcribes
    text = transcribe_from_microphone(duration=5)
    await log_activity(action="transcribe", details=text)
    return {"transcript": text}

@app.post("/api/ask")
async def api_ask(request: Request):
    payload = await request.json()
    prompt = payload.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt required")
    # send to Ollama
    resp = ollama.chat(prompt)
    # speak
    speak_text(resp)
    await log_activity(action="ask", details=prompt)
    return {"response": resp}

@app.post("/api/automation/run")
async def api_run(request: Request):
    # token protection for LAN control
    token = request.headers.get("x-api-token")
    if token != os.getenv("API_TOKEN", "changeme-token-for-local-lan"):
        raise HTTPException(status_code=401, detail="invalid token")
    payload = await request.json()
    cmd = payload.get("cmd")
    apppath = payload.get("app")
    if cmd:
        out = run_command(cmd)
        await log_activity(action="automation_cmd", details=cmd)
        return {"output": out}
    if apppath:
        open_app(apppath)
        await log_activity(action="automation_open", details=apppath)
        return {"status": "opened", "app": apppath}
    raise HTTPException(status_code=400, detail="cmd or app required")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    html = open("app/static/index.html","r",encoding="utf-8").read()
    return HTMLResponse(content=html)
