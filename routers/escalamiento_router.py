# routers/escalamiento_router.py
"""
Endpoints para gestionar conversaciones escaladas a humanos

Estos endpoints permiten:
1. Listar conversaciones escaladas (globales y personales)
2. Ver detalles de una conversación
3. Responder como humano con WebSocket broadcast
4. Marcar conversación como resuelta
5. Gestionar notificaciones
6. Estadísticas de atención
7. Transferir conversación a otro funcionario
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from database.database import get_db
from services.escalamiento_service import EscalamientoService
from services.conversation_service import ConversationService
from models.conversacion_sync import ConversacionSync, EstadoConversacionEnum
from models.conversation_mongo import ConversationUpdate, ConversationStatus, MessageRole
from models.notificacion_usuario import NotificacionUsuario
from models.usuario import Usuario
from models.persona import Persona
from models.agente_virtual import AgenteVirtual
# from dependencies.auth import get_current_user  # ← Descomentar cuando tengas auth

import logging
logger = logging.getLogger(__name__)


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
    calificacion: Optional[int] = Field(None, ge=1, le=5)
    comentario: Optional[str] = None
    tiempo_resolucion_minutos: Optional[int] = None


class TransferirConversacionRequest(BaseModel):
    """Request para transferir conversación a otro funcionario"""
    id_usuario_destino: int
    motivo: Optional[str] = "Transferencia de conversación"


class TomarConversacionRequest(BaseModel):
    """Request para que un funcionario tome una conversación"""
    id_usuario: int
    nombre_usuario: str


# ============================================
# ENDPOINTS - LISTAR CONVERSACIONES
# ============================================

@router.get("/conversaciones-escaladas")
async def listar_conversaciones_escaladas(
    solo_pendientes: bool = True,
    id_departamento: Optional[int] = None,
    estado: Optional[str] = None,
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    # current_user: Usuario = Depends(get_current_user)  # ← Descomentar con auth
):
    """
    Lista TODAS las conversaciones escaladas del departamento
    
    Query params:
    - solo_pendientes: Solo mostrar no resueltas (default: True)
    - id_departamento: Filtrar por departamento (opcional)
    - estado: Filtrar por estado específico (opcional)
    - limite: Número máximo de resultados
    
    Returns:
        Lista de conversaciones con información completa
    """
    try:
        service = EscalamientoService(db)
        
        conversaciones_mysql = service.obtener_conversaciones_escaladas(
            id_departamento=id_departamento,
            solo_pendientes=solo_pendientes
        )
        
        # Enriquecer con datos de MongoDB
        conversaciones_completas = []
        
        for conv in conversaciones_mysql[:limite]:
            try:
                mongo_conv = await ConversationService.get_conversation_by_session(
                    conv["session_id"]
                )
                
                if mongo_conv:
                    # Calcular tiempo de espera
                    tiempo_espera = None
                    if mongo_conv.metadata.fecha_escalamiento:
                        tiempo_espera = (datetime.utcnow() - mongo_conv.metadata.fecha_escalamiento).total_seconds() / 60
                    
                    conversaciones_completas.append({
                        **conv,
                        "agent_name": mongo_conv.agent_name,
                        "total_mensajes": mongo_conv.metadata.total_mensajes,
                        "ultimo_mensaje": mongo_conv.messages[-1].content[:150] if mongo_conv.messages else None,
                        "fecha_ultimo_mensaje": mongo_conv.messages[-1].timestamp.isoformat() if mongo_conv.messages else None,
                        "escalado_a_usuario_id": mongo_conv.metadata.escalado_a_usuario_id,
                        "escalado_a_usuario_nombre": mongo_conv.metadata.escalado_a_usuario_nombre,
                        "tiempo_espera_minutos": round(tiempo_espera, 1) if tiempo_espera else None,
                        "prioridad": "alta" if tiempo_espera and tiempo_espera > 30 else "normal"
                    })
                else:
                    conversaciones_completas.append(conv)
                    
            except Exception as e:
                logger.warning(f"⚠️ Error enriqueciendo conversación {conv['session_id']}: {e}")
                conversaciones_completas.append(conv)
        
        return {
            "success": True,
            "total": len(conversaciones_completas),
            "conversaciones": conversaciones_completas
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo conversaciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo conversaciones: {str(e)}"
        )






@router.get("/mis-conversaciones")
async def listar_mis_conversaciones(
    id_usuario: int = Query(..., description="ID del funcionario"),
    solo_activas: bool = True,
    limite: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Lista conversaciones asignadas a UN funcionario específico
    """
    try:
        logger.info(f"🔍 Buscando conversaciones para usuario {id_usuario}")
        
        from services.mongo_connection import get_conversations_by_user
        
        conversaciones_mongo = await get_conversations_by_user(
            user_id=id_usuario,
            solo_activas=solo_activas,
            limit=limite
        )
        
        logger.info(f"✅ Encontradas {len(conversaciones_mongo)} conversaciones")
        
        mis_conversaciones = []
        
        for mongo_conv in conversaciones_mongo:
            try:
                # Calcular métricas
                tiempo_desde_escalamiento = None
                if mongo_conv.metadata.fecha_escalamiento:
                    tiempo_desde_escalamiento = (
                        datetime.utcnow() - mongo_conv.metadata.fecha_escalamiento
                    ).total_seconds() / 60
                
                tiempo_desde_ultima_respuesta = None
                if mongo_conv.messages:
                    ultimo_msg = mongo_conv.messages[-1]
                    tiempo_desde_ultima_respuesta = (
                        datetime.utcnow() - ultimo_msg.timestamp
                    ).total_seconds() / 60
                
                # Buscar info en MySQL
                conv_sync = db.query(ConversacionSync).filter(
                    ConversacionSync.mongodb_conversation_id == mongo_conv.session_id
                ).first()
                
                # 🔥 FIX: Manejar role que puede ser str o Enum
                ultimo_mensaje_role = None
                if mongo_conv.messages:
                    role = mongo_conv.messages[-1].role
                    # Si ya es string, úsalo; si es Enum, obtén el value
                    ultimo_mensaje_role = role if isinstance(role, str) else role.value
                
                mis_conversaciones.append({
                    "id_conversacion_sync": conv_sync.id_conversacion_sync if conv_sync else None,
                    "session_id": mongo_conv.session_id,
                    "id_agente": mongo_conv.id_agente,
                    "agent_name": mongo_conv.agent_name,
                    "estado": mongo_conv.metadata.estado,
                    "total_mensajes": mongo_conv.metadata.total_mensajes,
                    "ultimo_mensaje": mongo_conv.messages[-1].content[:150] if mongo_conv.messages else None,
                    "ultimo_mensaje_de": ultimo_mensaje_role,  # 🔥 CAMBIADO
                    "fecha_ultimo_mensaje": mongo_conv.messages[-1].timestamp.isoformat() if mongo_conv.messages else None,
                    "fecha_escalamiento": mongo_conv.metadata.fecha_escalamiento.isoformat() if mongo_conv.metadata.fecha_escalamiento else None,
                    "escalado_a_usuario_id": mongo_conv.metadata.escalado_a_usuario_id,
                    "escalado_a_usuario_nombre": mongo_conv.metadata.escalado_a_usuario_nombre,
                    "tiempo_espera_minutos": round(tiempo_desde_escalamiento, 1) if tiempo_desde_escalamiento else None,
                    "tiempo_sin_respuesta_minutos": round(tiempo_desde_ultima_respuesta, 1) if tiempo_desde_ultima_respuesta else None,
                    "requiere_atencion": tiempo_desde_ultima_respuesta and tiempo_desde_ultima_respuesta > 10,
                    "prioridad": "alta" if (tiempo_desde_ultima_respuesta and tiempo_desde_ultima_respuesta > 30) else "normal"
                })
                
            except Exception as e:
                logger.warning(f"⚠️ Error procesando conversación {mongo_conv.session_id}: {e}")
        
        return {
            "success": True,
            "total": len(mis_conversaciones),
            "id_usuario": id_usuario,
            "conversaciones": mis_conversaciones
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo mis conversaciones: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo conversaciones: {str(e)}"
        )








