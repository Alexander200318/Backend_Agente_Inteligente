# routers/conversation_router.py
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Body, status, Depends
from datetime import datetime, timedelta
import logging

from models.conversation_mongo import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    ConversationListResponse,
    ConversationStats,
    MessageCreate,
    ConversationStatus,
    MessageRole
)
from models.usuario import Usuario
from services.conversation_service import ConversationService
from auth.dependencies import get_current_user

from fastapi.responses import StreamingResponse
from io import BytesIO
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/conversations",
    tags=["Conversaciones mongo"]
)


# ==================== CRUD BÁSICO ====================

@router.post(
    "/",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva conversación"
)
async def create_conversation(conversation_data: ConversationCreate):
    """
    Crear una nueva conversación en MongoDB
    
    **Campos requeridos:**
    - session_id: ID único de la sesión
    - id_agente: ID del agente asignado
    - agent_name: Nombre del agente
    
    **Campos opcionales:**
    - agent_type: Tipo de agente
    - id_visitante: ID del visitante
    - origin: Origen (web, mobile, widget, api)
    - ip_origen, user_agent, dispositivo, navegador: Metadata del cliente
    """
    try:
        return await ConversationService.create_conversation(conversation_data)
    except Exception as e:
        logger.error(f"Error creando conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear conversación: {str(e)}"
        )


@router.get(
    "/{session_id}",
    response_model=ConversationResponse,
    summary="Obtener conversación por session_id"
)
async def get_conversation(session_id: str):
    """
    Obtener una conversación específica con todo su historial de mensajes
    """
    try:
        conversation = await ConversationService.get_conversation_by_session(session_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación no encontrada: {session_id}"
            )
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener conversación: {str(e)}"
        )


@router.patch(
    "/{session_id}",
    response_model=ConversationResponse,
    summary="Actualizar estado de conversación"
)
async def update_conversation(session_id: str, update_data: ConversationUpdate):
    """
    Actualizar estado y metadata de una conversación
    
    **Campos actualizables:**
    - estado: activa, finalizada, abandonada, escalada_humano
    - requirio_atencion_humana: Boolean
    - escalado_a_usuario_id: ID del usuario al que se escaló
    - escalado_a_usuario_nombre: Nombre del usuario
    - calificacion: 1-5
    - comentario_calificacion: Texto del comentario
    """
    try:
        return await ConversationService.update_conversation_status(session_id, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error actualizando conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar conversación: {str(e)}"
        )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar conversación"
)
async def delete_conversation(session_id: str):
    """
    Eliminar una conversación permanentemente
    ⚠️ Esta acción no se puede deshacer
    """
    try:
        await ConversationService.delete_conversation(session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error eliminando conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar conversación: {str(e)}"
        )


