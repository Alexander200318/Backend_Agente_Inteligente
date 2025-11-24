# config/redis_config.py
import redis
from typing import Optional
import os

class RedisConfig:
    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = 0,
        password: Optional[str] = None
    ):
        # Leer desde variables de entorno o usar defaults
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port or int(os.getenv("REDIS_PORT", "6379"))
        self.db = db
        self.password = password or os.getenv("REDIS_PASSWORD", None)
        
        self._client = None
    
    @property
    def client(self) -> redis.Redis:
        """Obtiene o crea la conexión a Redis"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,  # Retorna strings en lugar de bytes
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Verificar conexión
            try:
                self._client.ping()
                print(f"✅ Redis conectado en {self.host}:{self.port}")
            except redis.ConnectionError as e:
                print(f"❌ Error conectando a Redis: {e}")
                raise
        
        return self._client
    
    def close(self):
        """Cierra la conexión"""
        if self._client:
            self._client.close()
            self._client = None

# Singleton global
_redis_instance = None

def get_redis_client() -> redis.Redis:
    """Obtiene la instancia global de Redis"""
    global _redis_instance
    if _redis_instance is None:
        config = RedisConfig()
        _redis_instance = config.client
    return _redis_instance