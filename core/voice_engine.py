"""
Voice Engine — Neural TTS Synthesis
Real-time speech generation for Jarvis v4.0.
"""
import os
import uuid
import logging
import asyncio
import edge_tts
import config

logger = logging.getLogger(__name__)

class VoiceEngine:
    """Neural Text-to-Speech Engine."""

    def __init__(self):
        self.voice_dir = config.VOICE_DIR
        os.makedirs(self.voice_dir, exist_ok=True)
        self.default_voice = getattr(config, "TTS_VOICE", "en-GB-RyanNeural")
        self.default_pitch = getattr(config, "TTS_PITCH", "-2Hz")
        self.default_rate = getattr(config, "TTS_RATE", "+0%")
        self.default_volume = getattr(config, "TTS_VOLUME", "+0%")

    async def speak(self, text: str, voice: str = None, pitch: str = None, rate: str = None, volume: str = None) -> dict:
        """
        Synthesize neural speech from text with Stark acoustic modulation.
        Returns the local filename and URL for the audio file.
        """
        voice = voice or self.default_voice
        pitch = pitch or self.default_pitch
        rate = rate or self.default_rate
        volume = volume or self.default_volume
        filename = f"speech_{uuid.uuid4().hex[:8]}.mp3"
        save_path = os.path.join(self.voice_dir, filename)

        try:
            # Neural synthesis via edge-tts (High fidelity)
            logger.info(f"Synthesizing neural voice ({voice}, {pitch}, {rate}) for: {text[:30]}...")
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
            await communicate.save(save_path)
            
            return {
                "status": "success",
                "url": f"/api/download/voice/{filename}",
                "filename": filename
            }

        except Exception as e:
            logger.error(f"Neural synthesis failure: {e}")
            return {"status": "error", "message": str(e)}

    async def transcribe(self, audio_path: str) -> dict:
        """
        Transcribe audio to text using Groq Whisper (Ultrafast).
        """
        if not config.GROQ_API_KEY:
            return {"status": "error", "message": "GROQ_API_KEY missing for transcription."}
        
        logger.info(f"Transcribing neural audio: {audio_path}")
        
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=config.GROQ_API_KEY
            )

            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), audio_file.read()),
                    model="whisper-large-v3",
                    response_format="text",
                )
            
            return {
                "status": "success",
                "text": transcription
            }

        except Exception as e:
            logger.error(f"Neural transcription failure: {e}")
            return {"status": "error", "message": str(e)}

    def speak_sync(self, text: str, voice: str = None) -> dict:
        """Synchronous wrapper for async speak."""
        return asyncio.run(self.speak(text, voice))
