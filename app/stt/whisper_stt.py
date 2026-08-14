import tempfile
import time
import os
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wavfile
from faster_whisper import WhisperModel

MODEL = os.getenv('WHISPER_MODEL', 'medium')
model = WhisperModel(MODEL, device="cpu", compute_type="int8")

def record_to_wav(duration=5, rate=16000):
    print(f"Recording {duration}s from default microphone...")
    data = sd.rec(int(duration * rate), samplerate=rate, channels=1, dtype='int16')
    sd.wait()
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    wavfile.write(tf.name, rate, data)
    return tf.name

# (VAD implementation remains here for future use)
def record_vad_to_wav(max_seconds: float = 6.0, silence_duration: float = 0.8, rate: int = 16000, vad_threshold: float = 1.2):
    # ... (keep existing VAD code unmodified) ...
    pass  # keep full VAD implementation in-place; not used by Phase One recorder

def transcribe_from_microphone(duration=6):
    """
    Phase One: use fixed-duration recording (duration seconds) and transcribe with faster-whisper.
    Returns transcribed text (may be empty string).
    """
    rate = int(os.getenv('VOSK_SAMPLE_RATE', os.getenv('TRANSCRIBE_SAMPLE_RATE', '16000')))
    max_seconds = float(os.getenv('MAX_RECORD_SECONDS', str(duration)))

    print("Recording user utterance...")
    wavpath = record_to_wav(duration=max_seconds, rate=rate)

    if not wavpath:
        return ""

    print(f"Recording saved to {wavpath}, starting transcription...")
    try:
        segments, info = model.transcribe(wavpath, beam_size=5)
        text = "".join([seg.text for seg in segments])
    except Exception as e:
        print("Error during transcription:", e)
        text = ""
    finally:
        try:
            os.remove(wavpath)
        except Exception:
            pass

    return text
