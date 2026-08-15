"""
VAD recorder tuned for post-wake capture with pre/post buffers and configurable thresholds.
Provides a simple energy-based VAD with pre-speech buffering and post-speech padding.
"""
import tempfile
import time
import os
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wavfile

from typing import Optional, Tuple

# Default configuration is read from environment where appropriate
DEFAULT_RATE = int(os.getenv('VOSK_SAMPLE_RATE', os.getenv('TRANSCRIBE_SAMPLE_RATE', '16000')))


def _rms(samples: np.ndarray) -> float:
    if samples.dtype.kind == 'i':
        samples = samples.astype('float32') / np.iinfo(samples.dtype).max
    else:
        samples = samples.astype('float32')
    return float(np.sqrt(np.mean(np.square(samples))))


def _record_frames(seconds: float, rate: int = DEFAULT_RATE) -> np.ndarray:
    frames = sd.rec(int(seconds * rate), samplerate=rate, channels=1, dtype='int16')
    sd.wait()
    return frames


def vad_record(pre_buffer: float = 0.3,
               post_padding: float = 0.2,
               min_speech_seconds: float = 0.2,
               silence_duration: float = 0.8,
               max_utterance: float = 8.0,
               rate: int = DEFAULT_RATE,
               chunk_sec: float = 0.2,
               vad_threshold: float = 1.2) -> Optional[str]:
    """Record after wake-word using energy-based VAD with pre/post buffers.

    Returns path to WAV file with the captured utterance or None if nothing detected.

    Strategy:
    - Capture an initial small pre-buffer (pre_buffer) so we have audio that occurred
      immediately before speech onset (accounts for users who start quickly).
    - Continuously record in chunks. Maintain a rolling buffer of audio frames.
    - When RMS exceeds threshold (ambient_rms * vad_threshold) and stays above for
      min_speech_seconds, mark speech started.
    - After speech started, keep recording until silence_duration seconds of low energy are observed,
      but include post_padding seconds after that to avoid clipping.
    - Cap recording at max_utterance seconds.
    """
    # sample ambient to set threshold
    ambient_sec = min(1.0, max(0.2, pre_buffer))
    ambient = _record_frames(ambient_sec, rate=rate)
    ambient_rms = _rms(ambient)
    min_floor = 1e-6
    threshold = max(min_floor, ambient_rms * vad_threshold)

    print(f"[VAD] ambient_rms={ambient_rms:.6f}, threshold={threshold:.6f} (mult={vad_threshold})")

    # Rolling buffers (as list of numpy arrays)
    pre_frames = []
    recorded_frames = []
    pre_frames_time = 0.0
    recorded_time = 0.0

    start_time = time.time()
    speech_started = False
    silence_accum = 0.0
    min_speech_accum = 0.0

    # fill initial pre_buffer
    if pre_buffer > 0:
        f = _record_frames(pre_buffer, rate=rate)
        pre_frames.append(f)
        pre_frames_time += pre_buffer

    # main loop
    while recorded_time < max_utterance:
        chunk = _record_frames(chunk_sec, rate=rate)
        recorded_time = time.time() - start_time
        rms = _rms(chunk)

        print(f"[VAD] chunk_rms={rms:.6f} (threshold={threshold:.6f}) recorded_time={recorded_time:.2f}s")

        if not speech_started:
            # accumulate pre-buffer
            pre_frames.append(chunk)
            pre_frames_time += chunk_sec
            # keep pre_frames length bounded to pre_buffer
            while pre_frames_time > pre_buffer and len(pre_frames) > 0:
                removed = pre_frames.pop(0)
                pre_frames_time -= chunk_sec

            # check for speech onset
            if rms >= threshold:
                min_speech_accum += chunk_sec
                if min_speech_accum >= min_speech_seconds:
                    speech_started = True
                    print(f"[VAD] Speech started after {recorded_time:.2f}s")
                    # move pre_frames into recorded_frames
                    recorded_frames.extend(pre_frames)
                    recorded_frames.append(chunk)
                    silence_accum = 0.0
            else:
                min_speech_accum = 0.0

        else:
            recorded_frames.append(chunk)
            if rms < threshold:
                silence_accum += chunk_sec
            else:
                silence_accum = 0.0

            if silence_accum >= silence_duration:
                # include post_padding by recording extra frames
                if post_padding > 0:
                    pad_frames = _record_frames(post_padding, rate=rate)
                    recorded_frames.append(pad_frames)
                print(f"[VAD] End of speech detected (silence_accum={silence_accum:.2f}s). Stopping.")
                break

        # safety exit if time exceeded
        if (time.time() - start_time) >= max_utterance:
            print("[VAD] Reached max utterance duration; stopping")
            break

    if not speech_started:
        print("[VAD] No speech detected in utterance window")
        return None

    # concatenate frames
    audio = np.concatenate(recorded_frames, axis=0)
    audio = audio.reshape(-1, 1)

    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    wavfile.write(tf.name, rate, audio)
    print(f"[VAD] Saved recorded utterance to {tf.name}")
    return tf.name
