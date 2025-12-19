# services/websocket_manager.py (ARCHIVO NUEVO)
from fastapi import WebSocket
from typing import Dict, List
import logging
import json

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gestiona conexiones WebSocket para chat en tiempo real
    """
    
    def __init__(self):
        # session_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Acepta conexión y la registra"""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        
        self.active_connections[session_id].append(websocket)
        logger.info(f"✅ WebSocket conectado: session={session_id}, total={len(self.active_connections[session_id])}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Desconecta y elimina de la lista"""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
                logger.info(f"🔌 WebSocket desconectado: session={session_id}")
            
            # Limpiar si no hay conexiones
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Envía mensaje a una conexión específica"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error enviando mensaje personal: {e}")
    
    async def broadcast(self, message: dict, session_id: str):
        """
        Envía mensaje a TODAS las conexiones de una sesión
        (widget + humano)
        """
        if session_id not in self.active_connections:
            logger.warning(f"No hay conexiones para session {session_id}")
            return
        
        disconnected = []
        
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
                disconnected.append(connection)
        
        # Limpiar conexiones muertas
        for conn in disconnected:
            self.disconnect(conn, session_id)
        
        logger.info(f"📢 Broadcast a {len(self.active_connections[session_id])} conexiones de session {session_id}")
    
    def get_connection_count(self, session_id: str) -> int:
        """Cuenta conexiones activas para una sesión"""
        return len(self.active_connections.get(session_id, []))


# Instancia global
manager = ConnectionManager()
