import time
import queue
import json
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer

print("====================================================")
print("         JARVIS AUDIO DIAGNOSTICS SUITE             ")
print("====================================================\n")

print("[1] QUERYING DEVICES...")
print(sd.query_devices())
print("\n[DEFAULT DEVICE INDEX]:", sd.default.device)
print("\n====================================================\n")

print("[2] TESTING RAW AUDIO VOLUME (SPEAK NOW)")
print("If the numbers don't move from ~0.0, your mic is muted or you selected the wrong one!\n")

def volume_callback(indata, frames, time, status):
    volume = np.linalg.norm(indata) * 10
    print(f"Volume Level: {volume:.2f}", end='\r')

try:
    with sd.InputStream(callback=volume_callback, channels=1, samplerate=16000):
        time.sleep(5)
except Exception as e:
    print(f"\n[ERROR] Volume test failed: {e}")

print("\n\n====================================================\n")

print("[3] TESTING VOSK ENGINE DIRECTLY (SAY 'JARVIS')")
print("Loading model...")

q = queue.Queue()
try:
    model = Model(lang="en-us")
except Exception as e:
    print(f"[ERROR] Failed to load Vosk model: {e}")
    exit(1)

rec = KaldiRecognizer(model, 16000)

def vosk_callback(indata, frames, time, status):
    q.put(bytes(indata))

try:
    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype='int16',
        channels=1,
        callback=vosk_callback
    ):
        print("Listening... (Press Ctrl+C to stop)")
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                if res.get("text"):
                    print(f"\n[FULL MATCH]: {res['text']}")
            else:
                partial = json.loads(rec.PartialResult())
                if partial.get("partial"):
                    print(f"Partial: {partial['partial']}                  ", end='\r')
except KeyboardInterrupt:
    print("\nDiagnostics complete.")
except Exception as e:
    print(f"\n[ERROR] Vosk stream crashed: {e}")
