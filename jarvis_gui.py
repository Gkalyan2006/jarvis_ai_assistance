"""
Jarvis GUI - Siri-like desktop interface with WAKE_BACKEND support
Supports WAKE_BACKEND=vosk|porcupine|whisper (vosk is default)
"""
import os
import threading
import time
import sys
from dotenv import load_dotenv
load_dotenv()

import tkinter as tk
from tkinter.scrolledtext import ScrolledText

# tray icon
try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except Exception:
    PYSTRAY_AVAILABLE = False

from app.stt.whisper_stt import transcribe_from_microphone
from app.llm.ollama_client import OllamaClient
from app.tts.tts import speak_text
from app.db.init_db import init_db, log_activity
from app.automation.windows_automation import open_app, run_command

# Wake backend selection
WAKE_BACKEND = os.getenv('WAKE_BACKEND', 'vosk').lower()

# Porcupine availability (optional)
try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except Exception:
    PORCUPINE_AVAILABLE = False

# VOSK availability will be checked when used


def create_image(color1=(0, 122, 255), color2=(255, 255, 255)):
    # simple circle icon
    img = Image.new('RGB', (64, 64), color2)
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill=color1)
    return img


class JarvisGUI:
    def __init__(self, root):
        self.root = root
        root.title('Jarvis')
        root.geometry('420x300')
        root.attributes('-topmost', True)

        self.status_var = tk.StringVar(value='Idle')
        self.label = tk.Label(root, textvariable=self.status_var, font=('Segoe UI', 14))
        self.label.pack(pady=6)

        self.log = ScrolledText(root, height=10)
        self.log.pack(fill='both', expand=True, padx=6, pady=6)

        btn_frame = tk.Frame(root)
        btn_frame.pack(fill='x', padx=6, pady=4)

        self.hide_btn = tk.Button(btn_frame, text='Hide', command=self.hide_window)
        self.hide_btn.pack(side='left')

        self.quit_btn = tk.Button(btn_frame, text='Exit', command=self.stop_and_exit)
        self.quit_btn.pack(side='right')

        self.running = False
        self.thread = None
        self.ollama = OllamaClient(os.getenv('OLLAMA_URL', 'http://localhost:11434'))

        # Wake backend init
        self.use_porcupine = False
        self.use_vosk = False
        if WAKE_BACKEND == 'porcupine' and PORCUPINE_AVAILABLE:
            keyword_path = os.getenv('PORCUPINE_KEYWORD_PATH')
            library_path = os.getenv('PORCUPINE_LIBRARY_PATH')
            sensitivity = float(os.getenv('PORCUPINE_SENSITIVITY', '0.5'))
            if keyword_path:
                try:
                    self.porcupine = pvporcupine.create(keyword_paths=[keyword_path], sensitivities=[sensitivity], library_path=library_path if library_path else None)
                    self.sample_rate = self.porcupine.sample_rate
                    self.frame_length = self.porcupine.frame_length
                    self.use_porcupine = True
                    self.log_write('Porcupine initialized')
                except Exception as e:
                    self.log_write(f'Porcupine init failed: {e}')

        elif WAKE_BACKEND == 'vosk':
            try:
                from app.wake.vosk_wake import VoskWakeListener
                model_path = os.getenv('VOSK_MODEL_PATH')
                if not model_path:
                    raise RuntimeError('VOSK_MODEL_PATH not set')
                self.vosk = VoskWakeListener(model_path=model_path, sample_rate=int(os.getenv('VOSK_SAMPLE_RATE', '16000')))
                self.use_vosk = True
                self.log_write('VOSK wake listener initialized')
            except Exception as e:
                self.log_write(f'VOSK init failed: {e}')
                raise
        else:
            self.log_write(f'Unsupported WAKE_BACKEND: {WAKE_BACKEND}')
            raise SystemExit('No supported wake backend available')

        init_db()

        if PYSTRAY_AVAILABLE:
            self.icon = pystray.Icon('jarvis', create_image(), 'Jarvis')
            self.icon.menu = pystray.Menu(pystray.MenuItem('Show', self.show_window), pystray.MenuItem('Exit', self.stop_and_exit))
            t = threading.Thread(target=self.icon.run, daemon=True)
            t.start()

        self.start_listener()

    def log_write(self, text):
        ts = time.strftime('%H:%M:%S')
        self.log.insert('end', f'[{ts}] {text}\n')
        self.log.see('end')

    def show_window(self, icon=None, item=None):
        try:
            self.root.deiconify()
        except Exception:
            pass

    def hide_window(self):
        self.root.withdraw()

    def stop_and_exit(self, icon=None, item=None):
        self.running = False
        try:
            if PYSTRAY_AVAILABLE:
                self.icon.stop()
        except Exception:
            pass
        self.root.quit()

    def start_listener(self):
        self.running = True
        self.thread = threading.Thread(target=self.listener_loop, daemon=True)
        self.thread.start()

    def listener_loop(self):
        if self.use_porcupine:
            import sounddevice as sd
            import struct
            with sd.RawInputStream(samplerate=self.sample_rate, blocksize=self.frame_length, dtype='int16', channels=1) as stream:
                self.log_write('Listening for wake-word (Porcupine)...')
                while self.running:
                    try:
                        pcm = stream.read(self.frame_length)[0]
                        if not pcm:
                            continue
                        pcm = struct.unpack_from('h' * (len(pcm) // 2), pcm)
                        result = self.porcupine.process(pcm)
                        if result >= 0:
                            self.on_wake()
                    except Exception as e:
                        self.log_write(f'Listen error: {e}')
                        time.sleep(0.5)

        elif self.use_vosk:
            self.log_write('Listening for wake-word (VOSK)...')
            while self.running:
                try:
                    detected = self.vosk.listen_once()
                    if detected:
                        self.on_wake()
                except Exception as e:
                    self.log_write(f'VOSK listen error: {e}')
                    time.sleep(0.5)

    def on_wake(self):
        self.status_var.set('Listening...')
        self.log_write('Wake word detected')
        try:
            transcript = transcribe_from_microphone(duration=6)
            self.log_write(f'You: {transcript}')
            resp = self.ollama.chat(transcript)
            self.log_write(f'Jarvis: {resp}')
            self.status_var.set('Speaking...')
            speak_text(resp)
            self.status_var.set('Idle')
            try:
                import asyncio
                asyncio.run(log_activity(action='interaction', details=f'user: {transcript} | assistant: {resp}'))
            except Exception:
                log_activity(action='interaction', details=f'user: {transcript} | assistant: {resp}')
            # automation triggers
            if resp.strip().upper().startswith('OPEN:'):
                path = resp.split(':', 1)[1].strip()
                if path:
                    open_app(path)
                    speak_text(f'Opening {path}')
            if resp.strip().upper().startswith('RUN:'):
                cmd = resp.split(':', 1)[1].strip()
                if cmd:
                    out = run_command(cmd)
                    speak_text('Command executed')
        except Exception as e:
            self.log_write(f'Interaction error: {e}')
            speak_text('Sorry, I had an error')
            self.status_var.set('Idle')


if __name__ == '__main__':
    root = tk.Tk()
    app = JarvisGUI(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.stop_and_exit()
