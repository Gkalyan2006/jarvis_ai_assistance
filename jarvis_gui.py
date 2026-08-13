"""
Jarvis GUI - Siri-like desktop interface

Usage: python jarvis_gui.py
Or use run_gui.bat on Windows.

Features:
- System tray icon (pystray) with menu: Show/Hide, Exit
- Small floating Tkinter window showing status, last transcript, last response
- Always-on wake-word listening using Porcupine (if configured), fallback to hotkey
- Uses the same core interaction flow: STT (faster-whisper) -> Ollama -> TTS (pyttsx3)

Environment variables: same as jarvis_service
- PORCUPINE_KEYWORD_PATH, PORCUPINE_LIBRARY_PATH, PORCUPINE_SENSITIVITY
- OLLAMA_URL

Notes:
- Requires pillow and pystray for system tray functionality
- Tkinter is part of the Python standard library on Windows
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

# Porcupine
try:
    import pvporcupine
    import sounddevice as sd
    import struct
    PORCUPINE_AVAILABLE = True
except Exception:
    PORCUPINE_AVAILABLE = False


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

        keyword_path = os.getenv('PORCUPINE_KEYWORD_PATH')
        library_path = os.getenv('PORCUPINE_LIBRARY_PATH')
        sensitivity = float(os.getenv('PORCUPINE_SENSITIVITY', '0.5'))
        self.use_porcupine = PORCUPINE_AVAILABLE and keyword_path
        self.keyword_path = keyword_path
        self.library_path = library_path
        self.sensitivity = sensitivity

        if self.use_porcupine:
            try:
                self.porcupine = pvporcupine.create(keyword_paths=[self.keyword_path], sensitivities=[self.sensitivity], library_path=self.library_path if self.library_path else None)
                self.sample_rate = self.porcupine.sample_rate
                self.frame_length = self.porcupine.frame_length
                self.log_write('Porcupine initialized')
            except Exception as e:
                self.log_write(f'Porcupine init failed: {e}')
                self.use_porcupine = False

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
            # use RawInputStream
            with sd.RawInputStream(samplerate=self.sample_rate, blocksize=self.frame_length, dtype='int16', channels=1) as stream:
                self.log_write('Listening for wake-word...')
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
        else:
            self.log_write('Fallback hotkey: press Enter in console to trigger')
            while self.running:
                try:
                    input()  # blocks
                    self.on_wake()
                except Exception as e:
                    self.log_write(f'Hotkey error: {e}')

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
