import re
import threading

import pyttsx3


class SpeechService:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.enabled = True
        self._configure_voice()

    def _configure_voice(self):
        voices = self.engine.getProperty("voices")
        for voice in voices:
            if "zira" in voice.name.lower() or "female" in voice.name.lower():
                self.engine.setProperty("voice", voice.id)
                break
        self.engine.setProperty("rate", 140)
        self.engine.setProperty("volume", 1.0)

    def set_enabled(self, enabled):
        self.enabled = enabled

    def speak_async(self, text):
        if not self.enabled:
            return
        threading.Thread(target=self._speak, args=(text,), daemon=True).start()

    def _speak(self, text):
        try:
            clean_text = re.sub(r"[^a-zA-Z0-9\s]", "", str(text))
            self.engine.say(clean_text)
            self.engine.runAndWait()
        except Exception as exc:
            print(f"TTS Error: {exc}")
