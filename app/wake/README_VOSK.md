VOSK model setup

Download a VOSK small English model and set VOSK_MODEL_PATH in your .env file.
Example:
1) Download: https://alphacephei.com/vosk/models (e.g. vosk-model-small-en-us-0.15)
2) Unzip to C:\models\vosk-model-small-en-us-0.15
3) In .env:
   WAKE_BACKEND=vosk
   VOSK_MODEL_PATH=C:\models\vosk-model-small-en-us-0.15
   VOSK_SAMPLE_RATE=16000

Run Jarvis GUI or service as usual: python jarvis_gui.py or python jarvis_service.py
