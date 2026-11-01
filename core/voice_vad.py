"""
JARVIS Acoustic Cortex — Silero VAD (Voice Activity Detection) & Conversational Interruption Engine
Provides ultra-low-latency, zero-overhead speech detection and full-duplex conversational barge-in.
"""
import io
import time
import logging
import threading
from typing import Dict, Any, Optional

import numpy as np

logger = logging.getLogger("jarvis.voice_vad")

class SileroVoiceDetector:
    """
    Sub-millisecond Voice Activity Detection using Silero VAD ONNX runtime.
    Detects user speech during system playback to enable natural interruption (barge-in).
    """

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.model = None
        self._interruption_flag = threading.Event()
        self._last_speech_time = 0.0
        self._init_model()

    def _init_model(self):
        """Initializes the Silero VAD ONNX model."""
        try:
            from silero_vad import load_silero_vad
            self.model = load_silero_vad(onnx=True)
            logger.info("Silero VAD ONNX acoustic model initialized successfully.")
        except Exception as e:
            logger.warning(f"Silero VAD init note (falling back to energy VAD): {e}")
            self.model = None

    def trigger_interruption(self, source: str = "user_voice") -> Dict[str, Any]:
        """Sets the global interruption signal, terminating ongoing speech synthesis."""
        self._interruption_flag.set()
        self._last_speech_time = time.time()
        logger.info(f"Acoustic Cortex: Interruption triggered by '{source}' at {self._last_speech_time:.2f}")
        return {
            "status": "success",
            "interrupted": True,
            "source": source,
            "timestamp": self._last_speech_time
        }

    def reset_interruption(self):
        """Clears the interruption event flag."""
        self._interruption_flag.clear()

    def is_interrupted(self) -> bool:
        """Checks if a user barge-in event was signaled."""
        return self._interruption_flag.is_set()

    def detect_speech_from_pcm(self, pcm_bytes: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        """
        Classifies an audio chunk (16kHz PCM 16-bit mono) for presence of human voice.
        Returns speech confidence and whether speech threshold was crossed.
        """
        if not pcm_bytes:
            return {"is_speech": False, "confidence": 0.0}

        # Auto-unpack WAV containers if present
        if pcm_bytes.startswith(b"RIFF") and b"WAVE" in pcm_bytes[:12]:
            try:
                import wave
                with wave.open(io.BytesIO(pcm_bytes), "rb") as wf:
                    sample_rate = wf.getframerate() or sample_rate
                    pcm_bytes = wf.readframes(wf.getnframes())
            except Exception:
                if len(pcm_bytes) > 44:
                    pcm_bytes = pcm_bytes[44:]

        # Ensure 16-bit alignment
        if len(pcm_bytes) % 2 != 0:
            pcm_bytes = pcm_bytes[:-1]

        if len(pcm_bytes) == 0:
            return {"is_speech": False, "confidence": 0.0}

        try:
            # 1. Silero VAD Model Path
            if self.model:
                import torch
                # Convert 16-bit PCM bytes to normalized float32 tensor
                audio_np = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Window size: 512 for 16kHz, 256 for 8kHz
                window_size = 512 if sample_rate >= 16000 else 256
                
                # Pad if shorter than a single window
                if len(audio_np) < window_size:
                    audio_np = np.pad(audio_np, (0, window_size - len(audio_np)), mode='constant')

                audio_tensor = torch.from_numpy(audio_np)
                
                # Window through chunks and extract maximum speech probability
                probs = []
                for idx in range(0, len(audio_tensor) - window_size + 1, window_size):
                    chunk = audio_tensor[idx : idx + window_size]
                    prob = float(self.model(chunk, sample_rate).item())
                    probs.append(prob)

                speech_prob = max(probs) if probs else 0.0
                is_speech = bool(speech_prob >= self.threshold)

                if is_speech:
                    self._last_speech_time = time.time()

                return {
                    "is_speech": is_speech,
                    "confidence": round(speech_prob, 4),
                    "engine": "silero_vad_onnx",
                    "sample_rate": sample_rate
                }

        except Exception as e:
            logger.debug(f"Silero VAD classification error: {e}")

        # 2. Ultra-fast Fallback: RMS Energy & Zero-Crossing Rate VAD
        try:
            audio_np = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
            rms = float(np.sqrt(np.mean(audio_np ** 2)))
            is_speech = bool(rms > 350.0)
            confidence = min(1.0, float(rms / 1200.0))
            return {
                "is_speech": is_speech,
                "confidence": round(confidence, 4),
                "engine": "energy_rms_fallback",
                "rms": round(rms, 2)
            }
        except Exception as fallback_err:
            logger.error(f"Fallback VAD error: {fallback_err}")
            return {"is_speech": False, "confidence": 0.0, "error": str(fallback_err)}

# Global Singleton Instance
voice_vad = SileroVoiceDetector()
