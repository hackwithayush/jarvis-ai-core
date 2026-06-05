from moviepy import ImageClip, AudioFileClip
import os
import uuid
import config

def create_video(image_path, audio_path):
    """
    Neural Video Pipeline: Merging visual and vocal assets.
    """
    try:
        print(f"Merging visual {image_path} with vocal {audio_path}...")
        
        # 1. Load visual asset
        clip = ImageClip(image_path).set_duration(5) # Default 5s
        
        # 2. Synchronize vocal asset
        audio = AudioFileClip(audio_path)
        
        # 3. Compile and Render
        video = clip.set_audio(audio)
        
        filename = f"video_{uuid.uuid4().hex}.mp4"
        output_path = os.path.join(config.VIDEO_GEN_DIR, filename)
        
        video.write_videofile(output_path, fps=24, codec="libx264")

        return {
            "status": "success",
            "filename": filename,
            "path": output_path,
            "url": f"/api/assets/videos/{filename}"
        }
    except Exception as e:
        print(f"Neural Video Failure: {e}")
        return {"status": "error", "message": str(e)}

def get_simulated_video(prompt: str):
    """
    Simulation Node: Providing instant visual feedback for the Executive HUD.
    Returns a professional-grade sample asset for demonstration purposes.
    """
    # Using a high-quality SpaceX launch sample as the platform default simulation
    return {
        "status": "success",
        "type": "video",
        "url": "https://samplelib.com/lib/preview/mp4/sample-5s.mp4",
        "info": "Neural platform simulation layer active."
    }
