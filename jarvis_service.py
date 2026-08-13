"""
Jarvis Service - Always-on wake-word listener and assistant loop
Runs on Windows 11, listens for the wake word (Porcupine) and then records,
transcribes (faster-whisper), queries local Ollama, and speaks response.

Run: python jarvis_service.py

Environment Variables (.env):
- OLLAMA_URL (e.g., http://localhost:11434)
- API_TOKEN (for mobile API if enabled)
- PORCUPINE_LIBRARY_PATH (optional) - path to Porcupine shared lib if needed
- PORCUPINE_KEYWORD_PATH (required for wake-word) - path to .ppn keyword file
- PORCUPINE_SENSITIVITY (optional, float 0-1)

If Porcupine is not available or no keyword path is set, the service falls back
to a push-to-talk fallback: press Enter to start recording.
"""
import os
import time
import sys
import threading
from dotenv import load_dotenv

load_dotenv()

from app.stt.whisper_stt import transcribe_from_microphone
from app.llm.ollama_client import OllamaClient
from app.tts.tts import speak_text
from app.db.init_db import init_db, log_activity
from app.automation.windows_automation import open_app, run_command

# Optional Porcupine wake-word listener
try:
    import pvporcupine
    import struct
    import sounddevice as sd
    PORCUPINE_AVAILABLE = True
except Exception:
    PORCUPINE_AVAILABLE = False


class PorcupineWakeListener:
    def __init__(self, keyword_path: str, library_path: str = None, sensitivity: float = 0.5):
        if not PORCUPINE_AVAILABLE:
            raise RuntimeError("pvporcupine is not installed or could not be imported")
        kwargs = {}
        if library_path:
            kwargs['library_path'] = library_path
        self.porcupine = pvporcupine.create(keyword_paths=[keyword_path], sensitivities=[sensitivity], **kwargs)
        self.sample_rate = self.porcupine.sample_rate
        self.frame_length = self.porcupine.frame_length

    def listen_once(self):
        # blocking listen until wake word triggers
        print("Listening for wake-word...")
        with sd.RawInputStream(samplerate=self.sample_rate, blocksize=self.frame_length, dtype='int16', channels=1) as stream:
            while True:
                pcm = stream.read(self.frame_length)[0]
                if not pcm:
                    continue
                pcm = struct.unpack_from("h" * (len(pcm) // 2), pcm)
                result = self.porcupine.process(pcm)
                if result >= 0:
                    print("Wake word detected")
                    return True


def fallback_hotkey_wait():
    input("Press Enter to speak (fallback hotkey)...")


def handle_interaction(ollama: OllamaClient):
    try:
        # record ~6 seconds for user utterance
        print("Recording user utterance...")
        transcript = transcribe_from_microphone(duration=6)
        print(f"User said: {transcript}")
        # call LLM
        resp = ollama.chat(transcript)
        print(f"Assistant: {resp}")
        speak_text(resp)
        # log
        try:
            # asyncio not required; init_db uses sqlite sync functions
            import asyncio
            asyncio.run(log_activity(action="interaction", details=f"user: {transcript} | assistant: {resp}"))
        except Exception:
            # fallback synchronous
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

    keyword_path = os.getenv('PORCUPINE_KEYWORD_PATH')
    library_path = os.getenv('PORCUPINE_LIBRARY_PATH')
    sensitivity = float(os.getenv('PORCUPINE_SENSITIVITY', '0.5'))

    use_porcupine = PORCUPINE_AVAILABLE and keyword_path
    if use_porcupine:
        try:
            wake = PorcupineWakeListener(keyword_path=keyword_path, library_path=library_path, sensitivity=sensitivity)
            print("Porcupine wake listener initialized")
        except Exception as e:
            print("Failed to initialize Porcupine:", e)
            use_porcupine = False

    print("Jarvis is ready. Say the wake word or use fallback hotkey.")

    try:
        while True:
            try:
                if use_porcupine:
                    wake.listen_once()
                else:
                    fallback_hotkey_wait()
                # handle in separate thread to avoid blocking wake listener (if you want continuous)
                t = threading.Thread(target=handle_interaction, args=(ollama,))
                t.start()
                # optionally join if you want to block until finished
                t.join()
                # short cooldown
                time.sleep(0.5)
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
