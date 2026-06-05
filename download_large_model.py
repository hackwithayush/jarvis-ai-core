import requests
from tqdm import tqdm
import zipfile
import os
import sys

URL = "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"
ZIP_FILE = "VOICE/vosk-model-en-us-0.22.zip"
EXTRACT_DIR = "VOICE"
MODEL_DIR = "VOICE/vosk-model-en-us-0.22"

def download_model():
    if not os.path.exists("VOICE"):
        os.makedirs("VOICE")
        
    if os.path.exists(MODEL_DIR):
        print(f"[OK] High-Accuracy Model already exists at {MODEL_DIR}")
        return

    print(f"Downloading 1.8GB Vosk Model: vosk-model-en-us-0.22...")
    print("This may take 5-10 minutes depending on your internet speed.")
    
    response = requests.get(URL, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(ZIP_FILE, 'wb') as file, tqdm(
        desc=ZIP_FILE,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)
            
    print("\nExtracting massive model...")
    with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
        zip_ref.extractall(EXTRACT_DIR)
        
    print("Cleaning up zip file...")
    os.remove(ZIP_FILE)
    print("✅ High-Accuracy Model Installation Complete!")

if __name__ == "__main__":
    download_model()
