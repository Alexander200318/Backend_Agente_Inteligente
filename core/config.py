from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # Aplicación
    APP_NAME: str = "CallCenterAI - Chatbot Institucional"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = True
    
    # Base de datos MySQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "chatbot_institucional"
    
    # JWT y Seguridad
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8081",      # ✅ Agrega este (Expo Web)
        "http://127.0.0.1:8081",      # ✅ Agrega este también
        "http://192.168.5.6:8081",    # ✅ Para dispositivos móviles en la misma red
    ]
    
    # Otros
    MAX_LOGIN_ATTEMPTS: int = 5
    PASSWORD_MIN_LENGTH: int = 8
    
    @property
    def DATABASE_URL(self) -> str:
        """Genera la URL de conexión a MySQL"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()