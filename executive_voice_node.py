"""
Jarvis v14.0 — Executive Voice Node (IRON MAN MODE)
Real-time Mic-to-LLM-to-Cloned-Voice Interface
"""
import queue
import threading
import logging
import sounddevice as sd
import soundfile as sf
import numpy as np

# Note: Requires 'openai-whisper' and 'TTS' (Coqui XTTS v2)
try:
    import whisper
    from TTS.api import TTS
except ImportError:
    whisper = None
    TTS = None

import config
from core.brain import JarvisBrain
from core.agent_engine import AgentEngine

logger = logging.getLogger("jarvis.voice")

class VoiceNode:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.is_running = False
        
        # 1. Initialize Intelligence
        self.agent = AgentEngine()
        self.brain = JarvisBrain(self.agent)
        
        # 2. Local Models (Heavy)
        if whisper and TTS:
            logger.info("Voice Node: Loading Whisper & XTTS (Iron Man Mode)...")
            self.whisper_model = whisper.load_model("base")
            self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        else:
            logger.warning("Voice Node: Heavy AI libraries (Whisper/TTS) missing. Falling back to Lite Mode.")

    def audio_callback(self, indata, frames, time, status):
        """Streaming audio chunks from Mic."""
        if status:
            logger.error(status)
        
        # 🌊 Interruption Logic: Detect if user is speaking while Jarvis is talking
        energy = np.linalg.norm(indata)
        if energy > config.VOICE_THRESHOLD and self.is_speaking:
            logger.info("Interruption Node: User signal detected. Silencing Jarvis.")
            sd.stop()
            self.is_speaking = False

        self.audio_queue.put(indata.copy())

    def listen_loop(self):
        """The constant real-time listener + Wake Word detection."""
        samplerate = 16000
        with sd.InputStream(callback=self.audio_callback, channels=1, samplerate=samplerate):
            logger.info("Voice Node: JARVIS is listening...")
            self.is_running = True
            
            while self.is_running:
                # 👂 Wake Word / Continuous Transcription
                if self.audio_queue.qsize() > 5: # Process in chunks
                    chunk = self.audio_queue.get()
                    # Simplified Wake Word logic (Keyword check in transcription)
                    if whisper:
                        result = self.whisper_model.transcribe(chunk)
                        text = result['text'].lower()
                        if "jarvis" in text or "hey" in text:
                            logger.info("Wake Word Detected. Awaiting mission.")
                            # Trigger response flow...


    def speak(self, text, lang="en"):
        """Voice Cloning Output."""
        if not TTS:
            # Fallback to EdgeTTS if heavy TTS is missing
            logger.info("Speech fallback: EdgeTTS Output.")
            import asyncio
            import edge_tts
            communicate = edge_tts.Communicate(text, "en-GB-RyanNeural")
            asyncio.run(communicate.save("output_lite.mp3"))
            # Play mp3...
            return

        # Iron Man Mode: Cloned Voice
        self.tts.tts_to_file(
            text=text,
            speaker_wav="voice.wav", # 🔥 Ensure this file exists in root
            language=lang,
            file_path="output.wav"
        )
        data, fs = sf.read("output.wav")
        sd.play(data, fs)
        sd.wait()

    def start(self):
        self.is_running = True
        threading.Thread(target=self.listen_loop, daemon=True).start()

if __name__ == "__main__":
    node = VoiceNode()
    node.start()
    while True:
        try:
            # Main interaction logic
            pass
        except KeyboardInterrupt:
            break
