# services/conversation_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
import logging

from models.conversation_mongo import (
    ConversationMongo,
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    ConversationListResponse,
    ConversationStats,
    MessageCreate,
    Message,
    ConversationStatus,
    ConversationMetadata
)
from database.mongodb import get_conversations_collection

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Servicio para gestionar conversaciones en MongoDB
    """
    
    @staticmethod
    async def create_conversation(
        conversation_data: ConversationCreate
    ) -> ConversationResponse:
        """
        Crear una nueva conversación
        
        Args:
            conversation_data: Datos de la conversación a crear
            
        Returns:
            ConversationResponse con la conversación creada
        """
        try:
            collection = await get_conversations_collection()
            
            # Crear metadata inicial
            metadata = ConversationMetadata(
                estado=ConversationStatus.activa,
                ip_origen=conversation_data.ip_origen,
                user_agent=conversation_data.user_agent,
                dispositivo=conversation_data.dispositivo,
                navegador=conversation_data.navegador,
                total_mensajes=0,
                total_mensajes_usuario=0,
                total_mensajes_agente=0
            )
            
            # Construir documento de conversación
            conversation = ConversationMongo(
                session_id=conversation_data.session_id,
                id_agente=conversation_data.id_agente,
                agent_name=conversation_data.agent_name,
                agent_type=conversation_data.agent_type,
                id_visitante=conversation_data.id_visitante,
                origin=conversation_data.origin,
                messages=[],
                metadata=metadata,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Insertar en MongoDB
            result = await collection.insert_one(conversation.dict())
            
            logger.info(f"✅ Conversación creada: session_id={conversation_data.session_id}")
            
            # Retornar con el ID generado
            return ConversationResponse(
                id=str(result.inserted_id),
                **conversation.dict()
            )
            
        except Exception as e:
            logger.error(f"❌ Error creando conversación: {e}")
            raise
    
    @staticmethod
    async def get_conversation_by_session(
        session_id: str
    ) -> Optional[ConversationResponse]:
        """
        Obtener conversación por session_id
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            ConversationResponse o None si no existe
        """
        try:
            collection = await get_conversations_collection()
            
            conversation = await collection.find_one({"session_id": session_id})
            
            if not conversation:
                return None
            
            # Convertir ObjectId a string
            conversation["id"] = str(conversation.pop("_id"))
            
            return ConversationResponse(**conversation)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo conversación: {e}")
            raise
    
    @staticmethod
    async def add_message(
        session_id: str,
        message_data: MessageCreate
    ) -> ConversationResponse:
        """
        Agregar un mensaje a una conversación existente
        
        Args:
            session_id: ID de la sesión
            message_data: Datos del mensaje a agregar
            
        Returns:
            ConversationResponse actualizada
        """
        try:
            collection = await get_conversations_collection()
            
            # Crear mensaje
            message = Message(
                role=message_data.role,
                content=message_data.content,
                timestamp=datetime.utcnow(),
                sources_used=message_data.sources_used,
                model_used=message_data.model_used,
                token_count=message_data.token_count,
                user_id=message_data.user_id,
                user_name=message_data.user_name
            )
            
            # Actualizar contadores
            update_query = {
                "$push": {"messages": message.dict()},
                "$set": {"updated_at": datetime.utcnow()},
                "$inc": {
                    "metadata.total_mensajes": 1
                }
            }
            
            # Incrementar contador según el rol
            # El role ya es string gracias a use_enum_values en Pydantic
            role_str = message_data.role if isinstance(message_data.role, str) else message_data.role.value
            if role_str == "user":
                update_query["$inc"]["metadata.total_mensajes_usuario"] = 1
            elif role_str in ["assistant", "human_agent"]:
                update_query["$inc"]["metadata.total_mensajes_agente"] = 1
            
            # Actualizar en MongoDB
            result = await collection.find_one_and_update(
                {"session_id": session_id},
                update_query,
                return_document=True  # Retornar documento actualizado
            )
            
            if not result:
                raise ValueError(f"Conversación no encontrada: {session_id}")
            
            logger.info(f"✅ Mensaje agregado a conversación: {session_id}")
            
            # Convertir y retornar
            result["id"] = str(result.pop("_id"))
            return ConversationResponse(**result)
            
        except Exception as e:
            logger.error(f"❌ Error agregando mensaje: {e}")
            raise
    
    @staticmethod
    async def update_conversation_status(
        session_id: str,
        update_data: ConversationUpdate
    ) -> ConversationResponse:
        """
        Actualizar estado y metadata de una conversación
        
        Args:
            session_id: ID de la sesión
            update_data: Datos a actualizar
            
        Returns:
            ConversationResponse actualizada
        """
        try:
            collection = await get_conversations_collection()
            
            # Construir update query
            update_query = {"$set": {"updated_at": datetime.utcnow()}}
            
            if update_data.estado is not None:
                # El estado ya es string gracias a use_enum_values
                estado_str = update_data.estado if isinstance(update_data.estado, str) else update_data.estado.value
                update_query["$set"]["metadata.estado"] = estado_str
            
            if update_data.requirio_atencion_humana is not None:
                update_query["$set"]["metadata.requirio_atencion_humana"] = update_data.requirio_atencion_humana
            
            if update_data.escalado_a_usuario_id is not None:
                update_query["$set"]["metadata.escalado_a_usuario_id"] = update_data.escalado_a_usuario_id
                update_query["$set"]["metadata.fecha_escalamiento"] = datetime.utcnow()
            
            if update_data.escalado_a_usuario_nombre is not None:
                update_query["$set"]["metadata.escalado_a_usuario_nombre"] = update_data.escalado_a_usuario_nombre
            
            if update_data.calificacion is not None:
                update_query["$set"]["metadata.calificacion"] = update_data.calificacion
            
            if update_data.comentario_calificacion is not None:
                update_query["$set"]["metadata.comentario_calificacion"] = update_data.comentario_calificacion
            
            # Actualizar
            result = await collection.find_one_and_update(
                {"session_id": session_id},
                update_query,
                return_document=True
            )
            
            if not result:
                raise ValueError(f"Conversación no encontrada: {session_id}")
            
            logger.info(f"✅ Conversación actualizada: {session_id}")
            
            result["id"] = str(result.pop("_id"))
            return ConversationResponse(**result)
            
        except Exception as e:
            logger.error(f"❌ Error actualizando conversación: {e}")
            raise
    
    @staticmethod
    async def list_conversations(
        id_agente: Optional[int] = None,
        estado: Optional[str] = None,
        origin: Optional[str] = None,
        escaladas: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> ConversationListResponse:
        """
        Listar conversaciones con filtros
        
        Args:
            id_agente: Filtrar por agente
            estado: Filtrar por estado
            origin: Filtrar por origen
            escaladas: Solo conversaciones escaladas
            page: Número de página
            page_size: Tamaño de página
            
        Returns:
            ConversationListResponse con paginación
        """
        try:
            collection = await get_conversations_collection()
            
            # Construir filtro
            filter_query = {}
            
            if id_agente is not None:
                filter_query["id_agente"] = id_agente
            
            if estado is not None:
                filter_query["metadata.estado"] = estado
            
            if origin is not None:
                filter_query["origin"] = origin
            
            if escaladas is not None:
                filter_query["metadata.requirio_atencion_humana"] = escaladas
            
            # Contar total
            total = await collection.count_documents(filter_query)
            
            # Calcular skip
            skip = (page - 1) * page_size
            
            # Obtener conversaciones
            cursor = collection.find(filter_query).sort("created_at", -1).skip(skip).limit(page_size)
            
            conversations = []
            async for conv in cursor:
                conv["id"] = str(conv.pop("_id"))
                conversations.append(ConversationResponse(**conv))
            
            return ConversationListResponse(
                total=total,
                page=page,
                page_size=page_size,
                conversations=conversations
            )
            
        except Exception as e:
            logger.error(f"❌ Error listando conversaciones: {e}")
            raise
    
    @staticmethod
    async def get_conversation_stats(
        id_agente: Optional[int] = None
    ) -> ConversationStats:
        """
        Obtener estadísticas de conversaciones
        
        Args:
            id_agente: Filtrar por agente (opcional)
            
        Returns:
            ConversationStats con métricas
        """
        try:
            collection = await get_conversations_collection()
            
            # Filtro base
            match_filter = {}
            if id_agente is not None:
                match_filter["id_agente"] = id_agente
            
            # Pipeline de agregación
            pipeline = [
                {"$match": match_filter},
                {
                    "$group": {
                        "_id": None,
                        "total_conversaciones": {"$sum": 1},
                        "conversaciones_activas": {
                            "$sum": {"$cond": [{"$eq": ["$metadata.estado", "activa"]}, 1, 0]}
                        },
                        "conversaciones_finalizadas": {
                            "$sum": {"$cond": [{"$eq": ["$metadata.estado", "finalizada"]}, 1, 0]}
                        },
                        "conversaciones_escaladas": {
                            "$sum": {"$cond": ["$metadata.requirio_atencion_humana", 1, 0]}
                        },
                        "total_mensajes": {"$sum": "$metadata.total_mensajes"},
                        "calificaciones": {"$push": "$metadata.calificacion"}
                    }
                }
            ]
            
            result = await collection.aggregate(pipeline).to_list(1)
            
            if not result:
                return ConversationStats(
                    total_conversaciones=0,
                    conversaciones_activas=0,
                    conversaciones_finalizadas=0,
                    conversaciones_escaladas=0,
                    promedio_mensajes_por_conversacion=0.0,
                    calificacion_promedio=None
                )
            
            data = result[0]
            
            # Calcular promedio de mensajes
            promedio_mensajes = (
                data["total_mensajes"] / data["total_conversaciones"]
                if data["total_conversaciones"] > 0
                else 0.0
            )
            
            # Calcular promedio de calificaciones
            calificaciones = [c for c in data["calificaciones"] if c is not None]
            calificacion_promedio = (
                sum(calificaciones) / len(calificaciones)
                if calificaciones
                else None
            )
            
            return ConversationStats(
                total_conversaciones=data["total_conversaciones"],
                conversaciones_activas=data["conversaciones_activas"],
                conversaciones_finalizadas=data["conversaciones_finalizadas"],
                conversaciones_escaladas=data["conversaciones_escaladas"],
                promedio_mensajes_por_conversacion=round(promedio_mensajes, 2),
                calificacion_promedio=round(calificacion_promedio, 2) if calificacion_promedio else None
            )
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            raise
    
    @staticmethod
    async def delete_conversation(session_id: str) -> bool:
        """
        Eliminar una conversación
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            collection = await get_conversations_collection()
            
            result = await collection.delete_one({"session_id": session_id})
            
            if result.deleted_count == 0:
                raise ValueError(f"Conversación no encontrada: {session_id}")
            
            logger.info(f"🗑️ Conversación eliminada: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error eliminando conversación: {e}")
            raise


 
    @staticmethod
    async def get_inactive_conversations(
        tiempo_limite: datetime,
        estados: List[ConversationStatus]
    ) -> List[Dict]:
        """
        Obtener conversaciones inactivas
        
        Args:
            tiempo_limite: Conversaciones sin actividad desde esta fecha
            estados: Lista de estados a considerar
            
        Returns:
            Lista de conversaciones inactivas
        """
        try:
            collection = await get_conversations_collection()
            
            # Convertir enums a strings para la query
            estados_str = [e.value for e in estados]
            
            # Buscar conversaciones con última actualización antes del tiempo límite
            cursor = collection.find({
                "metadata.estado": {"$in": estados_str},
                "updated_at": {"$lt": tiempo_limite}
            })
            
            conversaciones = []
            async for conv in cursor:
                conv['_id'] = str(conv['_id'])
                conversaciones.append(conv)
            
            logger.info(f"📊 Encontradas {len(conversaciones)} conversaciones inactivas")
            return conversaciones
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo conversaciones inactivas: {e}")
            return []
        

    @staticmethod
    async def update_conversation(
        session_id: str,
        update_data: ConversationUpdate
    ) -> ConversationResponse:
        """
        Alias de update_conversation_status para compatibilidad
        
        Args:
            session_id: ID de la sesión
            update_data: Datos a actualizar
            
        Returns:
            ConversationResponse actualizada
        """
        return await ConversationService.update_conversation_status(
            session_id=session_id,
            update_data=update_data
        )