import logging
from datetime import datetime, timezone
from models import db, Mission, User

logger = logging.getLogger(__name__)

class TaskEngine:
    """Manages 'Missions' (tasks) for the Stark Executive Suite."""
    
    def __init__(self, user_id=1):
        self.user_id = user_id

    def add_mission(self, title, description="", priority=1, deadline=None):
        """Add a new mission to the executive agenda."""
        try:
            mission = Mission(
                user_id=self.user_id,
                title=title,
                description=description,
                priority=priority,
                deadline=deadline
            )
            db.session.add(mission)
            db.session.commit()
            logger.info(f"Mission Synchronized: {title}")
            return {"status": "success", "id": mission.id}
        except Exception as e:
            logger.error(f"Mission Sync Failure: {e}")
            return {"status": "error", "message": str(e)}

    def list_active_missions(self):
        """Retrieve all pending or active missions."""
        try:
            missions = Mission.query.filter(
                Mission.user_id == self.user_id,
                Mission.status != 'completed'
            ).order_by(Mission.priority.desc()).all()
            
            return [
                {
                    "id": m.id,
                    "title": m.title,
                    "status": m.status,
                    "priority": m.priority,
                    "deadline": m.deadline.isoformat() if m.deadline else None
                }
                for m in missions
            ]
        except Exception as e:
            logger.error(f"Failed to fetch missions: {e}")
            return []

    def complete_mission(self, mission_id):
        """Mark a mission as completed."""
        try:
            mission = Mission.query.get(mission_id)
            if mission:
                mission.status = 'completed'
                db.session.commit()
                return {"status": "success"}
            return {"status": "error", "message": "Mission not found."}
        except Exception as e:
            logger.error(f"Failed to complete mission: {e}")
            return {"status": "error", "message": str(e)}
