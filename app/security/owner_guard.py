"""
Owner voice/passphrase guard for Jarvis Phase One
"""
import os
import tempfile
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wavfile

# Try multiple import paths for EncoderClassifier depending on SpeechBrain version
try:
    from speechbrain.pretrained import EncoderClassifier
except Exception:
    try:
        from speechbrain.inference.speaker import EncoderClassifier
    except Exception as e:
        raise ImportError("SpeechBrain EncoderClassifier not available: " + str(e))

# Configuration from environment
OWNER_VOICE_PATH = os.getenv('OWNER_VOICE_PATH', 'data/owner_voice.npy')
OWNER_VOICE_THRESHOLD = float(os.getenv('OWNER_VOICE_THRESHOLD', '0.45'))
OWNER_PASSPHRASE = os.getenv('OWNER_PASSPHRASE', 'blue quantum tiger')
OWNER_VERIFY_SECONDS = float(os.getenv('OWNER_VERIFY_SECONDS', '2.5'))
SAMPLE_RATE = int(os.getenv('VOSK_SAMPLE_RATE', os.getenv('TRANSCRIBE_SAMPLE_RATE', '16000')))

# Load enrolled owner embedding
_owner_embedding = None
if os.path.exists(OWNER_VOICE_PATH):
    try:
        _owner_embedding = np.load(OWNER_VOICE_PATH)
    except Exception as e:
        print(f"[SECURITY] Failed to load owner embedding from {OWNER_VOICE_PATH}: {e}")
        _owner_embedding = None
else:
    print(f"[SECURITY] Owner embedding file not found at {OWNER_VOICE_PATH}")

# Load speechbrain encoder lazily to avoid heavy import at module import time
_encoder = None

def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            _encoder = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir="pretrained_models/spkrec-ecapa-voxceleb")
        except Exception as e:
            print(f"[SECURITY] Failed to load EncoderClassifier: {e}")
            _encoder = None
    return _encoder


def _record_temp_wav(seconds: float = 2.5, rate: int = SAMPLE_RATE):
    """Record `seconds` from the default microphone and return a temp wav path."""
    data = sd.rec(int(seconds * rate), samplerate=rate, channels=1, dtype='int16')
    sd.wait()
    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    wavfile.write(tf.name, rate, data)
    return tf.name


def verify_owner(threshold: float | None = None) -> bool:
    """Record a short sample and compare speaker embedding to the enrolled owner.

    Returns True if similarity >= threshold, False otherwise. Prints similarity for debugging.
    """
    global _owner_embedding
    if threshold is None:
        threshold = OWNER_VOICE_THRESHOLD

    if _owner_embedding is None:
        print('[SECURITY] No enrolled owner embedding available; denying access')
        return False

    encoder = _get_encoder()
    if encoder is None:
        print('[SECURITY] Speaker encoder not available; denying access')
        return False

    # Record a short sample
    try:
        wav = _record_temp_wav(seconds=OWNER_VERIFY_SECONDS, rate=SAMPLE_RATE)
    except Exception as e:
        print(f'[SECURITY] Failed to record audio for verification: {e}')
        return False

    try:
        # Compute embedding for sample
        sample_emb = encoder.encode_file(wav)
        # convert to numpy
        try:
            sample_emb = sample_emb.detach().cpu().numpy().squeeze()
        except Exception:
            sample_emb = np.array(sample_emb).squeeze()

        # owner embedding may be stored as numpy array
        owner_emb = np.array(_owner_embedding).squeeze()

        # cosine similarity
        num = float(np.dot(owner_emb, sample_emb))
        denom = float(np.linalg.norm(owner_emb) * np.linalg.norm(sample_emb) + 1e-10)
        similarity = num / denom if denom > 0 else 0.0
        print(f"[SECURITY] similarity={similarity:.4f}")

        return similarity >= threshold
    except Exception as e:
        print(f'[SECURITY] Error during owner verification: {e}')
        return False
    finally:
        try:
            os.remove(wav)
        except Exception:
            pass


def verify_passphrase(text: str) -> bool:
    """Verify the transcribed passphrase against the configured owner passphrase.

    Do not log the actual passphrase. Return True if matches, False otherwise.
    """
    if not text:
        return False
    # normalize whitespace and case
    normalized = " ".join(text.strip().lower().split())
    expected = " ".join(OWNER_PASSPHRASE.strip().lower().split())
    return normalized == expected
