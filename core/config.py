import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import secrets

# Cargar variables de entorno
load_dotenv()

class Settings(BaseSettings):
    """Configuración centralizada de la aplicación"""
    
    # ============================================
    #   APLICACIÓN
    # ============================================
    APP_NAME: str = "CallCenterAI - Chatbot Institucional"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = True
    
    # ============================================
    #   BASE DE DATOS MYSQL
    # ============================================
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "chatbot_institucional"
    
    @property
    def DATABASE_URL(self) -> str:
        """Genera la URL de conexión a MySQL"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
    
    # ============================================
    #   JWT Y SEGURIDAD
    # ============================================
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(64))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ============================================
    #   SEGURIDAD DE LOGIN
    # ============================================
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    
    # ============================================
    #   POLÍTICA DE CONTRASEÑAS
    # ============================================
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL_CHAR: bool = True
    
    # ============================================
    #   RATE LIMITING
    # ============================================
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    
    # ============================================
    #   CORS
    # ============================================
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development, staging, production
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Configuración de CORS según el ambiente"""
        if self.ENVIRONMENT == "production":
            # 🔒 Producción: Solo dominios específicos (HTTPS)
            return [
                "https://app.tudominio.com",
                "https://portal.tudominio.com",
            ]
        elif self.ENVIRONMENT == "staging":
            # 🟡 Staging: Múltiples dominios HTTP y HTTPS
            return [
                "https://staging-app.tudominio.com",
                "http://staging-app.tudominio.com",
                "https://staging.tudominio.com",
                "http://staging.tudominio.com",
            ]
        else:
            # 🟢 Desarrollo: Todos los localhost
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8000",
                "http://localhost:8081",
                "http://127.0.0.1:8081",
                "http://192.168.5.5:8081",  # IP local de desarrollo
            ]
    
    # ============================================
    #   OLLAMA (IA LOCAL)
    # ============================================
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_BASE: str = "llama3"
    OLLAMA_MODEL: str = "llama3:8b" 
    
    @property
    def OLLAMA_URL(self) -> str:
        """Alias para compatibilidad"""
        return self.OLLAMA_BASE_URL
    
    # ============================================
    #   REDIS (CACHE)
    # ============================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    @property
    def REDIS_URL(self) -> str:
        """Genera la URL de conexión a Redis"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ============================================
    #   CHROMADB (VECTOR STORE)
    # ============================================
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "knowledge_base"
    
    # ============================================
    #   EMBEDDINGS
    # ============================================
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # ============================================
    #   CHATBOT
    # ============================================
    BOT_NAME: str = "TecAI"
    BOT_WELCOME_MESSAGE: str = "¡Hola! Soy el asistente virtual de TEC AZUAY. ¿En qué puedo ayudarte hoy?"
    DEFAULT_AGENT_ID: int = 1
    
    # ============================================
    #   LÍMITES Y TIMEOUTS
    # ============================================
    MAX_TOKENS: int = 2000
    TIMEOUT_SECONDS: int = 30
    
    # ============================================
    #   TEMPLATES Y ARCHIVOS ESTÁTICOS
    # ============================================
    TEMPLATES_DIR: str = "templates"
    STATIC_DIR: str = "static"
    
    class Config:
        """Configuración de Pydantic"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    # ============================================
    #   SERVICIO DE ASEGURAMIENTO / FENIX
    # ============================================
    ASEGURAMIENTO_BASE_URL: str = "http://apps.tecazuay.edu.ec:9093/aseguramiento/api/fenix"
# Instancia única de configuración


settings = Settings()


