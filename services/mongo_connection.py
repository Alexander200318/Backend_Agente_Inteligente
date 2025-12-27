# services/mongo_connection.py
"""
Helper para obtener conexión a MongoDB y operaciones comunes
"""
from database.mongodb import mongodb
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from models.conversation_mongo import ConversationMongo, MessageCreate, ConversationUpdate
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_mongo_db() -> AsyncIOMotorDatabase:
    """
    Obtener instancia de la base de datos MongoDB (async)
    
    Returns:
        AsyncIOMotorDatabase: Instancia de la base de datos
    """
    return mongodb.get_database()


def get_conversations_collection() -> AsyncIOMotorCollection:
    """
    Obtener colección de conversaciones
    
    Returns:
        AsyncIOMotorCollection: Colección conversations
    """
    db = get_mongo_db()
    return db["conversations"]





async def get_conversation_by_session(session_id: str) -> Optional[ConversationMongo]:
    """
    Obtener una conversación por session_id
    
    Args:
        session_id: ID de la sesión
        
    Returns:
        ConversationMongo o None si no existe
    """
    try:
        collection = get_conversations_collection()
        doc = await collection.find_one({"session_id": session_id})
        
        if doc:
            # Convertir ObjectId a string para Pydantic
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            return ConversationMongo(**doc)
        return None
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo conversación {session_id}: {e}")
        return None


async def get_conversations_by_user(
    user_id: int,
    solo_activas: bool = True,
    limit: int = 20
) -> List[ConversationMongo]:
    """
    Obtener conversaciones asignadas a un usuario
    """
    try:
        collection = get_conversations_collection()
        
        # 🔍 DEBUG: Ver qué colección estamos usando
        logger.info(f"=" * 80)
        logger.info(f"🔍 DEBUG get_conversations_by_user")
        logger.info(f"🔍 user_id: {user_id} (tipo: {type(user_id)})")
        logger.info(f"🔍 solo_activas: {solo_activas}")
        logger.info(f"🔍 collection name: {collection.name}")
        
        # Construir filtro
        mongo_filter = {
            "metadata.escalado_a_usuario_id": user_id
        }
        
        if solo_activas:
            mongo_filter["metadata.estado"] = {"$ne": "finalizada"}
        
        logger.info(f"🔍 Filtro MongoDB: {mongo_filter}")
        
        # 🔥 PRIMERO: Contar cuántos documentos coinciden SIN filtro
        total_en_coleccion = await collection.count_documents({})
        logger.info(f"📊 Total documentos en colección: {total_en_coleccion}")
        
        # 🔥 SEGUNDO: Contar con filtro solo por user_id
        count_por_usuario = await collection.count_documents({
            "metadata.escalado_a_usuario_id": user_id
        })
        logger.info(f"📊 Documentos con escalado_a_usuario_id={user_id}: {count_por_usuario}")
        
        # 🔥 TERCERO: Ver todos los valores únicos de escalado_a_usuario_id
        pipeline = [
            {"$group": {"_id": "$metadata.escalado_a_usuario_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        unique_users = await collection.aggregate(pipeline).to_list(length=50)
        logger.info(f"📊 Usuarios únicos con conversaciones: {unique_users}")
        
        # 🔥 CUARTO: Buscar UN documento de ejemplo
        ejemplo = await collection.find_one({})
        if ejemplo:
            logger.info(f"📋 Documento ejemplo (estructura): {ejemplo.get('session_id')}")
            logger.info(f"📋 metadata.escalado_a_usuario_id del ejemplo: {ejemplo.get('metadata', {}).get('escalado_a_usuario_id')}")
            logger.info(f"📋 Tipo del campo: {type(ejemplo.get('metadata', {}).get('escalado_a_usuario_id'))}")
        
        # Buscar y convertir a lista
        cursor = collection.find(mongo_filter).sort("updated_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        
        logger.info(f"🔍 Documentos encontrados con filtro completo: {len(docs)}")
        
        # Convertir a modelos Pydantic
        conversations = []
        for doc in docs:
            try:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                conversations.append(ConversationMongo(**doc))
            except Exception as e:
                logger.warning(f"⚠️ Error parseando conversación {doc.get('session_id')}: {e}")
                import traceback
                logger.warning(traceback.format_exc())
        
        logger.info(f"✅ Conversaciones parseadas: {len(conversations)}")
        logger.info(f"=" * 80)
        
        return conversations
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo conversaciones del usuario {user_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []




async def add_message_to_conversation(
    session_id: str,
    message: MessageCreate
) -> bool:
    """
    Agregar un mensaje a una conversación
    
    Args:
        session_id: ID de la sesión
        message: Datos del mensaje
        
    Returns:
        bool: True si se agregó correctamente
    """
    try:
        collection = get_conversations_collection()
        
        # Crear mensaje con timestamp
        message_dict = message.dict()
        message_dict["timestamp"] = datetime.utcnow()
        
        # Actualizar conversación
        result = await collection.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": message_dict},
                "$set": {"updated_at": datetime.utcnow()},
                "$inc": {
                    "metadata.total_mensajes": 1,
                    f"metadata.total_mensajes_{message.role.value}": 1
                }
            }
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"❌ Error agregando mensaje a {session_id}: {e}")
        return False


async def update_conversation_metadata(
    session_id: str,
    update_data: ConversationUpdate
) -> bool:
    """
    Actualizar metadata de una conversación
    
    Args:
        session_id: ID de la sesión
        update_data: Datos a actualizar
        
    Returns:
        bool: True si se actualizó correctamente
    """
    try:
        collection = get_conversations_collection()
        
        # Construir update dict
        update_dict = {}
        for field, value in update_data.dict(exclude_unset=True).items():
            update_dict[f"metadata.{field}"] = value
        
        update_dict["updated_at"] = datetime.utcnow()
        
        # Actualizar
        result = await collection.update_one(
            {"session_id": session_id},
            {"$set": update_dict}
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"❌ Error actualizando conversación {session_id}: {e}")
        return False