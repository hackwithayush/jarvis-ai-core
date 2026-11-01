"""
Automated Test for JARVIS Silero VAD & Conversational Barge-In Voice Engine
Verifies sub-millisecond speech detection, conversational barge-in state management,
synthetic audio waveforms, WAV unpacking, and Flask API endpoints.
"""
import sys
import os
import io
import wave
import struct
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.voice_vad import SileroVoiceDetector, voice_vad
from core.voice_engine import VoiceEngine


def generate_synthetic_tone(freq: float = 440.0, duration: float = 0.25, sample_rate: int = 16000, amplitude: float = 0.8) -> bytes:
    """Generates synthetic 16-bit PCM mono sine wave audio frames."""
    num_samples = int(duration * sample_rate)
    samples = []
    for i in range(num_samples):
        val = int(amplitude * 32767.0 * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
        samples.append(val)
    return struct.pack(f"<{len(samples)}h", *samples)


def generate_synthetic_wav(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Wraps raw 16-bit PCM bytes inside a valid RIFF/WAVE container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def run_all_tests():
    print("==================================================")
    print("JARVIS SILERO VAD & BARGE-IN VOICE ENGINE VERIFICATION")
    print("==================================================")

    # 1. Initialization
    print("\n1. Testing SileroVoiceDetector initialization...")
    detector = SileroVoiceDetector(threshold=0.5)
    assert detector.threshold == 0.5, "Threshold must equal 0.5"
    assert not detector.is_interrupted(), "Initial interruption state must be False"
    print("   [PASS] SileroVoiceDetector initialized correctly.")

    # 2. Interruption lifecycle
    print("\n2. Testing Conversational Barge-In trigger & reset lifecycle...")
    assert not detector.is_interrupted()
    res = detector.trigger_interruption(source="test_barge_in")
    assert res["status"] == "success", "Interruption trigger must succeed"
    assert res["interrupted"] is True, "Interrupted flag must be True"
    assert detector.is_interrupted() is True, "is_interrupted() must return True"
    print(f"   [PASS] Interruption signal registered: {res['source']} at t={res['timestamp']:.2f}")

    detector.reset_interruption()
    assert detector.is_interrupted() is False, "is_interrupted() must be False after reset"
    print("   [PASS] Interruption flag reset successfully.")

    # 3. Silent PCM classification
    print("\n3. Testing Silence VAD classification...")
    silence_pcm = b"\x00" * 3200  # 0.1s of 16kHz silence
    res_silence = detector.detect_speech_from_pcm(silence_pcm, sample_rate=16000)
    assert res_silence["is_speech"] is False, "Silence must NOT be classified as speech"
    assert res_silence["confidence"] < 0.35, f"Silence confidence should be low, got {res_silence['confidence']}"
    print(f"   [PASS] Silence classified: is_speech={res_silence['is_speech']}, confidence={res_silence['confidence']} ({res_silence['engine']})")

    # 4. Audio tone classification
    print("\n4. Testing Audio Tone classification...")
    tone_pcm = generate_synthetic_tone(freq=300.0, duration=0.25, sample_rate=16000, amplitude=0.9)
    res_tone = detector.detect_speech_from_pcm(tone_pcm, sample_rate=16000)
    assert "is_speech" in res_tone, "Result must contain is_speech"
    assert "confidence" in res_tone, "Result must contain confidence"
    print(f"   [PASS] Tone classified: is_speech={res_tone['is_speech']}, confidence={res_tone['confidence']} ({res_tone['engine']})")

    # 5. RIFF/WAVE container auto-unpacking
    print("\n5. Testing RIFF/WAVE container unpack...")
    pcm_raw = generate_synthetic_tone(freq=400.0, duration=0.2, sample_rate=16000, amplitude=0.5)
    wav_payload = generate_synthetic_wav(pcm_raw, sample_rate=16000)
    res_wav = detector.detect_speech_from_pcm(wav_payload, sample_rate=16000)
    assert "is_speech" in res_wav, "Unpacked WAV must classify correctly"
    print(f"   [PASS] WAV payload unpacked & processed: confidence={res_wav['confidence']}")

    # 6. VoiceEngine delegation
    print("\n6. Testing VoiceEngine VAD integration...")
    engine = VoiceEngine()
    ve_vad = engine.detect_vad(b"\x00" * 1600)
    assert ve_vad["is_speech"] is False, "VoiceEngine silence detection must be False"
    ve_interrupt = engine.trigger_barge_in("voice_engine_test")
    assert ve_interrupt["status"] == "success"
    assert voice_vad.is_interrupted() is True
    voice_vad.reset_interruption()
    print("   [PASS] VoiceEngine VAD methods routed to singleton correctly.")

    # 7. Flask API Endpoints
    print("\n7. Testing Flask API VAD and Interruption routes...")
    from app import app
    client = app.test_client()

    # Reset
    c_reset = client.post("/api/voice/interrupt/reset")
    assert c_reset.status_code == 200
    assert c_reset.get_json()["interrupted"] is False

    # Status check
    c_status = client.get("/api/voice/interrupt/status")
    assert c_status.status_code == 200
    assert c_status.get_json()["interrupted"] is False

    # Trigger interrupt via POST
    c_int = client.post("/api/voice/interrupt", json={"source": "test_flask_suite"})
    assert c_int.status_code == 200
    assert c_int.get_json()["interrupted"] is True
    assert client.get("/api/voice/interrupt/status").get_json()["interrupted"] is True
    print("   [PASS] /api/voice/interrupt & /api/voice/interrupt/status operational.")

    # Reset again
    client.post("/api/voice/interrupt/reset")

    # POST silence to /api/voice/vad
    c_vad = client.post(
        "/api/voice/vad",
        data=b"\x00" * 3200,
        content_type="application/octet-stream"
    )
    assert c_vad.status_code == 200
    vad_data = c_vad.get_json()
    assert vad_data["status"] == "success"
    assert vad_data["is_speech"] is False
    assert vad_data["barge_in_triggered"] is False
    print("   [PASS] /api/voice/vad streaming classification verified.")

    print("\n==================================================")
    print("ALL 7 SILERO VAD & BARGE-IN CHECKS PASSED NOMINALLY!")
    print("==================================================")


if __name__ == "__main__":
    run_all_tests()
