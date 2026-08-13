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
            # restrict grammar to the wake phrase to reduce false positives
            self.rec = self.KaldiRecognizer(self.model, self.sample_rate, '["hey buddy"]')

    def listen_once(self):
        import sounddevice as sd
        import struct
        import queue as _queue
        self._ensure_model()
        q = _queue.Queue()

        def callback(indata, frames, time, status):
            q.put(bytes(indata))

        # block until the wake phrase is detected
        with sd.RawInputStream(samplerate=self.sample_rate, blocksize=8000, dtype='int16', channels=1, callback=callback):
            while True:
                data = q.get()
                if self.rec.AcceptWaveform(data):
                    res = json.loads(self.rec.Result())
                    text = res.get('text', '')
                    if 'hey buddy' in text.lower():
                        return True
