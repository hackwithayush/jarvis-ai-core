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

    # English British (Christopher) for the premium Jarvis feel
    # The prompt specifically mentioned en-US-ChristopherNeural, so I will follow it.
    voice = "en-US-ChristopherNeural" 
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output)
    
    return output