# 🔥 NUEVO ENDPOINT: Guardar mensaje desde widget (sin WebSocket)
@router.post(
    "/save-message",
    summary="Guardar mensaje del widget"
)
async def save_widget_message(
    session_id: str = Query(..., description="ID de la sesión"),
    content: str = Query(..., description="Contenido del mensaje"),
    role: str = Query(default="user", description="user o assistant"),
    id_visitante: Optional[int] = Query(None, description="ID del visitante autenticado"),
    agent_name: str = Query(default="Agente Virtual", description="Nombre del agente"),
    id_agente: int = Query(default=1, description="ID del agente"),
    contenidos_json: Optional[str] = Query(None, description="JSON con contenidos consultados [{'id': 1, 'titulo': 'test', ...}]")
):
    """
    🔥 Guardar mensaje desde el widget (REST, sin WebSocket)
    
    Se llama en cada interacción del usuario con el chatbot
    - Crea la conversación si no existe
    - Guarda el mensaje CON contenidos consultados
    - Retorna la conversación actualizada
    """
    try:
        logger.info(f"📝 Guardando mensaje desde widget:")
        logger.info(f"   - Session: {session_id}")
        logger.info(f"   - Visitante: {id_visitante}")
        logger.info(f"   - Rol: {role}")
        logger.info(f"   - Agente: {agent_name}")
        
        # Verificar si la conversación existe
        existing_conv = await ConversationService.get_conversation_by_session(session_id)
        
        if not existing_conv:
            logger.info(f"⚠️ Conversación no existe, creando nueva...")
            
            # Crear conversación
            conv_create = ConversationCreate(
                session_id=session_id,
                id_agente=id_agente,
                agent_name=agent_name,
                agent_type="virtual",
                id_visitante=id_visitante,  # 🔥 INCLUIR VISITANTE
                origin="widget"
            )
            existing_conv = await ConversationService.create_conversation(conv_create)
            logger.info(f"✅ Conversación creada: {session_id}")
        
        # 🔥 PROCESAR CONTENIDOS CONSULTADOS
        contenidos_consultados = []
        total_contenidos = 0
        
        if contenidos_json:
            try:
                import json
                contenidos_list = json.loads(contenidos_json)
                
                # Transformar a ContentReference objects
                from models.conversation_mongo import ContentReference
                
                for item in contenidos_list:
                    ref = ContentReference(
                        id_unidad_contenido=item.get('id'),
                        titulo=item.get('titulo'),
                        tipo_contenido=item.get('tipo', 'documento'),
                        chunk_text=item.get('contenido'),
                        relevancia_score=item.get('score', 0.0),
                        categoria=item.get('categoria')
                    )
                    contenidos_consultados.append(ref)
                
                total_contenidos = len(contenidos_consultados)
                logger.info(f"✅ {total_contenidos} contenidos procesados")
            except Exception as e:
                logger.error(f"⚠️ Error procesando contenidos: {e}")
        
        # Guardar mensaje
        message = MessageCreate(
            role=MessageRole[role] if isinstance(role, str) else role,
            content=content,
            contenidos_consultados=contenidos_consultados,  # 🔥 NUEVO
            total_contenidos_usados=total_contenidos  # 🔥 NUEVO
        )
        
        updated_conv = await ConversationService.add_message(session_id, message)
        logger.info(f"✅ Mensaje guardado en MongoDB con {total_contenidos} contenidos")
        
        return {
            "ok": True,
            "session_id": session_id,
            "total_mensajes": updated_conv.metadata.total_mensajes,
            "total_contenidos_usados": total_contenidos,
            "conversation_id": str(updated_conv.id)
        }
        
    except Exception as e:
        logger.error(f"❌ Error guardando mensaje: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar mensaje: {str(e)}"
        )


# ==================== MENSAJES ====================

@router.post(
    "/{session_id}/messages",
    response_model=ConversationResponse,
    summary="Agregar mensaje a conversación"
)
async def add_message(session_id: str, message_data: MessageCreate):
    """
    Agregar un nuevo mensaje a una conversación existente
    
    **Roles disponibles:**
    - user: Mensaje del usuario
    - assistant: Respuesta del agente virtual
    - human_agent: Respuesta de agente humano
    - system: Mensaje del sistema
    
    **Campos opcionales:**
    - sources_used: Número de fuentes consultadas
    - model_used: Modelo de IA utilizado (ej: gpt-4, claude-3)
    - token_count: Tokens consumidos
    - user_id, user_name: Para mensajes de agente humano
    """
    try:
        return await ConversationService.add_message(session_id, message_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error agregando mensaje: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al agregar mensaje: {str(e)}"
        )


