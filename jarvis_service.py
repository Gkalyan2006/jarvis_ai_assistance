"""
Jarvis Service - Always-on wake-word listener and assistant loop
Supports WAKE_BACKEND=vosk|porcupine|whisper (vosk default)
"""
import os
import time
import sys
import threading
from dotenv import load_dotenv

# Load environment variables from .env (if present) early
load_dotenv()

from app.stt.whisper_stt import transcribe_from_microphone
from app.llm.ollama_client import OllamaClient
from app.tts.tts import speak_text
from app.db.init_db import init_db, log_activity
from app.automation.windows_automation import open_app, run_command

WAKE_BACKEND = os.getenv('WAKE_BACKEND', 'vosk').lower()

# Porcupine optional
try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except Exception:
    PORCUPINE_AVAILABLE = False

use_porcupine = False
use_vosk = False

if WAKE_BACKEND == 'porcupine' and PORCUPINE_AVAILABLE:
    keyword_path = os.getenv('PORCUPINE_KEYWORD_PATH')
    library_path = os.getenv('PORCUPINE_LIBRARY_PATH')
    sensitivity = float(os.getenv('PORCUPINE_SENSITIVITY', '0.5'))
    if keyword_path:
        try:
            wake_porcupine = pvporcupine.create(keyword_paths=[keyword_path], sensitivities=[sensitivity], library_path=library_path if library_path else None)
            sample_rate = wake_porcupine.sample_rate
            frame_length = wake_porcupine.frame_length
            use_porcupine = True
            print('Porcupine initialized')
        except Exception as e:
            print('Failed to init Porcupine:', e)
            use_porcupine = False

elif WAKE_BACKEND == 'vosk':
    try:
        from app.wake.vosk_wake import VoskWakeListener
        model_path = os.getenv('VOSK_MODEL_PATH')
        if not model_path:
            raise RuntimeError('VOSK_MODEL_PATH not set')
        wake_vosk = VoskWakeListener(model_path=model_path, sample_rate=int(os.getenv('VOSK_SAMPLE_RATE', '16000')))
        use_vosk = True
        print('VOSK initialized')
    except Exception as e:
        print('VOSK init failed:', e)
        raise

else:
    print('Unsupported WAKE_BACKEND or backend not available:', WAKE_BACKEND)
    raise SystemExit(1)


def handle_interaction(ollama: OllamaClient):
    try:
        # VAD-based recording for user utterance
        print("Recording user utterance (VAD)...")
        transcript = transcribe_from_microphone(duration=int(os.getenv('MAX_RECORD_SECONDS', '6')))
        if not transcript or not transcript.strip():
            print("No speech detected. Listening again...")
            return
        print(f"User said: {transcript}")
        # call LLM
        resp = ollama.chat(transcript)
        print(f"Assistant: {resp}")
        speak_text(resp)
        # log
        try:
            import asyncio
            asyncio.run(log_activity(action="interaction", details=f"user: {transcript} | assistant: {resp}"))
        except Exception:
            log_activity(action="interaction", details=f"user: {transcript} | assistant: {resp}")
        # simple post-processing: if assistant suggests to open app in a special format: OPEN: path
        if resp.strip().upper().startswith('OPEN:'):
            path = resp.split(':', 1)[1].strip()
            if path:
                open_app(path)
                speak_text(f"Opening {path}")
        # or RUN: command
        if resp.strip().upper().startswith('RUN:'):
            cmd = resp.split(':', 1)[1].strip()
            if cmd:
                out = run_command(cmd)
                speak_text("Command executed. Check logs for output.")
    except Exception as e:
        print("Error handling interaction:", e)
        speak_text("Sorry, I encountered an error.")


def main():
    print("Starting Jarvis Service (Phase One)")
    init_db()
    ollama = OllamaClient(os.getenv('OLLAMA_URL', 'http://localhost:11434'))

    try:
        while True:
            try:
                if use_porcupine:
                    import sounddevice as sd, struct
                    with sd.RawInputStream(samplerate=sample_rate, blocksize=frame_length, dtype='int16', channels=1) as stream:
                        pcm = stream.read(frame_length)[0]
                        pcm = struct.unpack_from('h' * (len(pcm) // 2), pcm)
                        result = wake_porcupine.process(pcm)
                        if result >= 0:
                            t = threading.Thread(target=handle_interaction, args=(ollama,))
                            t.start()
                            t.join()
                elif use_vosk:
                    detected = wake_vosk.listen_once()
                    if detected:
                        t = threading.Thread(target=handle_interaction, args=(ollama,))
                        t.start()
                        t.join()
                else:
                    # No hotkey fallback: block until a supported backend triggers
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("Shutting down Jarvis (keyboard interrupt)")
                break
            except Exception as e:
                print("Runtime error in main loop:", e)
                time.sleep(1)
    finally:
        print("Jarvis service stopped")


if __name__ == '__main__':
    main()
