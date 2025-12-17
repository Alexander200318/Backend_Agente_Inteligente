# database/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from typing import Optional
import logging
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

class MongoDBManager:
    """
    Gestor de conexión a MongoDB con soporte async (Motor) y sync (PyMongo)
    """
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    sync_client: Optional[MongoClient] = None
    
    # Configuración desde variables de entorno
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME: str = os.getenv("MONGO_DB_NAME", "chatbot_institucional")
    
    @classmethod
    def connect(cls):
        """Conectar a MongoDB (async)"""
        try:
            cls.client = AsyncIOMotorClient(cls.MONGO_URI)
            cls.db = cls.client[cls.DB_NAME]
            logger.info(f"✅ Conectado a MongoDB: {cls.DB_NAME}")
        except Exception as e:
            logger.error(f"❌ Error conectando a MongoDB: {e}")
            raise
    
    @classmethod
    def connect_sync(cls):
        """Conectar a MongoDB (sync) - para casos especiales"""
        try:
            cls.sync_client = MongoClient(cls.MONGO_URI)
            logger.info(f"✅ Conectado a MongoDB (sync): {cls.DB_NAME}")
        except Exception as e:
            logger.error(f"❌ Error conectando a MongoDB sync: {e}")
            raise
    
    @classmethod
    def close(cls):
        """Cerrar conexión"""
        if cls.client:
            cls.client.close()
            logger.info("🔌 Conexión MongoDB cerrada")
        if cls.sync_client:
            cls.sync_client.close()
            logger.info("🔌 Conexión MongoDB sync cerrada")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Obtener instancia de la base de datos"""
        if cls.db is None:
            cls.connect()
        return cls.db
    
    @classmethod
    def get_collection(cls, collection_name: str):
        """Obtener una colección específica"""
        db = cls.get_database()
        return db[collection_name]


# Instancia global
mongodb = MongoDBManager()


# Dependency para FastAPI
async def get_mongodb():
    """
    Dependency para usar en endpoints de FastAPI
    
    Usage:
        @router.get("/...")
        async def endpoint(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
            ...
    """
    return mongodb.get_database()


# Funciones helper para colecciones específicas
async def get_conversations_collection():
    """Obtener colección de conversaciones"""
    return mongodb.get_collection("conversations")


async def get_messages_collection():
    """Obtener colección de mensajes (si decides separarlos)"""
    return mongodb.get_collection("messages")


# Función de inicialización para main.py
async def init_mongodb():
    """
    Inicializar MongoDB al arrancar la aplicación
    
    Usage en main.py:
        @app.on_event("startup")
        async def startup_event():
            await init_mongodb()
    """
    try:
        mongodb.connect()
        
        # Verificar conexión
        await mongodb.db.command("ping")
        logger.info("🏓 MongoDB ping exitoso")
        
        # Crear índices importantes
        conversations = await get_conversations_collection()
        
        # Índice por session_id (único)
        await conversations.create_index("session_id", unique=True)
        
        # Índice por id_agente (para búsquedas rápidas)
        await conversations.create_index("id_agente")
        
        # Índice por estado
        await conversations.create_index("metadata.estado")
        
        # Índice por fecha de creación (para ordenar)
        await conversations.create_index("created_at", background=True)
        
        # Índice compuesto para búsquedas frecuentes
        await conversations.create_index([
            ("id_agente", 1),
            ("metadata.estado", 1),
            ("created_at", -1)
        ])
        
        logger.info("✅ Índices de MongoDB creados correctamente")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error inicializando MongoDB: {e}")
        raise


# Función de cierre para main.py
async def close_mongodb():
    """
    Cerrar conexión MongoDB al detener la aplicación
    
    Usage en main.py:
        @app.on_event("shutdown")
        async def shutdown_event():
            await close_mongodb()
    """
    mongodb.close()
    logger.info("👋 MongoDB desconectado")