@router.get(
    "/{session_id}/messages",
    summary="Obtener solo mensajes de conversación"
)
async def get_messages(
    session_id: str,
    role: Optional[MessageRole] = Query(None, description="Filtrar por rol"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limitar cantidad")
):
    """
    Obtener solo los mensajes de una conversación (sin metadata completa)
    
    Útil para mostrar el historial de chat sin datos extras
    """
    try:
        conversation = await ConversationService.get_conversation_by_session(session_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación no encontrada: {session_id}"
            )
        
        messages = conversation.messages
        
        # Filtrar por rol si se especifica
        if role:
            messages = [msg for msg in messages if msg.role == role.value]
        
        # Limitar cantidad si se especifica
        if limit:
            messages = messages[-limit:]
        
        return {
            "session_id": session_id,
            "total_messages": len(messages),
            "messages": messages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo mensajes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener mensajes: {str(e)}"
        )



@router.get(
    "/export/excel",
    summary="Exportar conversaciones a Excel con filtros"
)
async def export_conversations_to_excel(
    id_agente: Optional[int] = Query(None, description="Filtrar por ID de agente (None = todos)"),
    estado: Optional[ConversationStatus] = Query(None, description="Filtrar por estado (None = todos)"),
    origin: Optional[str] = Query(None, description="Filtrar por origen (web, mobile, widget, api)"),
    escaladas: Optional[bool] = Query(None, description="🆘 Solo conversaciones escaladas"),
    incluir_visitante: bool = Query(True, description="👤 Incluir datos de visitante (IP, dispositivo, navegador, ubicación)"),
    solo_visitante: bool = Query(False, description="👤 Solo datos del visitante (Nombre, Apellido, Email, Ocupación)"),
    fecha_inicio: Optional[datetime] = Query(None, description="📅 Fecha inicio (Todo el historial si no se especifica)"),
    fecha_fin: Optional[datetime] = Query(None, description="📅 Fecha fin (hoy si no se especifica)"),
    columnas_excluidas: List[str] = Query(
    default=["id_agente", "session_id", "id_visitante", "escalado_a_usuario_id", 
             "comentario_calificacion", "calificacion", "visitante_pais", 
             "visitante_ciudad", "visitante_satisfaccion", "visitante_total_mensajes"],
    description="Columnas a excluir del reporte"
)
):
    """
    📊 Exportar conversaciones a Excel con filtros personalizados
    
    **Filtros disponibles:**
    - **Período**: Todo el historial (sin fechas) | Rango personalizado
    - **🤖 Agente Virtual**: Todos los agentes (None) | Agente específico
    - **📊 Estado**: Todos los estados (None) | activa, finalizada, escalada_humano, abandonada
    - **📱 Origen**: Todos los orígenes (None) | web, mobile, widget, api
    - **🆘 Solo escaladas**: Conversaciones que requirieron atención humana
    - **👤 Incluir datos de visitante**: IP, dispositivo, navegador, ubicación
    
    **Columnas excluidas por defecto:** Calificación, Satisfacción, País, Ciudad, Mensajes
    """
    try:
        estado_str = estado.value if estado else None
        
        excel_file = await ConversationService.export_to_excel(
            id_agente=id_agente,
            estado=estado_str,
            origin=origin,
            escaladas=escaladas,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            incluir_visitante=incluir_visitante,
            solo_visitante=solo_visitante,
            columnas_excluidas=columnas_excluidas
        )
        
        filename = f"conversaciones_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exportando a Excel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al exportar: {str(e)}"
        )



