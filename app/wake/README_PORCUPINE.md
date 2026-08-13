# Porcupine setup notes

This project expects you to obtain a Porcupine keyword (.ppn) file for your
wake word (for example, "Hey Buddy"). Porcupine keyword files and library
binaries come from Picovoice and may require registration and an access key.

Steps to obtain keyword and library (summary):
1. Register at https://console.picovoice.ai/ and create a Porcupine keyword for "Hey Buddy".
2. Download the `.ppn` keyword file for the platform (Windows x64) and the
dynamic library (.dll).
3. Place the `.ppn` file somewhere on your disk and set the environment variable
   PORCUPINE_KEYWORD_PATH to that full path.
4. If needed, set PORCUPINE_LIBRARY_PATH to the Porcupine native library path.

If you cannot obtain Porcupine, the service will fall back to a push-to-talk
hotkey (press Enter) to start recording.
