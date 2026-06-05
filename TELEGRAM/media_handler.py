"""
Media Handler
Processes incoming Voice Notes using the local Faster-Whisper STT.
"""
import os
import sys
import pathlib

# Append root so we can import VOICE
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.absolute()))
from VOICE.speech_to_text.faster_whisper_engine import FasterWhisperEngine

class MediaHandler:
    def __init__(self):
        # Initializes STT only if needed to save VRAM on boot
        self.stt = None 
        print("[MEDIA] Media Handler ready to process voice notes.")
        
    def transcribe_voice_note(self, file_path: str) -> str:
        """ Transcribes a downloaded Telegram OGG voice note. """
        if not self.stt:
             print("[MEDIA] Loading Whisper model to transcribe remote voice note...")
             self.stt = FasterWhisperEngine(model_size="base")
             
        text = self.stt.transcribe(file_path)
        
        # Clean up the file to save disk space
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return text