# 🔥 NUEVO ENDPOINT: Exportar a Word
@router.get(
    "/export/word",
    summary="Exportar conversaciones a Word con filtros"
)
async def export_conversations_to_word(
    id_agente: Optional[int] = Query(None, description="Filtrar por ID de agente (None = todos)"),
    estado: Optional[ConversationStatus] = Query(None, description="Filtrar por estado (None = todos)"),
    origin: Optional[str] = Query(None, description="Filtrar por origen (web, mobile, widget, api)"),
    escaladas: Optional[bool] = Query(None, description="🆘 Solo conversaciones escaladas"),
    incluir_visitante: bool = Query(True, description="👤 Incluir datos de visitante (IP, dispositivo, navegador, ubicación)"),
    solo_visitante: bool = Query(False, description="👤 Solo datos del visitante (Nombre, Apellido, Email, Ocupación)"),
    fecha_inicio: Optional[datetime] = Query(None, description="📅 Fecha inicio (Todo el historial si no se especifica)"),
    fecha_fin: Optional[datetime] = Query(None, description="📅 Fecha fin (hoy si no se especifica)"),
    columnas_excluidas: List[str] = Query(
        default=["id_agente", "session_id", "id_visitante", "escalado_a_usuario_id", 
                 "comentario_calificacion", "calificacion", "visitante_pais", 
                 "visitante_ciudad", "visitante_satisfaccion", "visitante_total_mensajes"],
        description="Columnas a excluir del reporte"
    ),
    current_user: Usuario = Depends(get_current_user),
):
    """
    📄 Exportar conversaciones a Word con filtros personalizados
    
    Los mismos filtros que Excel pero genera un documento Word formateado bonito.
    """
    try:
        estado_str = estado.value if estado else None
        
        # Extraer nombre del usuario desde el objeto Usuario
        usuario_nombre = current_user.username if current_user else 'Usuario Desconocido'
        
        word_file = await ConversationService.export_to_word(
            id_agente=id_agente,
            estado=estado_str,
            origin=origin,
            escaladas=escaladas,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            incluir_visitante=incluir_visitante,
            solo_visitante=solo_visitante,
            columnas_excluidas=columnas_excluidas,
            usuario_nombre=usuario_nombre
        )
        
        filename = f"conversaciones_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"
        
        return StreamingResponse(
            word_file,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exportando a Word: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al exportar: {str(e)}"
        )



# ==================== LISTADO Y FILTROS ====================

# routers/conversation_router.py

@router.get(
    "/",
    response_model=ConversationListResponse,
    summary="Listar conversaciones con filtros"
)
async def list_conversations(
    id_agente: Optional[int] = Query(None, description="Filtrar por ID de agente"),
    estado: Optional[ConversationStatus] = Query(None, description="Filtrar por estado"),
    origin: Optional[str] = Query(None, description="Filtrar por origen (web, mobile, etc)"),
    escaladas: Optional[bool] = Query(None, description="Solo conversaciones escaladas a humano"),
    id_visitante: Optional[int] = Query(None, description="Filtrar por ID de visitante"),
    user_id: Optional[int] = Query(None, description="Filtrar por agente humano asignado"),
    fecha_inicio: Optional[datetime] = Query(None, description="Fecha inicio (ISO 8601)"),
    fecha_fin: Optional[datetime] = Query(None, description="Fecha fin (ISO 8601)"),
    calificacion_min: Optional[int] = Query(None, ge=1, le=5, description="Calificación mínima"),
    calificacion_max: Optional[int] = Query(None, ge=1, le=5, description="Calificación máxima"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Resultados por página"),
    sort_by: str = Query("created_at", description="Campo para ordenar"),
    sort_order: str = Query("desc", description="Orden: asc o desc")
):
    """
    Listar conversaciones con paginación y filtros opcionales
    
    **Filtros disponibles:**
    - id_agente: Conversaciones de un agente específico
    - estado: activa, finalizada, abandonada, escalada_humano
    - origin: web, mobile, widget, api
    - escaladas: true/false para ver solo las que requirieron atención humana
    - id_visitante: Conversaciones de un visitante específico
    - user_id: Conversaciones atendidas por agente humano específico
    - fecha_inicio: Conversaciones creadas desde esta fecha
    - fecha_fin: Conversaciones creadas hasta esta fecha
    - calificacion_min: Calificación mínima (1-5)
    - calificacion_max: Calificación máxima (1-5)
    
    **Paginación:**
    - page: Número de página (default: 1)
    - page_size: Resultados por página (max: 100, default: 20)
    - sort_by: Campo para ordenar (default: created_at)
    - sort_order: asc o desc (default: desc)
    """
    try:
        estado_str = estado.value if estado else None
        
        return await ConversationService.list_conversations(
            id_agente=id_agente,
            estado=estado_str,
            origin=origin,
            escaladas=escaladas,
            id_visitante=id_visitante,
            user_id=user_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            calificacion_min=calificacion_min,
            calificacion_max=calificacion_max,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
    except Exception as e:
        logger.error(f"Error listando conversaciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar conversaciones: {str(e)}"
        )


# ==================== ESTADÍSTICAS ====================

@router.get(
    "/stats/overview",
    response_model=ConversationStats,
    summary="Estadísticas generales"
)
async def get_conversation_stats(
    id_agente: Optional[int] = Query(None, description="Filtrar estadísticas por agente"),
    fecha_inicio: Optional[datetime] = Query(None, description="Fecha inicio (ISO 8601)"),  # 🔥 AGREGAR
    fecha_fin: Optional[datetime] = Query(None, description="Fecha fin (ISO 8601)")  # 🔥 AGREGAR
):
    """
    Obtener estadísticas generales de conversaciones
    
    **Métricas incluidas:**
    - Total de conversaciones
    - Conversaciones por estado (activas, finalizadas, escaladas)
    - Promedio de mensajes por conversación
    - Calificación promedio
    
    Si se especifica id_agente, las estadísticas serán solo de ese agente
    Si se especifican fechas, filtra por rango de fechas
    """
    try:
        return await ConversationService.get_conversation_stats(
            id_agente=id_agente,
            fecha_inicio=fecha_inicio,  # 🔥 PASAR PARÁMETROS
            fecha_fin=fecha_fin  # 🔥 PASAR PARÁMETROS
        )
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )


@router.get(
    "/stats/agent/{id_agente}",
    summary="Estadísticas por agente"
)
async def get_agent_stats(id_agente: int):
    """
    Obtener estadísticas específicas de un agente
    
    Alias conveniente para /stats/overview?id_agente={id}
    """
    try:
        return await ConversationService.get_conversation_stats(id_agente=id_agente)
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas del agente: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )


# ==================== GESTIÓN DE ESTADOS ====================

@router.post(
    "/{session_id}/finalize",
    response_model=ConversationResponse,
    summary="Finalizar conversación"
)
async def finalize_conversation(
    session_id: str,
    calificacion: Optional[int] = Body(None, ge=1, le=5),
    comentario: Optional[str] = Body(None)
):
    """
    Marcar una conversación como finalizada
    
    Opcionalmente se puede agregar calificación y comentario
    """
    try:
        update_data = ConversationUpdate(
            estado=ConversationStatus.finalizada,
            calificacion=calificacion,
            comentario_calificacion=comentario
        )
        return await ConversationService.update_conversation_status(session_id, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error finalizando conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al finalizar conversación: {str(e)}"
        )


@router.post(
    "/{session_id}/escalate",
    response_model=ConversationResponse,
    summary="Escalar a atención humana"
)
async def escalate_conversation(
    session_id: str,
    user_id: int = Body(..., description="ID del agente humano"),
    user_name: str = Body(..., description="Nombre del agente humano")
):
    """
    Escalar una conversación a atención humana
    
    Marca la conversación como escalada y asigna un agente humano
    """
    try:
        update_data = ConversationUpdate(
            estado=ConversationStatus.escalada_humano,
            requirio_atencion_humana=True,
            escalado_a_usuario_id=user_id,
            escalado_a_usuario_nombre=user_name
        )
        return await ConversationService.update_conversation_status(session_id, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error escalando conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al escalar conversación: {str(e)}"
        )


@router.post(
    "/{session_id}/rating",
    response_model=ConversationResponse,
    summary="Calificar conversación"
)
async def rate_conversation(
    session_id: str,
    calificacion: int = Body(..., ge=1, le=5, description="Calificación de 1 a 5"),
    comentario: Optional[str] = Body(None, description="Comentario adicional")
):
    """
    Agregar o actualizar calificación de una conversación
    """
    try:
        update_data = ConversationUpdate(
            calificacion=calificacion,
            comentario_calificacion=comentario
        )
        return await ConversationService.update_conversation_status(session_id, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calificando conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calificar conversación: {str(e)}"
        )