# ============================================
# ENDPOINTS - DETALLES Y ACCIONES
# ============================================

@router.get("/conversacion/{session_id}")
async def obtener_conversacion_detalle(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene los detalles completos de una conversación escalada
    
    Path params:
    - session_id: ID de la sesión
    
    Returns:
        Conversación completa con todos los mensajes y metadata
    """
    try:
        # Obtener de MongoDB
        conversation = await ConversationService.get_conversation_by_session(session_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación {session_id} no encontrada"
            )
        
        # Obtener info adicional de MySQL
        conv_sync = db.query(ConversacionSync).filter(
            ConversacionSync.mongodb_conversation_id == session_id
        ).first()
        
        # Obtener info del agente
        agente = db.query(AgenteVirtual).filter(
            AgenteVirtual.id_agente == conversation.id_agente
        ).first()
        
        return {
            "success": True,
            "conversation": conversation,
            "sync_info": {
                "id_conversacion_sync": conv_sync.id_conversacion_sync if conv_sync else None,
                "estado_mysql": conv_sync.estado.value if conv_sync else None,
                "fecha_inicio": conv_sync.fecha_inicio.isoformat() if conv_sync and conv_sync.fecha_inicio else None,
                "fecha_fin": conv_sync.fecha_fin.isoformat() if conv_sync and conv_sync.fecha_fin else None
            },
            "agente_info": {
                "nombre": agente.nombre_agente if agente else None,
                "tipo": agente.tipo_agente if agente else None,
                "departamento_id": agente.id_departamento if agente else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo conversación: {str(e)}"
        )


@router.post("/conversacion/{session_id}/tomar")
async def tomar_conversacion(
    session_id: str,
    request: TomarConversacionRequest,
    db: Session = Depends(get_db)
):
    """
    🔥 NUEVO: Funcionario "toma" una conversación sin asignar
    
    Path params:
    - session_id: ID de la sesión
    
    Body:
    - id_usuario: ID del funcionario
    - nombre_usuario: Nombre del funcionario
    
    Returns:
        Confirmación de asignación
    """
    try:
        # Verificar que la conversación existe y no está asignada
        mongo_conv = await ConversationService.get_conversation_by_session(session_id)
        
        if not mongo_conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada"
            )
        
        # Verificar si ya está asignada
        if mongo_conv.metadata.escalado_a_usuario_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Conversación ya asignada a {mongo_conv.metadata.escalado_a_usuario_nombre}"
            )
        
        # Asignar al funcionario
        update_data = ConversationUpdate(
            escalado_a_usuario_id=request.id_usuario,
            escalado_a_usuario_nombre=request.nombre_usuario
        )
        
        await ConversationService.update_conversation(session_id, update_data)
        
        # Agregar mensaje de sistema
        from models.conversation_mongo import MessageCreate
        mensaje_sistema = MessageCreate(
            role=MessageRole.system,
            content=f"🙋 {request.nombre_usuario} ha tomado esta conversación"
        )
        await ConversationService.add_message(session_id, mensaje_sistema)
        
        logger.info(f"✅ Conversación {session_id} tomada por {request.nombre_usuario}")
        
        return {
            "success": True,
            "session_id": session_id,
            "asignado_a": request.nombre_usuario,
            "mensaje": "Conversación asignada correctamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error tomando conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@router.post("/conversacion/{session_id}/responder")
async def responder_conversacion(
    session_id: str,
    request: RespuestaHumanoRequest,
    db: Session = Depends(get_db)
):
    """
    Humano responde a conversación escalada con WebSocket broadcast
    """
    try:
        # 🔥 LOG COMPLETO
        logger.info(f"=" * 80)
        logger.info(f"📝 ENDPOINT /responder llamado")
        logger.info(f"   - session_id: {session_id}")
        logger.info(f"   - mensaje: {request.mensaje[:50]}...")
        logger.info(f"   - id_usuario: {request.id_usuario}")
        logger.info(f"   - nombre_usuario: '{request.nombre_usuario}'")
        logger.info(f"=" * 80)
        
        # 🔥 Si nombre_usuario está vacío, buscar en BD
        nombre_final = request.nombre_usuario
        if not nombre_final or nombre_final.strip() == "":
            logger.warning(f"⚠️ nombre_usuario vacío, buscando en BD...")
            usuario = db.query(Usuario).join(Persona).filter(
                Usuario.id_usuario == request.id_usuario
            ).first()
            
            if usuario and usuario.persona:
                nombre_final = f"{usuario.persona.nombres} {usuario.persona.primer_apellido}"
                logger.info(f"✅ Nombre obtenido de BD: '{nombre_final}'")
            else:
                nombre_final = "Agente Humano"
                logger.warning(f"⚠️ Usuario no encontrado, usando fallback")
        
        escalamiento_service = EscalamientoService(db)
        
        resultado = await escalamiento_service.responder_como_humano(
            session_id=session_id,
            mensaje=request.mensaje,
            id_usuario=request.id_usuario,
            nombre_usuario=nombre_final  # 🔥 Usar nombre final
        )
        
        if resultado["success"]:
            # 🔥 WEBSOCKET BROADCAST
            try:
                from services.websocket_manager import manager
                
                broadcast_data = {
                    "type": "message",
                    "role": "human_agent",
                    "content": request.mensaje,
                    "user_id": request.id_usuario,
                    "user_name": nombre_final,  # 🔥 Usar nombre final
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                logger.info(f"📡 Broadcasting data: {broadcast_data}")
                
                await manager.broadcast(broadcast_data, session_id)
                
                logger.info(f"✅ Broadcast exitoso para session {session_id}")
                broadcast_success = True
                
            except Exception as ws_error:
                logger.error(f"❌ Error en WebSocket broadcast: {ws_error}")
                import traceback
                logger.error(traceback.format_exc())
                broadcast_success = False
            
            return {
                "ok": True,
                "message": "Respuesta enviada correctamente",
                "total_mensajes": resultado.get("total_mensajes"),
                "broadcast": broadcast_success,
                "nombre_usado": nombre_final  # 🔥 Para debug
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error enviando respuesta"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en responder_conversacion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/conversacion/{session_id}/transferir")
async def transferir_conversacion(
    session_id: str,
    request: TransferirConversacionRequest,
    db: Session = Depends(get_db)
):
    """
    🔥 NUEVO: Transferir conversación a otro funcionario
    
    Path params:
    - session_id: ID de la sesión
    
    Body:
    - id_usuario_destino: ID del funcionario destino
    - motivo: Motivo de la transferencia
    
    Returns:
        Confirmación de transferencia
    """
    try:
        # Verificar que el usuario destino existe
        usuario_destino = db.query(Usuario).join(Persona).filter(
            Usuario.id_usuario == request.id_usuario_destino,
            Usuario.estado == 'activo'
        ).first()
        
        if not usuario_destino:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario destino no encontrado o inactivo"
            )
        
        # Obtener nombre completo
        nombre_destino = f"{usuario_destino.persona.nombres} {usuario_destino.persona.primer_apellido}"
        
        # Actualizar asignación en MongoDB
        update_data = ConversationUpdate(
            escalado_a_usuario_id=request.id_usuario_destino,
            escalado_a_usuario_nombre=nombre_destino
        )
        
        await ConversationService.update_conversation(session_id, update_data)
        
        # Agregar mensaje de sistema
        from models.conversation_mongo import MessageCreate
        mensaje_sistema = MessageCreate(
            role=MessageRole.system,
            content=f"🔄 Conversación transferida a {nombre_destino}. Motivo: {request.motivo}"
        )
        await ConversationService.add_message(session_id, mensaje_sistema)
        
        # Crear notificación para el usuario destino
        from models.notificacion_usuario import TipoNotificacionEnum
        
        mongo_conv = await ConversationService.get_conversation_by_session(session_id)
        
        notificacion = NotificacionUsuario(
            id_usuario=request.id_usuario_destino,
            id_agente=mongo_conv.id_agente if mongo_conv else None,
            tipo=TipoNotificacionEnum.urgente,
            titulo='Conversación transferida a ti',
            mensaje=f'Se te ha transferido una conversación. Motivo: {request.motivo}',
            icono='arrow-right-circle',
            url_accion=f'/conversaciones-escaladas/{session_id}',
            datos_adicionales=f'{{"session_id": "{session_id}", "motivo": "{request.motivo}"}}',
            leida=False,
            fecha_creacion=datetime.utcnow()
        )
        
        db.add(notificacion)
        db.commit()
        
        logger.info(f"✅ Conversación {session_id} transferida a usuario {request.id_usuario_destino}")
        
        return {
            "success": True,
            "session_id": session_id,
            "transferido_a": nombre_destino,
            "id_usuario_destino": request.id_usuario_destino,
            "mensaje": "Conversación transferida correctamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error transfiriendo conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@router.post("/conversacion/{session_id}/resolver")
async def marcar_como_resuelta(
    session_id: str,
    request: MarcarResueltoRequest,
    db: Session = Depends(get_db)
):
    """
    Marca una conversación como resuelta con calificación opcional
    
    Path params:
    - session_id: ID de la sesión
    
    Body:
    - calificacion: Calificación 1-5 (opcional)
    - comentario: Comentario adicional (opcional)
    - tiempo_resolucion_minutos: Tiempo que tomó resolver (opcional)
    
    Returns:
        Confirmación
    """
    try:
        # Actualizar en MongoDB
        update_data = ConversationUpdate(
            estado=ConversationStatus.finalizada,
            calificacion=request.calificacion,
            comentario_calificacion=request.comentario
        )
        
        conversation = await ConversationService.update_conversation(
            session_id, 
            update_data
        )
        
        # Agregar mensaje de cierre
        from models.conversation_mongo import MessageCreate
        mensaje_cierre = f"✅ Conversación marcada como resuelta"
        if request.calificacion:
            mensaje_cierre += f" - Calificación: {request.calificacion}/5"
        if request.comentario:
            mensaje_cierre += f"\nComentario: {request.comentario}"
        
        mensaje_sistema = MessageCreate(
            role=MessageRole.system,
            content=mensaje_cierre
        )
        await ConversationService.add_message(session_id, mensaje_sistema)
        
        # Actualizar en MySQL
        conv_sync = db.query(ConversacionSync).filter(
            ConversacionSync.mongodb_conversation_id == session_id
        ).first()
        
        if conv_sync:
            conv_sync.estado = EstadoConversacionEnum.finalizada
            conv_sync.fecha_fin = datetime.utcnow()
            conv_sync.ultima_sincronizacion = datetime.utcnow()
            db.commit()
        
        logger.info(f"✅ Conversación {session_id} marcada como resuelta")
        
        return {
            "success": True,
            "session_id": session_id,
            "estado": "finalizada",
            "calificacion": request.calificacion,
            "tiempo_resolucion_minutos": request.tiempo_resolucion_minutos
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error marcando como resuelta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


# ============================================
# ENDPOINTS - ESTADÍSTICAS
# ============================================

@router.get("/estadisticas")
async def obtener_estadisticas_generales(
    id_departamento: Optional[int] = None,
    dias: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    🔥 NUEVO: Estadísticas generales de escalamiento
    
    Query params:
    - id_departamento: Filtrar por departamento (opcional)
    - dias: Últimos N días (default: 7)
    
    Returns:
        Estadísticas completas
    """
    try:
        fecha_desde = datetime.utcnow() - timedelta(days=dias)
        
        # Query base
        query = db.query(ConversacionSync).filter(
            ConversacionSync.fecha_inicio >= fecha_desde
        )
        
        if id_departamento:
            query = query.join(
                AgenteVirtual,
                ConversacionSync.id_agente_inicial == AgenteVirtual.id_agente
            ).filter(
                AgenteVirtual.id_departamento == id_departamento
            )
        
        conversaciones = query.all()
        
        # Calcular métricas
        total = len(conversaciones)
        escaladas = len([c for c in conversaciones if c.requirio_atencion_humana])
        resueltas = len([c for c in conversaciones if c.estado == EstadoConversacionEnum.finalizada])
        pendientes = len([c for c in conversaciones if c.estado == EstadoConversacionEnum.escalada_humano])
        
        # Tiempo promedio de resolución
        tiempos_resolucion = []
        for c in conversaciones:
            if c.fecha_inicio and c.fecha_fin:
                tiempo = (c.fecha_fin - c.fecha_inicio).total_seconds() / 60
                tiempos_resolucion.append(tiempo)
        
        tiempo_promedio = sum(tiempos_resolucion) / len(tiempos_resolucion) if tiempos_resolucion else 0
        
        return {
            "success": True,
            "periodo": {
                "desde": fecha_desde.isoformat(),
                "hasta": datetime.utcnow().isoformat(),
                "dias": dias
            },
            "estadisticas": {
                "total_conversaciones": total,
                "conversaciones_escaladas": escaladas,
                "conversaciones_resueltas": resueltas,
                "conversaciones_pendientes": pendientes,
                "tiempo_promedio_resolucion_minutos": round(tiempo_promedio, 1),
                "tasa_resolucion": round((resueltas / escaladas * 100) if escaladas > 0 else 0, 1)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@router.get("/mis-estadisticas")
async def obtener_mis_estadisticas(
    id_usuario: int = Query(..., description="ID del funcionario"),
    dias: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    🔥 NUEVO: Estadísticas personales de un funcionario
    
    Query params:
    - id_usuario: ID del funcionario (obligatorio)
    - dias: Últimos N días (default: 7)
    
    Returns:
        Estadísticas del funcionario
    """
    try:
        fecha_desde = datetime.utcnow() - timedelta(days=dias)
        
        # Obtener conversaciones del funcionario desde MongoDB
        conversaciones_mysql = db.query(ConversacionSync).filter(
            ConversacionSync.fecha_inicio >= fecha_desde
        ).all()
        
        mis_conversaciones = []
        for conv_sync in conversaciones_mysql:
            try:
                mongo_conv = await ConversationService.get_conversation_by_session(
                    conv_sync.mongodb_conversation_id
                )
                
                if mongo_conv and mongo_conv.metadata.escalado_a_usuario_id == id_usuario:
                    mis_conversaciones.append({
                        "sync": conv_sync,
                        "mongo": mongo_conv
                    })
            except:
                continue
        
        # Calcular métricas
        total = len(mis_conversaciones)
        resueltas = len([c for c in mis_conversaciones if c["sync"].estado == EstadoConversacionEnum.finalizada])
        pendientes = len([c for c in mis_conversaciones if c["sync"].estado == EstadoConversacionEnum.escalada_humano])
        
        # Tiempo promedio
        tiempos = []
        for c in mis_conversaciones:
            if c["sync"].fecha_inicio and c["sync"].fecha_fin:
                tiempo = (c["sync"].fecha_fin - c["sync"].fecha_inicio).total_seconds() / 60
                tiempos.append(tiempo)
        
        tiempo_promedio = sum(tiempos) / len(tiempos) if tiempos else 0
        
        # Calificación promedio
        calificaciones = [
            c["mongo"].metadata.calificacion 
            for c in mis_conversaciones 
            if c["mongo"].metadata.calificacion
        ]
        calificacion_promedio = sum(calificaciones) / len(calificaciones) if calificaciones else None
        
        return {
            "success": True,
            "id_usuario": id_usuario,
            "periodo": {
                "desde": fecha_desde.isoformat(),
                "hasta": datetime.utcnow().isoformat(),
                "dias": dias
            },
            "estadisticas": {
                "total_conversaciones_atendidas": total,
                "conversaciones_resueltas": resueltas,
                "conversaciones_pendientes": pendientes,
                "tiempo_promedio_resolucion_minutos": round(tiempo_promedio, 1),
                "calificacion_promedio": round(calificacion_promedio, 2) if calificacion_promedio else None,
                "tasa_resolucion": round((resueltas / total * 100) if total > 0 else 0, 1)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo mis estadísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


# ============================================
# ENDPOINTS - NOTIFICACIONES
# ============================================

@router.get("/mis-notificaciones")
async def obtener_mis_notificaciones(
    id_usuario: int = Query(..., description="ID del funcionario"),
    solo_no_leidas: bool = True,
    limite: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Obtiene las notificaciones del funcionario
    
    Query params:
    - id_usuario: ID del funcionario (obligatorio)
    - solo_no_leidas: Solo mostrar no leídas (default: True)
    - limite: Número máximo de notificaciones
    
    Returns:
        Lista de notificaciones
    """
    try:
        query = db.query(NotificacionUsuario).filter(
            NotificacionUsuario.id_usuario == id_usuario
        )
        
        if solo_no_leidas:
            query = query.filter(NotificacionUsuario.leida == False)
        
        notificaciones = query.order_by(
            NotificacionUsuario.fecha_creacion.desc()
        ).limit(limite).all()
        
        return {
            "success": True,
            "total": len(notificaciones),
            "no_leidas": len([n for n in notificaciones if not n.leida]),
            "notificaciones": [
                {
                    "id": n.id_notificacion,
                    "tipo": n.tipo.value if hasattr(n.tipo, 'value') else n.tipo,
                    "titulo": n.titulo,
                    "mensaje": n.mensaje,
                    "icono": n.icono,
                    "url_accion": n.url_accion,
                    "leida": n.leida,
                    "fecha_creacion": n.fecha_creacion.isoformat() if n.fecha_creacion else None,
                    "fecha_lectura": n.fecha_lectura.isoformat() if n.fecha_lectura else None
                }
                for n in notificaciones
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo notificaciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@router.post("/notificacion/{id_notificacion}/marcar-leida")
async def marcar_notificacion_leida(
    id_notificacion: int,
    db: Session = Depends(get_db)
):
    """
    Marca una notificación como leída
    
    Path params:
    - id_notificacion: ID de la notificación
    
    Returns:
        Confirmación
    """
    try:
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
        logger.error(f"❌ Error marcando notificación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@router.post("/notificaciones/marcar-todas-leidas")
async def marcar_todas_leidas(
    id_usuario: int = Query(..., description="ID del funcionario"),
    db: Session = Depends(get_db)
):
    """
    🔥 NUEVO: Marca todas las notificaciones del usuario como leídas
    
    Query params:
    - id_usuario: ID del funcionario
    
    Returns:
        Número de notificaciones marcadas
    """
    try:
        resultado = db.query(NotificacionUsuario).filter(
            NotificacionUsuario.id_usuario == id_usuario,
            NotificacionUsuario.leida == False
        ).update({
            "leida": True,
            "fecha_lectura": datetime.utcnow()
        })
        
        db.commit()
        
        return {
            "success": True,
            "notificaciones_actualizadas": resultado
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error marcando todas como leídas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


# ============================================
# ENDPOINTS - UTILIDADES
# ============================================

@router.get("/funcionarios-disponibles")
async def listar_funcionarios_disponibles(
    id_departamento: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    🔥 NUEVO: Lista funcionarios disponibles para transferencia
    
    Query params:
    - id_departamento: Filtrar por departamento (opcional)
    
    Returns:
        Lista de funcionarios
    """
    try:
        from models.usuario_rol import UsuarioRol
        from models.rol import Rol
        
        query = db.query(Usuario).join(Persona).join(
            UsuarioRol, Usuario.id_usuario == UsuarioRol.id_usuario
        ).join(
            Rol, UsuarioRol.id_rol == Rol.id_rol
        ).filter(
            Usuario.estado == 'activo',
            Persona.estado == 'activo',
            UsuarioRol.activo == True,
            Rol.nivel_jerarquia == 3  # Solo funcionarios
        )
        
        if id_departamento:
            query = query.filter(Persona.id_departamento == id_departamento)
        
        funcionarios = query.distinct().all()
        
        return {
            "success": True,
            "total": len(funcionarios),
            "funcionarios": [
                {
                    "id_usuario": f.id_usuario,
                    "username": f.username,
                    "nombre_completo": f"{f.persona.nombres} {f.persona.primer_apellido}",
                    "email": f.email,
                    "id_departamento": f.persona.id_departamento if f.persona else None
                }
                for f in funcionarios
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo funcionarios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )