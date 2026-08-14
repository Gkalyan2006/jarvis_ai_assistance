import queue
import json

class VoskWakeListener:
    """
    Vosk-based wake listener for a fixed phrase ("hey buddy").
    Usage:
      listener = VoskWakeListener(model_path=r"C:\models\vosk-model-small-en-us-0.15")
      while running:
          listener.listen_once()
          # do wake action
    """
    def __init__(self, model_path: str, sample_rate: int = 16000):
        from vosk import Model, KaldiRecognizer
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.Model = Model
        self.KaldiRecognizer = KaldiRecognizer
        self.model = None
        self.rec = None

    def _ensure_model(self):
        if self.model is None:
            self.model = self.Model(self.model_path)
            self._reset_recognizer()

    def _reset_recognizer(self):
        # Create a fresh recognizer instance restricted to the wake phrase grammar
        # so each listen cycle starts from a clean state.
        try:
            self.rec = self.KaldiRecognizer(self.model, self.sample_rate, '["hey buddy"]')
        except Exception:
            # Fallback: create without grammar if the grammar causes issues
            self.rec = self.KaldiRecognizer(self.model, self.sample_rate)

    def listen_once(self) -> bool:
        import sounddevice as sd
        import struct
        import queue as _queue
        import time

        self._ensure_model()

        q = _queue.Queue()

        def callback(indata, frames, timestamp, status):
            if status:
                # print status for debugging
                print(f"[VOSK] InputStream status: {status}")
            q.put(bytes(indata))

        print('[VOSK] Listening for "Hey Buddy"...')

        # block until the wake phrase is detected
        with sd.RawInputStream(samplerate=self.sample_rate, blocksize=8000, dtype='int16', channels=1, callback=callback):
            while True:
                try:
                    data = q.get()
                except Exception:
                    # if queue fails, wait briefly and continue
                    time.sleep(0.01)
                    continue

                # Feed audio to recognizer
                if self.rec.AcceptWaveform(data):
                    try:
                        res = json.loads(self.rec.Result())
                    except Exception:
                        res = {}
                    text = res.get('text', '') if isinstance(res, dict) else ''
                    if text:
                        print(f"[VOSK][final] Recognized: {text}")
                    else:
                        print("[VOSK][final] No final text")

                    if 'hey buddy' in text.lower():
                        print('[VOSK] Wake word detected (final).')
                        # Reinitialize recognizer for the next wake cycle
                        self._reset_recognizer()
                        return True

                else:
                    # partial result is available; check it as well
                    try:
                        pres = json.loads(self.rec.PartialResult())
                    except Exception:
                        pres = {}
                    ptext = pres.get('partial', '') if isinstance(pres, dict) else ''
                    if ptext:
                        print(f"[VOSK][partial] Recognized: {ptext}")
                    # Check partial transcripts for wake phrase
                    if 'hey buddy' in ptext.lower():
                        print('[VOSK] Wake word detected (partial).')
                        # Reinitialize recognizer for the next wake cycle
                        self._reset_recognizer()
                        return True
