import json
import logging
import os
import uuid
import asyncio
import threading
import edge_tts
import config
from core.image_engine import ImageGenerator
from core.video_engine import create_video
from core.model_manager import ModelManager

logger = logging.getLogger(__name__)

class MissionEngine:
    """
    Neural Orchestrator: Conversing logic into multimedia reality.
    Handles the full Script -> Voice -> Image -> Video pipeline.
    """
    
    def __init__(self, model_manager: ModelManager, db_session=None):
        self.model = model_manager
        self.image_gen = ImageGenerator()
        self.db_session = db_session

    def initiate_project(self, project_id: str, topic: str):
        """Phase 1: Intelligence Drafting (Script Generator)."""
        # Run script generation in background
        thread = threading.Thread(target=self._run_drafting_sync, args=(project_id, topic))
        thread.start()
        return project_id

    def create_mission(self, topic: str, user_id=None):
        """High-level entry point for creating missions (autonomous projects)."""
        project_id = f"msn_{uuid.uuid4().hex[:8]}"
        
        # We need to save the project record first
        from models import Project
        from app import db
        
        # If no user_id, use Admin (default creator)
        if not user_id:
            from models import User
            admin = User.query.filter_by(username='Admin').first()
            user_id = admin.id if admin else 1

        project = Project(id=project_id, user_id=user_id, topic=topic, status="initializing")
        db.session.add(project)
        db.session.commit()
        
        return self.initiate_project(project_id, topic)

    def finalize_project(self, project_id: str):
        """Phase 2: Neural Synthesis (Rendering)."""
        # Run rendering in background
        thread = threading.Thread(target=self._run_synthesis_sync, args=(project_id,))
        thread.start()
        return project_id

    def _run_drafting_sync(self, project_id, topic):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._execute_drafting(project_id, topic))
        except Exception as e:
            logger.error(f"Drafting failed for {project_id}: {e}")
            self._update_project_status(project_id, "failed", progress=0)
        finally:
            loop.close()

    def _run_synthesis_sync(self, project_id):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._execute_synthesis(project_id))
        except Exception as e:
            logger.error(f"Synthesis failed for {project_id}: {e}")
            self._update_project_status(project_id, "failed")
        finally:
            loop.close()

    async def _execute_drafting(self, project_id, topic):
        self._update_project_status(project_id, "drafting", 10)
        
        script = await self._generate_script(topic)
        if not script:
            raise Exception("Failed to generate mission script.")

        # Save script scenes to DB
        from models import Project, ProjectScene
        try:
            # We need a temporary session if not provided
            from app import db, app
            with app.app_context():
                project = Project.query.get(project_id)
            if project:
                project.title = script.get("title", topic)
                project.status = "draft"
                project.progress = 100 # Draft complete
                
                for i, scene in enumerate(script.get("scenes", [])):
                    ps = ProjectScene(
                        project_id=project_id,
                        index=i,
                        narration=scene["narration"],
                        visual_prompt=scene["visual_prompt"]
                    )
                    db.session.add(ps)
                db.session.commit()
                logger.info(f"Project {project_id} drafted successfully.")
        except Exception as e:
            logger.error(f"DB Error during drafting: {e}")
            raise e

    async def _execute_synthesis(self, project_id):
        self._update_project_status(project_id, "rendering", 5)
        
        from models import Project, ProjectScene
        from app import db, app
        
        with app.app_context():
            project = Project.query.get(project_id)
            if not project:
                raise Exception("Project not found.")
            
        scenes = sorted(project.scenes, key=lambda x: x.index)
        final_clips = []
        
        # Get user voice preferences
        user = project.author
        prefs = user.preferences or {}
        v_rate = prefs.get("voice_rate", "+0%")
        v_pitch = prefs.get("voice_pitch", "+0Hz")
        v_volume = prefs.get("voice_volume", "+0%")

        for i, scene in enumerate(scenes):
            self._update_project_status(project_id, "rendering", 10 + int((i/len(scenes)) * 80))
            
            # 2a. Voice Generation
            audio_filename = f"{project_id}_scene_{i}.mp3"
            audio_path = os.path.join(config.VOICE_DIR, audio_filename)
            communicate = edge_tts.Communicate(
                scene.narration, 
                config.TTS_VOICE,
                rate=v_rate,
                pitch=v_pitch,
                volume=v_volume
            )
            await communicate.save(audio_path)
            scene.audio_url = f"/api/assets/voices/{audio_filename}"
            
            # 2b. Image Generation
            img_result = self.image_gen.generate(scene.visual_prompt)
            if img_result["status"] == "success":
                scene.image_url = img_result["url"]
                image_path = img_result.get("path") or img_result.get("local_path")
                
                # 2c. Merge into Clip
                clip_result = create_video(image_path, audio_path)
                if clip_result["status"] == "success":
                    scene.clip_url = f"/api/assets/videos/{os.path.basename(clip_result['path'])}"
                    final_clips.append(clip_result["path"])
            
            db.session.commit()

        # 3. Final Assembly
        self._update_project_status(project_id, "assembling", 95)
        
        if len(final_clips) > 1:
            import importlib
            try:
                # Try moviepy v1.x structure
                mpy_editor = importlib.import_module("moviepy.editor")
                concatenate_videoclips = mpy_editor.concatenate_videoclips
                VideoFileClip = mpy_editor.VideoFileClip
            except ImportError:
                # Fallback to moviepy v2.x structure
                mpy_video = importlib.import_module("moviepy.video.VideoClip")
                mpy_io = importlib.import_module("moviepy.video.io.VideoFileClip")
                concatenate_videoclips = mpy_video.concatenate_videoclips
                VideoFileClip = mpy_io.VideoFileClip

            clips = [VideoFileClip(c) for c in final_clips]
            final_video = concatenate_videoclips(clips)
            final_filename = f"studio_{project_id}.mp4"
            final_path = os.path.join(config.VIDEO_GEN_DIR, final_filename)
            final_video.write_videofile(final_path, fps=24, codec="libx264")
            project.final_video_url = f"/api/assets/videos/{final_filename}"
        elif final_clips:
            project.final_video_url = f"/api/assets/videos/{os.path.basename(final_clips[0])}"
        
        project.status = "completed"
        project.progress = 100
        db.session.commit()

    def _update_project_status(self, project_id, status, progress=None):
        from models import Project
        from app import db, app
        try:
            with app.app_context():
                project = Project.query.get(project_id)
                if project:
                    project.status = status
                    if progress is not None:
                        project.progress = progress
                    db.session.commit()
        except:
            pass

    async def _generate_script(self, topic):
        prompt = f"""
        Act as a professional YouTube scriptwriter. Create a short 'Faceless Video' script about: {topic}.
        Return ONLY a JSON object in the following format:
        {{
            "title": "...",
            "scenes": [
                {{
                    "narration": "Text to be spoken by AI voiceover",
                    "visual_prompt": "Highly detailed image generation prompt for Stable Diffusion (Stark/Futuristic style)"
                }},
                ... (3-5 scenes)
            ]
        }}
        No intro, no outro, strictly JSON.
        """
        
        # Using coding model for better JSON adherence
        history = [{"role": "user", "content": prompt}]
        response_text = self.model.generate(history, model=config.ROUTING_CONFIG["coding"])
        
        try:
            # Clean possible markdown junk
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Script JSON Parse Failure: {e}")
            logger.debug(f"Raw response: {response_text}")
            return None

    def list_missions(self, user_id=None):
        """Retrieve all missions/projects for the HUD."""
        from models import Project
        if user_id:
            return Project.query.filter_by(user_id=user_id).order_by(Project.created_at.desc()).all()
        return Project.query.order_by(Project.created_at.desc()).all()
