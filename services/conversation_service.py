# services/conversation_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime
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

from io import BytesIO
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from database.database import get_db  # 🔥 TU IMPORT CORRECTO
from models.visitante_anonimo import VisitanteAnonimo  # 🔥 TU MODELO

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Servicio para gestionar conversaciones en MongoDB
    """
    

    @staticmethod
    async def create_conversation(
        conversation_data: ConversationCreate
    ) -> ConversationResponse:
        """Crear una nueva conversación"""
        try:
            # 🔥 AGREGAR LOG AL INICIO:
            logger.info(f"=" * 80)
            logger.info(f"🏗️ INICIANDO CREACIÓN EN MONGODB")
            logger.info(f"   - Session ID: {conversation_data.session_id}")
            logger.info(f"   - ID Visitante: {conversation_data.id_visitante}")
            logger.info(f"   - ID Agente: {conversation_data.id_agente}")
            logger.info(f"   - Agent Name: {conversation_data.agent_name}")
            logger.info(f"=" * 80)
            
            collection = await get_conversations_collection()
            
            # 🔥 AGREGAR LOG DE COLECCIÓN:
            logger.info(f"✅ Colección MongoDB obtenida: {collection.name}")
            
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
            
            # 🔥 AGREGAR LOG DE METADATA:
            logger.info(f"📋 Metadata creada:")
            logger.info(f"   - Estado: {metadata.estado}")
            logger.info(f"   - IP: {metadata.ip_origen}")
            logger.info(f"   - Dispositivo: {metadata.dispositivo}")
            
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
            
            # 🔥 AGREGAR LOG ANTES DE INSERTAR:
            logger.info(f"📄 Documento a insertar:")
            logger.info(f"{conversation.dict()}")
            
            # Insertar en MongoDB
            result = await collection.insert_one(conversation.dict())
            
            # 🔥 AGREGAR LOG DESPUÉS DE INSERTAR:
            logger.info(f"=" * 80)
            logger.info(f"✅ DOCUMENTO INSERTADO EN MONGODB")
            logger.info(f"   - ObjectId: {result.inserted_id}")
            logger.info(f"   - Session ID: {conversation_data.session_id}")
            logger.info(f"   - Acknowledged: {result.acknowledged}")
            logger.info(f"=" * 80)
            
            # Retornar con el ID generado
            return ConversationResponse(
                id=str(result.inserted_id),
                **conversation.dict()
            )
            
        except Exception as e:
            # 🔥 MEJORAR LOG DE ERROR:
            logger.error(f"=" * 80)
            logger.error(f"❌ ERROR EN CREATE_CONVERSATION")
            logger.error(f"   - Session ID: {conversation_data.session_id}")
            logger.error(f"   - Error: {str(e)}")
            logger.error(f"   - Tipo: {type(e).__name__}")
            logger.error(f"=" * 80)
            import traceback
            logger.error(traceback.format_exc())
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
        """Agregar un mensaje a una conversación existente"""
        try:
            # 🔥 AGREGAR LOG AL INICIO:
            logger.info(f"=" * 80)
            logger.info(f"💬 GUARDANDO MENSAJE EN MONGODB")
            logger.info(f"   - Session ID: {session_id}")
            logger.info(f"   - Role: {message_data.role}")
            logger.info(f"   - Contenido (primeros 100 chars): {message_data.content[:100]}...")
            logger.info(f"   - Sources used: {message_data.sources_used}")
            logger.info(f"   - Model used: {message_data.model_used}")
            logger.info(f"=" * 80)
            
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
            
            # 🔥 AGREGAR LOG DE MENSAJE:
            logger.info(f"📝 Mensaje creado:")
            logger.info(f"   - Role: {message.role}")
            logger.info(f"   - Timestamp: {message.timestamp}")
            logger.info(f"   - Content length: {len(message.content)} chars")
            
            # Actualizar contadores
            update_query = {
                "$push": {"messages": message.dict()},
                "$set": {"updated_at": datetime.utcnow()},
                "$inc": {
                    "metadata.total_mensajes": 1
                }
            }
            
            # Incrementar contador según el rol
            role_str = message_data.role if isinstance(message_data.role, str) else message_data.role.value
            if role_str == "user":
                update_query["$inc"]["metadata.total_mensajes_usuario"] = 1
            elif role_str in ["assistant", "human_agent"]:
                update_query["$inc"]["metadata.total_mensajes_agente"] = 1
            
            # 🔥 AGREGAR LOG DE UPDATE QUERY:
            logger.info(f"🔄 Update query:")
            logger.info(f"{update_query}")
            
            # Actualizar en MongoDB
            result = await collection.find_one_and_update(
                {"session_id": session_id},
                update_query,
                return_document=True
            )
            
            if not result:
                # 🔥 MEJORAR LOG DE ERROR:
                logger.error(f"=" * 80)
                logger.error(f"❌ CONVERSACIÓN NO ENCONTRADA")
                logger.error(f"   - Session ID buscado: {session_id}")
                logger.error(f"   - Mensaje que se intentaba guardar: {message_data.role}")
                logger.error(f"=" * 80)
                raise ValueError(f"Conversación no encontrada: {session_id}")
            
            # 🔥 AGREGAR LOG DE ÉXITO:
            logger.info(f"=" * 80)
            logger.info(f"✅ MENSAJE GUARDADO EXITOSAMENTE")
            logger.info(f"   - Session ID: {session_id}")
            logger.info(f"   - Total mensajes ahora: {result['metadata']['total_mensajes']}")
            logger.info(f"   - Mensajes usuario: {result['metadata']['total_mensajes_usuario']}")
            logger.info(f"   - Mensajes agente: {result['metadata']['total_mensajes_agente']}")
            logger.info(f"=" * 80)
            
            # Convertir y retornar
            result["id"] = str(result.pop("_id"))
            return ConversationResponse(**result)
            
        except Exception as e:
            # 🔥 MEJORAR LOG DE ERROR:
            logger.error(f"=" * 80)
            logger.error(f"❌ ERROR EN ADD_MESSAGE")
            logger.error(f"   - Session ID: {session_id}")
            logger.error(f"   - Role del mensaje: {message_data.role}")
            logger.error(f"   - Error: {str(e)}")
            logger.error(f"   - Tipo: {type(e).__name__}")
            logger.error(f"=" * 80)
            import traceback
            logger.error(traceback.format_exc())
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
    
    # services/conversation_service.py
    @staticmethod
    async def list_conversations(
        id_agente: Optional[int] = None,
        estado: Optional[str] = None,
        origin: Optional[str] = None,
        escaladas: Optional[bool] = None,
        id_visitante: Optional[int] = None,
        user_id: Optional[int] = None,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        calificacion_min: Optional[int] = None,
        calificacion_max: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> ConversationListResponse:
        """
        Listar conversaciones con filtros avanzados
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
            
            if id_visitante is not None:
                filter_query["id_visitante"] = id_visitante
            
            if user_id is not None:
                filter_query["metadata.escalado_a_usuario_id"] = user_id
            
            # Filtro por rango de fechas
            if fecha_inicio or fecha_fin:
                filter_query["created_at"] = {}
                if fecha_inicio:
                    filter_query["created_at"]["$gte"] = fecha_inicio
                if fecha_fin:
                    filter_query["created_at"]["$lte"] = fecha_fin
            
            # Filtro por calificación
            if calificacion_min or calificacion_max:
                filter_query["metadata.calificacion"] = {}
                if calificacion_min:
                    filter_query["metadata.calificacion"]["$gte"] = calificacion_min
                if calificacion_max:
                    filter_query["metadata.calificacion"]["$lte"] = calificacion_max
            
            # Contar total
            total = await collection.count_documents(filter_query)
            
            # Calcular skip
            skip = (page - 1) * page_size
            
            # Determinar orden
            sort_direction = -1 if sort_order.lower() == "desc" else 1
            
            # Obtener conversaciones
            cursor = collection.find(filter_query).sort(sort_by, sort_direction).skip(skip).limit(page_size)
            
            conversations = []
            async for conv in cursor:
                conv["id"] = str(conv.pop("_id"))
                conversations.append(ConversationResponse(**conv))
            
            logger.info(f"📋 Listadas {len(conversations)} de {total} conversaciones")
            
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
    
    @staticmethod
    async def obtener_o_crear_conversacion_activa(
        session_id: str,
        id_agente: int,
        agent_name: str,
        agent_type: Optional[str] = None,
        id_visitante: Optional[int] = None,
        origin: str = "web",
        ip_origen: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ConversationResponse:
        """
        🔥 NUEVA FUNCIÓN:
        Obtener conversación activa o crear nueva si:
        - No existe conversación
        - La conversación existente está finalizada/abandonada
        
        Args:
            session_id: ID de la sesión
            id_agente: ID del agente
            agent_name: Nombre del agente
            agent_type: Tipo de agente
            id_visitante: ID del visitante
            origin: Origen de la conversación
            ip_origen: IP del cliente
            user_agent: User agent del navegador
            
        Returns:
            ConversationResponse (existente activa o nueva)
        """
        try:
            collection = await get_conversations_collection()
            
            # 🔥 PASO 1: Buscar conversación existente
            conversation = await collection.find_one({"session_id": session_id})
            
            if conversation:
                estado = conversation.get("metadata", {}).get("estado")
                
                # 🔥 PASO 2: Verificar si está activa
                if estado == "activa":
                    logger.info(f"✅ Conversación activa encontrada: {session_id}")
                    conversation["id"] = str(conversation.pop("_id"))
                    return ConversationResponse(**conversation)
                
                else:
                    # 🔥 PASO 3: Conversación finalizada → Crear nueva
                    logger.info(f"🔄 Conversación {session_id} está {estado}, creando nueva...")
                    
                    # Crear nueva conversación con nuevo session_id
                    from datetime import datetime
                    import uuid
                    
                    nuevo_session_id = f"{session_id}-{int(datetime.utcnow().timestamp())}"
                    
                    conversation_data = ConversationCreate(
                        session_id=nuevo_session_id,
                        id_agente=id_agente,
                        agent_name=agent_name,
                        agent_type=agent_type,
                        id_visitante=id_visitante,
                        origin=origin,
                        ip_origen=ip_origen,
                        user_agent=user_agent
                    )
                    
                    return await ConversationService.create_conversation(conversation_data)
            
            else:
                # 🔥 PASO 4: No existe conversación → Crear nueva
                logger.info(f"📝 No existe conversación para {session_id}, creando nueva...")
                
                conversation_data = ConversationCreate(
                    session_id=session_id,
                    id_agente=id_agente,
                    agent_name=agent_name,
                    agent_type=agent_type,
                    id_visitante=id_visitante,
                    origin=origin,
                    ip_origen=ip_origen,
                    user_agent=user_agent
                )
                
                return await ConversationService.create_conversation(conversation_data)
                
        except Exception as e:
            logger.error(f"❌ Error en obtener_o_crear_conversacion_activa: {e}")
            raise




    @staticmethod
    async def export_to_excel(
        id_agente: Optional[int] = None,
        estado: Optional[str] = None,
        origin: Optional[str] = None,
        escaladas: Optional[bool] = None,
        id_visitante: Optional[int] = None,
        user_id: Optional[int] = None,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        calificacion_min: Optional[int] = None,
        calificacion_max: Optional[int] = None,
        incluir_visitante: bool = True
    ) -> BytesIO:
        """
        Exportar conversaciones a Excel con datos del visitante
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
            if id_visitante is not None:
                filter_query["id_visitante"] = id_visitante
            if user_id is not None:
                filter_query["metadata.escalado_a_usuario_id"] = user_id
            
            if fecha_inicio or fecha_fin:
                filter_query["created_at"] = {}
                if fecha_inicio:
                    filter_query["created_at"]["$gte"] = fecha_inicio
                if fecha_fin:
                    filter_query["created_at"]["$lte"] = fecha_fin
            
            if calificacion_min or calificacion_max:
                filter_query["metadata.calificacion"] = {}
                if calificacion_min:
                    filter_query["metadata.calificacion"]["$gte"] = calificacion_min
                if calificacion_max:
                    filter_query["metadata.calificacion"]["$lte"] = calificacion_max
            
            # Obtener conversaciones
            cursor = collection.find(filter_query).sort("created_at", -1)
            conversations = await cursor.to_list(length=None)
            
            # Preparar datos
            data = []
            visitante_ids = set()
            
            for conv in conversations:
                row = {
                    'Session ID': conv.get('session_id'),
                    'ID Agente': conv.get('id_agente'),
                    'Nombre Agente': conv.get('agent_name'),
                    'Tipo Agente': conv.get('agent_type'),
                    'ID Visitante': conv.get('id_visitante'),
                    'Estado': conv.get('metadata', {}).get('estado'),
                    'Origen': conv.get('origin'),
                    'Fecha Creación': conv.get('created_at'),
                    'Fecha Actualización': conv.get('updated_at'),
                    'Total Mensajes': conv.get('metadata', {}).get('total_mensajes', 0),
                    'Mensajes Usuario': conv.get('metadata', {}).get('total_mensajes_usuario', 0),
                    'Mensajes Agente': conv.get('metadata', {}).get('total_mensajes_agente', 0),
                    'Requirió Atención Humana': conv.get('metadata', {}).get('requirio_atencion_humana', False),
                    'Escalado a Usuario ID': conv.get('metadata', {}).get('escalado_a_usuario_id'),
                    'Escalado a Usuario Nombre': conv.get('metadata', {}).get('escalado_a_usuario_nombre'),
                    'Calificación': conv.get('metadata', {}).get('calificacion'),
                    'Comentario Calificación': conv.get('metadata', {}).get('comentario_calificacion'),
                    'IP Origen': conv.get('metadata', {}).get('ip_origen'),
                    'User Agent': conv.get('metadata', {}).get('user_agent'),
                    'Dispositivo': conv.get('metadata', {}).get('dispositivo'),
                    'Navegador': conv.get('metadata', {}).get('navegador')
                }
                
                if conv.get('id_visitante'):
                    visitante_ids.add(conv.get('id_visitante'))
                
                data.append(row)
            
            # 🔥 OBTENER DATOS DE VISITANTES DESDE TU BD MYSQL
            visitantes_data = {}
            if incluir_visitante and visitante_ids:
                db = next(get_db())
                try:
                    visitantes = db.query(VisitanteAnonimo).filter(
                        VisitanteAnonimo.id_visitante.in_(list(visitante_ids))
                    ).all()
                    
                    for visitante in visitantes:
                        visitantes_data[visitante.id_visitante] = {
                            'nombre': visitante.nombre,
                            'apellido': visitante.apellido,
                            'email': visitante.email,
                            'edad': visitante.edad,
                            'ocupacion': visitante.ocupacion,
                            'pais': visitante.pais,
                            'ciudad': visitante.ciudad,
                            'canal_acceso': visitante.canal_acceso,
                            'pertenece_instituto': visitante.pertenece_instituto,
                            'satisfaccion_estimada': visitante.satisfaccion_estimada,
                            'primera_visita': visitante.primera_visita,
                            'total_conversaciones': visitante.total_conversaciones,
                            'total_mensajes': visitante.total_mensajes,
                            'dispositivo': visitante.dispositivo.value if visitante.dispositivo else None,
                            'navegador': visitante.navegador,
                            'sistema_operativo': visitante.sistema_operativo
                        }
                finally:
                    db.close()
            
            # 🔥 ENRIQUECER DATOS CON INFORMACIÓN DEL VISITANTE
            if incluir_visitante:
                for row in data:
                    vid = row['ID Visitante']
                    if vid and vid in visitantes_data:
                        v = visitantes_data[vid]
                        row['Visitante Nombre'] = v['nombre']
                        row['Visitante Apellido'] = v['apellido']
                        row['Visitante Email'] = v['email']
                        row['Visitante Edad'] = v['edad']
                        row['Visitante Ocupación'] = v['ocupacion']
                        row['Visitante País'] = v['pais']
                        row['Visitante Ciudad'] = v['ciudad']
                        row['Visitante Canal Acceso'] = v['canal_acceso']
                        row['Visitante Pertenece Instituto'] = v['pertenece_instituto']
                        row['Visitante Satisfacción'] = v['satisfaccion_estimada']
                        row['Visitante Primera Visita'] = v['primera_visita']
                        row['Visitante Total Conversaciones'] = v['total_conversaciones']
                        row['Visitante Total Mensajes'] = v['total_mensajes']
                        row['Visitante Dispositivo'] = v['dispositivo']
                        row['Visitante Navegador'] = v['navegador']
                        row['Visitante SO'] = v['sistema_operativo']
            
            # Crear Excel
            df = pd.DataFrame(data)
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Conversaciones', index=False)
                
                workbook = writer.book
                worksheet = writer.sheets['Conversaciones']
                
                # Estilo de encabezados
                header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                
                for cell in worksheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Ajustar anchos de columna
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            output.seek(0)
            logger.info(f"✅ Excel generado con {len(data)} conversaciones")
            
            return output
            
        except Exception as e:
            logger.error(f"❌ Error generando Excel: {e}")
            raise