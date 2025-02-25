import asyncio
import json
from typing import Any, Dict, List

from fastapi import WebSocket

from app.core.logging_config import get_logger

logger = get_logger("websocket_manager")


class WebSocketManager:
    def __init__(self):
        # Change the structure to include user_id
        self.active_connections: Dict[str, Dict[int, List[WebSocket]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, file_id: str, user_id: int):
        """Connect a websocket client"""
        async with self._lock:
            if file_id not in self.active_connections:
                self.active_connections[file_id] = {}
            if user_id not in self.active_connections[file_id]:
                self.active_connections[file_id][user_id] = []
            self.active_connections[file_id][user_id].append(websocket)
            logger.info(f"WebSocket client connected for file_id: {
                        file_id}, user_id: {user_id}")

    async def disconnect(self, websocket: WebSocket, file_id: str, user_id: int):
        """Disconnect a websocket client"""
        async with self._lock:
            if file_id in self.active_connections and user_id in self.active_connections[file_id]:
                try:
                    self.active_connections[file_id][user_id].remove(websocket)
                    if not self.active_connections[file_id][user_id]:
                        del self.active_connections[file_id][user_id]
                    if not self.active_connections[file_id]:
                        del self.active_connections[file_id]
                except ValueError:
                    pass
            logger.info(f"WebSocket client disconnected for file_id: {
                        file_id}, user_id: {user_id}")

    async def send_progress(self, file_id: str, user_id: int, data: dict):
        """Send progress update to all connected clients for a specific file and user"""
        if (file_id not in self.active_connections or
                user_id not in self.active_connections[file_id]):
            return

        message = json.dumps(data)
        disconnected = []

        for websocket in self.active_connections[file_id][user_id]:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending progress update: {str(e)}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket, file_id, user_id)
