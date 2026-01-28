import threading
import time
from groq_service.groq_agent_service import GroqAgentService

def cleanup_sessions_periodically(interval_minutes: int = 10):
    """Limpia sesiones expiradas cada X minutos"""
    while True:
        time.sleep(interval_minutes * 60)
        expired = GroqAgentService._session_manager.cleanup_expired()
        if expired > 0:
            print(f"🧹 Limpiadas {expired} sesiones expiradas")