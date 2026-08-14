import tempfile
import time
import os
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wavfile
from faster_whisper import WhisperModel

# model size for faster-whisper; keep as before
MODEL = os.getenv('WHISPER_MODEL', 'medium')

# Load model once at import time
model = WhisperModel(MODEL, device="cpu", compute_type="int8")


def _rms(samples: np.ndarray) -> float:
    if samples.dtype.kind == 'i':
        # int16 -> scale to [-1,1]
        samples = samples.astype('float32') / np.iinfo(samples.dtype).max
    elif samples.dtype.kind == 'f':
        samples = samples.astype('float32')
    return float(np.sqrt(np.mean(np.square(samples))))


def _record_chunk(seconds: float, rate: int):
    frames = sd.rec(int(seconds * rate), samplerate=rate, channels=1, dtype='int16')
    sd.wait()
    return frames


def record_vad_to_wav(max_seconds: float = 6.0, silence_duration: float = 0.8, rate: int = 16000, vad_threshold: float = 1.2):
    """Record audio using a simple energy-based VAD.

    - Samples ambient noise for a short period to compute a threshold.
    - Waits for speech onset, then records until silence_duration seconds of low energy
      are observed or max_seconds is reached.
    - Writes the recorded audio to a temporary WAV file and returns its path.
    """
    chunk_sec = 0.2
    ambient_sec = min(1.0, max(0.2, 0.5))

    print(f"VAD recording: sampling ambient for {ambient_sec}s to set threshold")
    ambient = _record_chunk(ambient_sec, rate)
    ambient_rms = _rms(ambient)
    # Use a modest floor to avoid a threshold of exactly zero on silent devices
    min_floor = 1e-6
    threshold = max(min_floor, ambient_rms * vad_threshold)
    print(f"Ambient RMS={ambient_rms:.6f}, vad threshold={threshold:.6f} (multiplier={vad_threshold})")

    started = False
    silence_time = 0.0
    recorded_chunks = []
    total_time = 0.0

    print("Waiting for speech...")
    start_time = time.time()
    while total_time < max_seconds:
        chunk = _record_chunk(chunk_sec, rate)
        total_time = time.time() - start_time
        rms = _rms(chunk)

        # Print live RMS so we can observe microphone level
        print(f"Chunk RMS={rms:.6f} (threshold={threshold:.6f})")

        if not started:
            if rms >= threshold:
                started = True
                recorded_chunks.append(chunk)
                silence_time = 0.0
                print(f"Speech detected (rms={rms:.6f}), start recording")
            else:
                # still waiting for speech
                pass
        else:
            recorded_chunks.append(chunk)
            if rms < threshold:
                silence_time += chunk_sec
            else:
                silence_time = 0.0

            if silence_time >= silence_duration:
                print(f"Silence detected for {silence_time}s, stopping recording")
                break

        # safety: check max seconds again
        if (time.time() - start_time) >= max_seconds:
            print("Reached maximum recording duration, stopping")
            break

    if not started:
        # No speech detected
        print("No speech was detected during recording window")
        return None

    # concatenate recorded chunks
    audio = np.concatenate(recorded_chunks, axis=0)
    # ensure correct dtype
    audio = audio.reshape(-1, 1)

    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    wavfile.write(tf.name, rate, audio)
    return tf.name


def transcribe_from_microphone(duration=6):
    """Record using VAD and transcribe with faster-whisper.

    - duration parameter is used as a fallback for MAX_RECORD_SECONDS if the env var is not set.
    - Returns the transcribed text (possibly empty string) or empty string if no speech.
    """
    rate = int(os.getenv('VOSK_SAMPLE_RATE', os.getenv('TRANSCRIBE_SAMPLE_RATE', '16000')))
    max_seconds = float(os.getenv('MAX_RECORD_SECONDS', str(duration)))
    silence_duration = float(os.getenv('SILENCE_DURATION', '0.8'))
    vad_threshold = float(os.getenv('VAD_THRESHOLD', '1.2'))

    wavpath = record_vad_to_wav(max_seconds=max_seconds, silence_duration=silence_duration, rate=rate, vad_threshold=vad_threshold)
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
