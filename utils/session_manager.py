from datetime import datetime, timedelta
from typing import Dict

class SessionManager:
    def __init__(self, ttl_minutes: int = 30):
        self.sessions: Dict[str, datetime] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def touch(self, session_id: str):
        """Actualiza última actividad de sesión"""
        self.sessions[session_id] = datetime.now()
    
    def cleanup_expired(self):
        """Limpia sesiones expiradas"""
        now = datetime.now()
        expired = [sid for sid, last_active in self.sessions.items() 
                   if now - last_active > self.ttl]
        for sid in expired:
            del self.sessions[sid]
        return len(expired)
    
    def is_active(self, session_id: str) -> bool:
        """Verifica si sesión está activa"""
        if session_id not in self.sessions:
            return False
        return (datetime.now() - self.sessions[session_id]) <= self.ttl