from vosk import Model, KaldiRecognizer
import sounddevice as sd
import queue
import json

q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

print("Loading Vosk Model...")
try:
    model = Model(lang="en-us")
except Exception as e:
    print(f"Failed to load Vosk model: {e}")
    exit(1)

rec = KaldiRecognizer(model, 16000)

print("Starting audio stream...")
try:
    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype='int16',
        channels=1,
        callback=callback
    ):
        print("\n===============================")
        print("Listening... Say something!")
        print("===============================\n")
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                print(f"[HEARD]: {result.get('text', '')}")
            else:
                # Partial results
                partial = json.loads(rec.PartialResult())
                if partial.get("partial", "") != "":
                    print(f"[Partial]: {partial.get('partial', '')}", end='\r')
except Exception as e:
    print(f"Audio stream error: {e}")
