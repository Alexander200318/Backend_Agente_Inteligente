import threading
import time
from ollama.ollama_agent_service import OllamaAgentService

def cleanup_sessions_periodically(interval_minutes: int = 10):
    """Limpia sesiones expiradas cada X minutos"""
    while True:
        time.sleep(interval_minutes * 60)
        expired = OllamaAgentService._session_manager.cleanup_expired()
        if expired > 0:
            print(f"🧹 Limpiadas {expired} sesiones expiradas")