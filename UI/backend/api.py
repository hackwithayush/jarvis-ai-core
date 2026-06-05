"""
JARVIS UI Backend (FastAPI + WebSockets)
Bridges the Python ALWAYS_ON_RUNTIME logic with the React/Electron Frontend.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import sys
import pathlib
import json

# Bind to internal JARVIS core
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.absolute()))
from ALWAYS_ON_RUNTIME.active_task_queue import TaskState

app = FastAPI(title="JARVIS AI UI Engine")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                pass

manager = ConnectionManager()
current_state = TaskState.IDLE.value

import asyncio
import random

async def notification_emitter():
    while True:
        await asyncio.sleep(random.randint(15, 30))
        messages = [
            {"message": "VRAM optimized. Unloaded qwen2.5-coder.", "type": "info"},
            {"message": "Incoming Telegram Message from Admin.", "type": "warning"},
            {"message": "Web search agent completed data retrieval.", "type": "success"},
            {"message": "High CPU load detected on main thread.", "type": "error"}
        ]
        note = random.choice(messages)
        await manager.broadcast({
            "type": "notification",
            "message": note["message"],
            "notification_type": note["type"]
        })

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(notification_emitter())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global current_state
    await manager.connect(websocket)
    try:
        # Send initial sync state to the glowing orb frontend
        await websocket.send_text(json.dumps({"type": "state_change", "state": current_state}))
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            # Allow frontend commands (like manual abort)
            if payload.get("type") == "set_state":
                current_state = payload.get("state")
                await manager.broadcast({"type": "state_change", "state": current_state})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/status")
async def get_status():
    import psutil
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": psutil.virtual_memory().percent,
        "state": current_state
    }

class StateUpdate(BaseModel):
    state: str

@app.post("/api/set_state")
async def update_state(update: StateUpdate):
    global current_state
    current_state = update.state
    await manager.broadcast({"type": "state_change", "state": current_state})
    return {"status": "synced"}

if __name__ == "__main__":
    import uvicorn
    print("[UI BACKEND] Starting FastAPI WebSocket Server on port 8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