# ==================== UTILIDADES ====================

@router.get(
    "/inactive/list",
    summary="Obtener conversaciones inactivas"
)
async def get_inactive_conversations(
    minutos_inactividad: int = Query(30, ge=1, description="Minutos sin actividad"),
    estados: str = Query("activa", description="Estados a considerar (separados por coma)")
):
    """
    Obtener conversaciones sin actividad reciente
    
    Útil para identificar conversaciones que pueden ser finalizadas automáticamente
    
    **Ejemplo:** 
    - `minutos_inactividad=30` y `estados=activa` 
    - Retorna conversaciones activas sin mensajes en 30 minutos
    """
    try:
        tiempo_limite = datetime.utcnow() - timedelta(minutes=minutos_inactividad)
        
        # Convertir string de estados a lista de enums
        estados_list = [
            ConversationStatus(estado.strip()) 
            for estado in estados.split(",")
        ]
        
        conversations = await ConversationService.get_inactive_conversations(
            tiempo_limite=tiempo_limite,
            estados=estados_list
        )
        
        return {
            "total": len(conversations),
            "minutos_inactividad": minutos_inactividad,
            "tiempo_limite": tiempo_limite,
            "estados_filtrados": estados,
            "conversaciones": conversations
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error obteniendo conversaciones inactivas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener conversaciones inactivas: {str(e)}"
        )


@router.post(
    "/obtain-or-create",
    response_model=ConversationResponse,
    summary="🔥 Obtener conversación activa o crear nueva"
)
async def obtain_or_create_conversation(
    session_id: str = Query(..., description="Session ID único"),
    id_agente: int = Query(..., description="ID del agente"),
    agent_name: str = Query(..., description="Nombre del agente"),
    agent_type: Optional[str] = Query(None, description="Tipo de agente"),
    id_visitante: Optional[int] = Query(None, description="ID del visitante"),
    origin: str = Query("web", description="Origen: web, mobile, widget, api"),
    ip_origen: Optional[str] = Query(None, description="IP del cliente"),
    user_agent: Optional[str] = Query(None, description="User agent")
):
    """
    🔥 **Endpoint inteligente para gestión de sesiones**
    
    Obtiene una conversación activa existente o crea una nueva si:
    - No existe conversación con ese session_id
    - La conversación existente está finalizada/abandonada
    
    **Casos de uso:**
    - Reconectar a una conversación activa después de recarga de página
    - Crear nueva conversación para usuario que vuelve después de finalizar
    - Gestionar sesiones automáticamente sin duplicados
    
    **Comportamiento:**
    - ✅ Si existe y está activa → Retorna la existente
    - 🔄 Si existe pero está finalizada → Crea nueva con timestamp
    - 📝 Si no existe → Crea nueva
    """
    try:
        return await ConversationService.obtener_o_crear_conversacion_activa(
            session_id=session_id,
            id_agente=id_agente,
            agent_name=agent_name,
            agent_type=agent_type,
            id_visitante=id_visitante,
            origin=origin,
            ip_origen=ip_origen,
            user_agent=user_agent
        )
    except Exception as e:
        logger.error(f"Error en obtener_o_crear_conversacion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener o crear conversación: {str(e)}"
        )
    

@router.get(
    "/stats/daily",
    summary="Estadísticas diarias para gráficas"
)
async def get_daily_stats(
    id_agente: Optional[int] = Query(None, description="Filtrar por agente"),
    dias: int = Query(7, ge=1, le=30, description="Número de días (1-30)")
):
    """
    Obtener estadísticas agrupadas por día para gráficas de tendencias
    
    Retorna datos de los últimos N días con:
    - Total de conversaciones por día
    - Conversaciones activas por día
    - Conversaciones finalizadas por día
    - Conversaciones escaladas por día
    """
    try:
        return await ConversationService.get_daily_stats(
            id_agente=id_agente,
            dias=dias
        )
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas diarias: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas diarias: {str(e)}"
        )