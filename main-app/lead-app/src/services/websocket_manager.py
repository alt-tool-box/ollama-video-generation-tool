import json
from typing import Dict, List
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self.active_connections:
            if websocket in self.active_connections[job_id]:
                self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
    
    async def send_progress(self, job_id: str, data: dict):
        if job_id in self.active_connections:
            message = json.dumps(data)
            dead_connections = []
            
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_text(message)
                except:
                    dead_connections.append(connection)
            
            for conn in dead_connections:
                self.disconnect(conn, job_id)
    
    async def broadcast_status(self, job_id: str, status: str, step: str = None,
                               progress: int = None, message: str = None, error: str = None):
        data = {
            "type": "progress",
            "job_id": job_id,
            "status": status
        }
        if step:
            data["step"] = step
        if progress is not None:
            data["progress"] = progress
        if message:
            data["message"] = message
        if error:
            data["error"] = error
        
        await self.send_progress(job_id, data)


ws_manager = WebSocketManager()
