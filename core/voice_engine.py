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
        # Choosing a premium British neural voice (Stark/Jarvis persona)
        self.default_voice = "en-GB-RyanNeural" 

    async def speak(self, text: str, voice: str = None) -> dict:
        """
        Synthesize neural speech from text.
        Returns the local filename for the audio file.
        """
        voice = voice or self.default_voice
        filename = f"speech_{uuid.uuid4().hex[:8]}.mp3"
        save_path = os.path.join(self.voice_dir, filename)

        try:
            # Neural synthesis via edge-tts (High fidelity)
            logger.info(f"Synthesizing neural voice for: {text[:30]}...")
            communicate = edge_tts.Communicate(text, voice)
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
