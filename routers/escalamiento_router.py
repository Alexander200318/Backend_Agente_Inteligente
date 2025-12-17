# routers/escalamiento_router.py
"""
Endpoints para gestionar conversaciones escaladas a humanos

Estos endpoints permiten:
1. Listar conversaciones escaladas
2. Ver detalles de una conversación
3. Responder como humano
4. Marcar conversación como resuelta
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from database.database import get_db
from services.escalamiento_service import EscalamientoService
from services.conversation_service import ConversationService
# from dependencies.auth import get_current_user  # ← Descomentar cuando tengas auth
# from models.usuario import Usuario  # ← Descomentar cuando tengas auth

router = APIRouter(
    prefix="/escalamiento",
    tags=["Escalamiento a Humanos"]
)


# ============================================
# SCHEMAS
# ============================================

class RespuestaHumanoRequest(BaseModel):
    """Request para responder como humano"""
    mensaje: str
    id_usuario: int  # Temporal: después vendrá del token JWT
    nombre_usuario: str  # Temporal: después vendrá del token JWT


class MarcarResueltoRequest(BaseModel):
    """Request para marcar conversación como resuelta"""
    calificacion: Optional[int] = None  # 1-5
    comentario: Optional[str] = None


# ============================================
# ENDPOINTS
# ============================================

@router.get("/conversaciones-escaladas")
async def listar_conversaciones_escaladas(
    solo_pendientes: bool = True,
    id_departamento: Optional[int] = None,
    db: Session = Depends(get_db),
    # current_user: Usuario = Depends(get_current_user)  # ← Descomentar con auth
):
    """
    Lista conversaciones escaladas pendientes de atención
    
    Query params:
    - solo_pendientes: Solo mostrar no resueltas (default: True)
    - id_departamento: Filtrar por departamento (opcional)
    
    Returns:
        Lista de conversaciones con información básica
    """
    try:
        service = EscalamientoService(db)
        
        # TODO: Cuando tengas auth, usar el departamento del current_user
        # id_depto = current_user.persona.id_departamento if current_user.persona else None
        
        conversaciones_mysql = service.obtener_conversaciones_escaladas(
            id_departamento=id_departamento,
            solo_pendientes=solo_pendientes
        )
        
        # Enriquecer con datos de MongoDB
        conversaciones_completas = []
        
        for conv in conversaciones_mysql:
            try:
                # Obtener detalles de MongoDB
                mongo_conv = await ConversationService.get_conversation_by_session(
                    conv["session_id"]
                )
                
                if mongo_conv:
                    conversaciones_completas.append({
                        **conv,
                        "agent_name": mongo_conv.agent_name,
                        "total_mensajes": mongo_conv.metadata.total_mensajes,
                        "ultimo_mensaje": mongo_conv.messages[-1].content[:100] if mongo_conv.messages else None,
                        "fecha_ultimo_mensaje": mongo_conv.messages[-1].timestamp.isoformat() if mongo_conv.messages else None,
                        "escalado_a": mongo_conv.metadata.escalado_a_usuario_nombre
                    })
                else:
                    conversaciones_completas.append(conv)
                    
            except Exception as e:
                print(f"⚠️ Error enriqueciendo conversación {conv['session_id']}: {e}")
                conversaciones_completas.append(conv)
        
        return {
            "success": True,
            "total": len(conversaciones_completas),
            "conversaciones": conversaciones_completas
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo conversaciones: {str(e)}"
        )


@router.get("/conversacion/{session_id}")
async def obtener_conversacion_detalle(
    session_id: str,
    db: Session = Depends(get_db),
    # current_user: Usuario = Depends(get_current_user)  # ← Descomentar con auth
):
    """
    Obtiene los detalles completos de una conversación escalada
    
    Path params:
    - session_id: ID de la sesión
    
    Returns:
        Conversación completa con todos los mensajes
    """
    try:
        # Obtener de MongoDB
        conversation = await ConversationService.get_conversation_by_session(session_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación {session_id} no encontrada"
            )
        
        # TODO: Verificar que el usuario tenga permiso (mismo departamento)
        
        return {
            "success": True,
            "conversation": conversation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo conversación: {str(e)}"
        )


@router.post("/conversacion/{session_id}/responder")
async def responder_conversacion(
    session_id: str,
    request: RespuestaHumanoRequest,
    db: Session = Depends(get_db),
    # current_user: Usuario = Depends(get_current_user)  # ← Descomentar con auth
):
    """
    Agrega una respuesta de humano a la conversación
    
    Path params:
    - session_id: ID de la sesión
    
    Body:
    - mensaje: Texto de la respuesta
    - id_usuario: ID del usuario (temporal, vendrá del token)
    - nombre_usuario: Nombre del usuario (temporal, vendrá del token)
    
    Returns:
        Confirmación de mensaje agregado
    """
    try:
        service = EscalamientoService(db)
        
        # TODO: Cuando tengas auth, usar current_user
        # id_usuario = current_user.id_usuario
        # nombre_usuario = f"{current_user.persona.nombre} {current_user.persona.apellido}"
        
        resultado = await service.responder_como_humano(
            session_id=session_id,
            mensaje=request.mensaje,
            id_usuario=request.id_usuario,
            nombre_usuario=request.nombre_usuario
        )
        
        return {
            "success": True,
            **resultado
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error respondiendo conversación: {str(e)}"
        )


@router.post("/conversacion/{session_id}/resolver")
async def marcar_como_resuelta(
    session_id: str,
    request: MarcarResueltoRequest,
    db: Session = Depends(get_db),
    # current_user: Usuario = Depends(get_current_user)  # ← Descomentar con auth
):
    """
    Marca una conversación como resuelta y opcionalmente agrega calificación
    
    Path params:
    - session_id: ID de la sesión
    
    Body:
    - calificacion: Calificación 1-5 (opcional)
    - comentario: Comentario adicional (opcional)
    
    Returns:
        Confirmación
    """
    try:
        from models.conversation_mongo import ConversationUpdate, ConversationStatus
        from models.conversacion_sync import ConversacionSync, EstadoConversacionEnum
        
        # Actualizar en MongoDB
        update_data = ConversationUpdate(
            estado=ConversationStatus.finalizada,
            calificacion=request.calificacion,
            comentario_calificacion=request.comentario
        )
        
        conversation = await ConversationService.update_conversation_status(
            session_id, 
            update_data
        )
        
        # Actualizar en MySQL
        conv_sync = db.query(ConversacionSync).filter(
            ConversacionSync.mongodb_conversation_id == session_id
        ).first()
        
        if conv_sync:
            conv_sync.estado = EstadoConversacionEnum.finalizada
            conv_sync.fecha_fin = datetime.utcnow()
            db.commit()
        
        return {
            "success": True,
            "session_id": session_id,
            "estado": "finalizada",
            "calificacion": request.calificacion
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marcando como resuelta: {str(e)}"
        )


@router.get("/mis-notificaciones")
async def obtener_mis_notificaciones(
    solo_no_leidas: bool = True,
    limit: int = 20,
    db: Session = Depends(get_db),
    # current_user: Usuario = Depends(get_current_user)  # ← Descomentar con auth
):
    """
    Obtiene las notificaciones del usuario actual
    
    Query params:
    - solo_no_leidas: Solo mostrar no leídas (default: True)
    - limit: Número máximo de notificaciones (default: 20)
    
    Returns:
        Lista de notificaciones
    """
    try:
        from models.notificacion_usuario import NotificacionUsuario
        
        # TODO: Cuando tengas auth, usar current_user.id_usuario
        # Por ahora, usar un ID de prueba o parametrizable
        id_usuario = 1  # ← Cambiar cuando tengas auth
        
        query = db.query(NotificacionUsuario).filter(
            NotificacionUsuario.id_usuario == id_usuario
        )
        
        if solo_no_leidas:
            query = query.filter(NotificacionUsuario.leida == False)
        
        notificaciones = query.order_by(
            NotificacionUsuario.fecha_creacion.desc()
        ).limit(limit).all()
        
        return {
            "success": True,
            "total": len(notificaciones),
            "notificaciones": [
                {
                    "id": n.id_notificacion,
                    "tipo": n.tipo,
                    "titulo": n.titulo,
                    "mensaje": n.mensaje,
                    "url_accion": n.url_accion,
                    "leida": n.leida,
                    "fecha_creacion": n.fecha_creacion.isoformat() if n.fecha_creacion else None
                }
                for n in notificaciones
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo notificaciones: {str(e)}"
        )


@router.post("/notificacion/{id_notificacion}/marcar-leida")
async def marcar_notificacion_leida(
    id_notificacion: int,
    db: Session = Depends(get_db),
    # current_user: Usuario = Depends(get_current_user)  # ← Descomentar con auth
):
    """
    Marca una notificación como leída
    
    Path params:
    - id_notificacion: ID de la notificación
    
    Returns:
        Confirmación
    """
    try:
        from models.notificacion_usuario import NotificacionUsuario
        from datetime import datetime
        
        notificacion = db.query(NotificacionUsuario).filter(
            NotificacionUsuario.id_notificacion == id_notificacion
        ).first()
        
        if not notificacion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notificación no encontrada"
            )
        
        notificacion.leida = True
        notificacion.fecha_lectura = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "id_notificacion": id_notificacion,
            "leida": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marcando notificación: {str(e)}"
        )
