import tempfile
import sounddevice as sd
import scipy.io.wavfile as wavfile
from faster_whisper import WhisperModel

MODEL = "medium"  # faster-whisper model size for demo

model = WhisperModel(MODEL, device="cpu", compute_type="int8")

def record_to_wav(duration=5, rate=16000):
    print(f"Recording {duration}s from default microphone...")
    data = sd.rec(int(duration * rate), samplerate=rate, channels=1, dtype='int16')
    sd.wait()
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    wavfile.write(tf.name, rate, data)
    return tf.name


def transcribe_from_microphone(duration=5):
    wavpath = record_to_wav(duration=duration)
    segments, info = model.transcribe(wavpath, beam_size=5)
    text = "".join([seg.text for seg in segments])
    return text
