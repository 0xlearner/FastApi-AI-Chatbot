from fastapi import WebSocket
from typing import Dict, List
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, file_id: str):
        logger.info(f"[{datetime.utcnow()}] Accepting WebSocket connection for file_id: {file_id}")
        await websocket.accept()
        if file_id not in self.active_connections:
            self.active_connections[file_id] = []
        self.active_connections[file_id].append(websocket)
        logger.info(f"[{datetime.utcnow()}] Active connections for file_id {file_id}: {len(self.active_connections[file_id])}")

    async def disconnect(self, websocket: WebSocket, file_id: str):
        if file_id in self.active_connections:
            self.active_connections[file_id].remove(websocket)
            if not self.active_connections[file_id]:
                del self.active_connections[file_id]
            logger.info(f"[{datetime.utcnow()}] Disconnected WebSocket for file_id: {file_id}")
        else:
            logger.warning(f"[{datetime.utcnow()}] Attempted to disconnect non-existent connection for file_id: {file_id}")

    async def send_progress(self, file_id: str, data: dict):
        if file_id in self.active_connections:
            logger.info(f"[{datetime.utcnow()}] Sending progress update for file_id {file_id}: {json.dumps(data)}")
            failed_connections = []
            for connection in self.active_connections[file_id]:
                try:
                    await connection.send_json(data)
                except Exception as e:
                    logger.error(f"Error sending progress update to connection: {str(e)}")
                    failed_connections.append(connection)
            
            # Remove failed connections
            for failed in failed_connections:
                self.active_connections[file_id].remove(failed)
            
            if failed_connections:
                logger.warning(f"Removed {len(failed_connections)} failed connections for file_id {file_id}")
        else:
            logger.warning(f"[{datetime.utcnow()}] No active connections found for file_id: {file_id}")