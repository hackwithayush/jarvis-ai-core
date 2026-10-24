"""
Standardized Voice Node — JARVIS Phonic Engine
Neural TTS synthesis using edge-tts.
"""
import edge_tts
import asyncio
import os
import uuid
import config

async def speak(text: str, output: str = None) -> str:
    """
    Synthesize speech from text and save to file.
    Returns the path to the generated MP3.
    """
    if not output:
        filename = f"voice_{uuid.uuid4().hex[:8]}.mp3"
        output = os.path.join(config.VOICE_DIR, filename)

    voice = getattr(config, "TTS_VOICE", "en-GB-RyanNeural")
    pitch = getattr(config, "TTS_PITCH", "-2Hz")
    rate = getattr(config, "TTS_RATE", "+0%")
    volume = getattr(config, "TTS_VOLUME", "+0%")
    
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
    await communicate.save(output)
    
    return output
