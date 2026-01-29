# routers/chat_router.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database.database import get_db 
from pydantic import BaseModel
from groq_service.groq_agent_service import GroqAgentService
from services.escalamiento_service import EscalamientoService
from services.conversation_service import ConversationService, ConversationCreate
from models.agente_virtual import AgenteVirtual
from utils.json_utils import safe_json_dumps
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

class ClientInfo(BaseModel):
    """Información del cliente/navegador"""
    user_agent: str
    dispositivo: str
    navegador: str
    sistema_operativo: str
    pantalla: Optional[Dict[str, int]] = None
    idioma: Optional[str] = None

class ChatRequest(BaseModel):
    agent_id: int
    message: str
    session_id: str
    origin: Optional[str] = "web"
    client_info: Optional[ClientInfo] = None
    k: Optional[int] = None
    use_reranking: Optional[bool] = None
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None

@router.post("/agent")
def chat_with_agent(
    request: Request,
    payload: ChatRequest, 
    db: Session = Depends(get_db)
):
    service = GroqAgentService(db)
    
    ip_origen = request.client.host if request.client else None
    user_agent = payload.client_info.user_agent if payload.client_info else request.headers.get("user-agent")
    dispositivo = payload.client_info.dispositivo if payload.client_info else None
    navegador = payload.client_info.navegador if payload.client_info else None
    sistema_operativo = payload.client_info.sistema_operativo if payload.client_info else None
    
    try:
        res = service.chat_with_agent(
            id_agente=payload.agent_id,
            pregunta=payload.message,
            session_id=payload.session_id,
            origin=payload.origin,
            ip_origen=ip_origen,
            user_agent=user_agent,
            dispositivo=dispositivo,
            navegador=navegador,
            sistema_operativo=sistema_operativo,
            k=payload.k,
            use_reranking=payload.use_reranking,
            temperatura=payload.temperatura,
            max_tokens=payload.max_tokens
        )
        return res
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/stream")
async def chat_with_agent_stream(
    request: Request,
    payload: ChatRequest, 
    db: Session = Depends(get_db)
):
    """
    Chat con streaming y sistema de confirmación de escalamiento
    
    🔥 FLUJO DE ESCALAMIENTO:
    1. Usuario dice "quiero hablar con humano"
    2. Sistema solicita confirmación + advierte sobre registro
    3. Usuario confirma o rechaza
    4. Si confirma → escala
    5. Si rechaza → continúa con IA
    """
    service = GroqAgentService(db)
    escalamiento_service = EscalamientoService(db)
    
    ip_origen = request.client.host if request.client else None
    user_agent = payload.client_info.user_agent if payload.client_info else request.headers.get("user-agent")
    dispositivo = payload.client_info.dispositivo if payload.client_info else None
    navegador = payload.client_info.navegador if payload.client_info else None
    sistema_operativo = payload.client_info.sistema_operativo if payload.client_info else None
    
    async def event_generator():
        print("🚀🚀🚀 EVENT_GENERATOR INICIADO 🚀🚀🚀")
        print(f"Session: {payload.session_id}")
        print(f"Mensaje: '{payload.message}'")
        last_event_time = datetime.now()
        heartbeat_interval = 15
        
        # 🔥 INICIALIZAR VARIABLES
        conversation = None
        agente = None
        
        try:

            # ============================================
            # 🔥 PASO -1: VERIFICAR SI HAY VISITANTE REGISTRADO
            # ============================================
            visitante_registrado = False
            id_visitante = None

            try:
                from services.visitante_anonimo_service import VisitanteAnonimoService
                visitante_service = VisitanteAnonimoService(db)
                visitante = visitante_service.obtener_por_sesion(payload.session_id)
                visitante_registrado = True
                id_visitante = visitante.id_visitante
                logger.info(f"✅ Visitante registrado encontrado: {id_visitante}")
            except:
                logger.info(f"⚠️ No hay visitante registrado (primeros 3 mensajes)")
                visitante_registrado = False

            # Solo crear conversación SI hay visitante registrado# Solo crear conversación SI hay visitante registrado
            if visitante_registrado:
                try:
                    # Obtener agente
                    agente = db.query(AgenteVirtual).filter(
                        AgenteVirtual.id_agente == payload.agent_id
                    ).first()
                    
                    if not agente:
                        yield f"data: {safe_json_dumps({'type': 'error', 'content': f'Agente {payload.agent_id} no encontrado'})}\n\n"
                        return
                    
                    # 🔥 AGREGAR LOG DE AGENTE:
                    logger.info(f"🤖 AGENTE SELECCIONADO")
                    logger.info(f"   - ID: {agente.id_agente}")
                    logger.info(f"   - Nombre: {agente.nombre_agente}")
                    logger.info(f"   - Tipo: {agente.tipo_agente}")
                    logger.info(f"   - Departamento: {agente.id_departamento}")
        
                    # Verificar si ya existe conversación
                    conversation = await ConversationService.get_conversation_by_session(payload.session_id)

                    # 🔥 AGREGAR LOG DE VERIFICACIÓN:
                    if conversation:
                        logger.info(f"=" * 80)
                        logger.info(f"♻️ CONVERSACIÓN EXISTENTE ENCONTRADA")
                        logger.info(f"   - MongoDB ID: {conversation.id}")
                        logger.info(f"   - Session ID: {conversation.session_id}")
                        logger.info(f"   - ID Visitante: {conversation.id_visitante}")
                        logger.info(f"   - Total mensajes: {conversation.metadata.total_mensajes}")
                        logger.info(f"   - Estado: {conversation.metadata.estado}")
                        logger.info(f"   - Creada: {conversation.created_at}")
                        logger.info(f"=" * 80)
                    
                    if not conversation:
                        # 🔥 AGREGAR LOG ANTES DE CREAR:
                        logger.info(f"=" * 80)
                        logger.info(f"📝 CREANDO NUEVA CONVERSACIÓN")
                        logger.info(f"   - Session ID: {payload.session_id}")
                        logger.info(f"   - ID Visitante: {id_visitante}")
                        logger.info(f"   - ID Agente: {payload.agent_id}")
                        logger.info(f"   - Nombre Agente: {agente.nombre_agente}")
                        logger.info(f"   - Tipo Agente: {agente.tipo_agente}")
                        logger.info(f"   - Origin: {payload.origin}")
                        logger.info(f"   - IP Origen: {ip_origen}")
                        logger.info(f"=" * 80)
                        
                        conversation_data = ConversationCreate(
                            session_id=payload.session_id,
                            id_agente=payload.agent_id,
                            agent_name=agente.nombre_agente,
                            agent_type=agente.tipo_agente,
                            id_visitante=id_visitante,
                            origin=payload.origin,
                            ip_origen=ip_origen,
                            user_agent=user_agent
                        )

                        # 🔥 AGREGAR LOG DE DATOS:
                        logger.info(f"📦 DATOS DE CONVERSACIÓN A CREAR:")
                        logger.info(f"   {conversation_data.dict()}")

                        conversation = await ConversationService.create_conversation(conversation_data)
                        
                        # 🔥 AGREGAR LOG DESPUÉS DE CREAR:
                        logger.info(f"=" * 80)
                        logger.info(f"✅ CONVERSACIÓN MONGODB CREADA EXITOSAMENTE")
                        logger.info(f"   - MongoDB ID: {conversation.id}")
                        logger.info(f"   - Session ID: {conversation.session_id}")
                        logger.info(f"   - ID Visitante: {conversation.id_visitante}")
                        logger.info(f"   - Estado: {conversation.metadata.estado}")
                        logger.info(f"=" * 80)
                        
                        # 🔥 NUEVO: Crear registro de sincronización en MySQL
                        try:
                            from services.conversacion_sync_service import ConversacionSyncService
                            from schemas.conversacion_sync_schemas import ConversacionSyncCreate
                            
                            sync_service = ConversacionSyncService(db)

                            # 🔥 AGREGAR LOG ANTES DE SYNC:
                            logger.info(f"🔄 CREANDO SINCRONIZACIÓN MYSQL")
                            logger.info(f"   - MongoDB ID: {str(conversation.id)}")
                            logger.info(f"   - ID Visitante: {id_visitante}")
                            logger.info(f"   - ID Agente Inicial: {payload.agent_id}")
                            
                            sync_data = ConversacionSyncCreate(
                                mongodb_conversation_id=str(conversation.id),
                                id_visitante=id_visitante,
                                id_agente_inicial=payload.agent_id,
                                id_agente_actual=payload.agent_id,
                                estado="activa"
                            )
                            
                            sync_record = sync_service.crear_conversacion(sync_data)

                            # 🔥 AGREGAR LOG DESPUÉS DE SYNC:
                            logger.info(f"=" * 80)
                            logger.info(f"✅ SYNC MYSQL CREADO EXITOSAMENTE")
                            logger.info(f"   - ID Sync: {sync_record.id_conversacion_sync}")
                            logger.info(f"   - MongoDB ID: {sync_record.mongodb_conversation_id}")
                            logger.info(f"   - ID Visitante: {sync_record.id_visitante}")
                            logger.info(f"   - Estado: {sync_record.estado}")
                            logger.info(f"=" * 80)
                            
                        except Exception as sync_error:
                            # 🔥 MEJORAR LOG DE ERROR:
                            logger.error(f"=" * 80)
                            logger.error(f"❌ ERROR CREANDO SYNC MYSQL")
                            logger.error(f"   - Error: {str(sync_error)}")
                            logger.error(f"   - Tipo: {type(sync_error).__name__}")
                            logger.error(f"   - MongoDB ID intentado: {str(conversation.id)}")
                            logger.error(f"=" * 80)
                            import traceback
                            logger.error(traceback.format_exc())

                    else:
                        logger.info(f"✅ Conversación existente: {conversation.id}")
                        
                except Exception as e:
                    # 🔥 MEJORAR LOG DE ERROR:
                    logger.error(f"=" * 80)
                    logger.error(f"❌ ERROR CRÍTICO EN CREACIÓN DE CONVERSACIÓN")
                    logger.error(f"   - Session ID: {payload.session_id}")
                    logger.error(f"   - Error: {str(e)}")
                    logger.error(f"   - Tipo: {type(e).__name__}")
                    logger.error(f"=" * 80)
                    import traceback
                    logger.error(traceback.format_exc())
                    
                    yield f"data: {safe_json_dumps({'type': 'error', 'content': f'Error iniciando conversación: {str(e)}'})}\n\n"
                    return
            else:
                logger.info(f"⏭️ Sin visitante registrado, NO se creará conversación aún")
            
            # ============================================
            # 🔥 PASO 0: VERIFICAR CONFIRMACIÓN PENDIENTE PRIMERO
            # ============================================
            tiene_pendiente = escalamiento_service.tiene_confirmacion_pendiente(payload.session_id)
            
            logger.info(f"🔍 Verificando confirmación pendiente: {tiene_pendiente} para session {payload.session_id}")
            
            # 🔥 SI HAY CONFIRMACIÓN PENDIENTE Y NO HAY CONVERSACIÓN, CREARLA AHORA
            if tiene_pendiente and not conversation:
                logger.info(f"🔧 CREANDO CONVERSACIÓN TEMPORAL PARA ESCALAMIENTO")
                try:
                    # Obtener agente si no lo tenemos
                    if not agente:
                        agente = db.query(AgenteVirtual).filter(
                            AgenteVirtual.id_agente == payload.agent_id
                        ).first()
                    
                    if agente:
                        conversation_data = ConversationCreate(
                            session_id=payload.session_id,
                            id_agente=payload.agent_id,
                            agent_name=agente.nombre_agente,
                            agent_type=agente.tipo_agente,
                            id_visitante=id_visitante,
                            origin=payload.origin,
                            ip_origen=ip_origen,
                            user_agent=user_agent
                        )
                        conversation = await ConversationService.create_conversation(conversation_data)
                        logger.info(f"✅ CONVERSACIÓN TEMPORAL CREADA PARA ESCALAMIENTO: {conversation.id}")
                except Exception as e:
                    logger.error(f"❌ Error creando conversación temporal: {e}")
            
            # 🔥 LOGS DE DEBUG
            logger.info(f"=" * 80)
            logger.info(f"🔍 DEBUG CONFIRMACIÓN:")
            logger.info(f"   - session_id: {payload.session_id}")
            logger.info(f"   - mensaje: '{payload.message}'")
            logger.info(f"   - tiene_pendiente: {tiene_pendiente}")
            logger.info(f"   - confirmaciones en memoria: {escalamiento_service._confirmaciones_pendientes}")
            logger.info(f"=" * 80)

            
            if tiene_pendiente:
                logger.info(f"⏳ HAY CONFIRMACIÓN PENDIENTE - Evaluando respuesta: '{payload.message}'")
                
                # ============================================
                # PASO 1: PROCESAR RESPUESTA DE CONFIRMACIÓN
                # ============================================
                # Hay una confirmación pendiente, verificar respuesta
                respuesta = escalamiento_service.detectar_confirmacion(payload.message)
                
                logger.info(f"🎯 Respuesta detectada: '{respuesta}'")
                
                if respuesta == 'confirmar':
                    # ✅ USUARIO CONFIRMÓ → ESCALAR
                    logger.info(f"✅ Usuario confirmó escalamiento para session {payload.session_id}")
                    
                    # Limpiar pendiente
                    escalamiento_service.limpiar_confirmacion_pendiente(payload.session_id)
                    
                    # Mostrar mensaje de confirmado
                    mensaje_confirmado = escalamiento_service.obtener_mensaje_confirmado()
                    
                    yield f"data: {safe_json_dumps({'type': 'status', 'content': mensaje_confirmado})}\n\n"
                    last_event_time = datetime.now()
                    
                    # Proceder con escalamiento
                    try:
                        resultado_escalamiento = await escalamiento_service.escalar_conversacion(
                            session_id=payload.session_id,
                            id_agente=payload.agent_id,
                            motivo="Usuario confirmó escalamiento a humano"
                        )
                        
                        # 🔥 VERIFICAR SI HUBO ERROR
                        if not resultado_escalamiento.get('ok', False):
                            error_tipo = resultado_escalamiento.get('error')
                            
                            if error_tipo == 'no_disponibles':
                                # ❌ NO HAY FUNCIONARIOS DISPONIBLES
                                logger.warning(f"⚠️ No hay funcionarios disponibles para session {payload.session_id}")
                                
                                # 🔥 MENSAJE VISIBLE EN EL WIDGET
                                mensaje_no_disponibles = (
                                    "⚠️ **No hay encargados disponibles en este momento**\n\n"
                                    "Lamentablemente, **no hay personal disponible** para atenderte ahora.\n\n"
                                    "**Opciones:**\n"
                                    "**/intentar nuevamente más tarde**\n"
                                    "**/contactar por otros medios**\n"
                                    "**/continuar aquí conmigo**\n\n"
                                    "Disculpa las molestias. 🙏"
                                )
                                
                                # 🔥 ENVIAR COMO TOKENS (para que se muestre como respuesta del agente)
                                for char in mensaje_no_disponibles:
                                    yield f"data: {safe_json_dumps({'type': 'token', 'content': char})}\n\n"
                                    await asyncio.sleep(0.01)  # Simular escritura natural
                                
                                # 🔥 FINALIZAR STREAM
                                yield f"data: {safe_json_dumps({'type': 'done', 'content': mensaje_no_disponibles})}\n\n"
                                yield "data: [DONE]\n\n"
                                return
                            else:
                                # Otro tipo de error
                                yield f"data: {safe_json_dumps({'type': 'error', 'content': 'Error inesperado al escalar'})}\n\n"
                                yield "data: [DONE]\n\n"
                                return
                        
                        # ✅ ESCALAMIENTO EXITOSO
                        funcionario = resultado_escalamiento.get('funcionario_asignado', {})
                        nombre_funcionario = funcionario.get('nombre', 'Un agente')

                        mensaje_escalamiento = (
                            f"🔔 **Conectado con atención humana**\n\n"
                            f"**{nombre_funcionario}** te atenderá en breve.\n\n"
                            f"💡 Si deseas volver al agente virtual en cualquier momento, solo **escribe:** finalizar escalamiento o volver al bot"
                        )

                        evento_escalamiento = {
                            'type': 'escalamiento',
                            'session_id': payload.session_id,
                            'content': mensaje_escalamiento,
                            'metadata': {
                                'usuario_id': funcionario.get('id'),
                                'usuario_nombre': nombre_funcionario
                            }
                        }

                        yield f"data: {safe_json_dumps(evento_escalamiento)}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                        
                    except Exception as esc_error:
                        logger.error(f"❌ Error escalando: {esc_error}")
                        
                        evento_error = {
                            'type': 'error',
                            'content': 'No se pudo completar la conexión. Intenta de nuevo.'
                        }
                        
                        yield f"data: {safe_json_dumps(evento_error)}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                
                elif respuesta == 'rechazar':
                    # ❌ USUARIO RECHAZÓ → CONTINUAR NORMAL
                    logger.info(f"❌ Usuario rechazó escalamiento para session {payload.session_id}")
                    
                    # Limpiar pendiente
                    escalamiento_service.limpiar_confirmacion_pendiente(payload.session_id)
                    
                    # Mostrar mensaje de cancelado
                    mensaje_cancelado = escalamiento_service.obtener_mensaje_cancelado()
                    
                    yield f"data: {safe_json_dumps({'type': 'status', 'content': mensaje_cancelado})}\n\n"
                    yield f"data: {safe_json_dumps({'type': 'done', 'content': mensaje_cancelado})}\n\n"
                    yield "data: [DONE]\n\n"
                    return  # 🔥 TERMINAR AQUÍ, no procesar el mensaje como pregunta
                
                else:
                    # 🤔 RESPUESTA AMBIGUA → PEDIR CLARIFICACIÓN
                    logger.warning(f"⚠️ Respuesta ambigua para confirmación: '{payload.message}'")
                    
                    mensaje_clarificacion = """⚠️ No entendí tu respuesta.

Por favor responde claramente:
✅ **"Sí"** para conectar con un agente humano
❌ **"No"** para continuar aquí conmigo"""
                    
                    yield f"data: {safe_json_dumps({'type': 'status', 'content': mensaje_clarificacion})}\n\n"
                    yield f"data: {safe_json_dumps({'type': 'done', 'content': mensaje_clarificacion})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
            
            # ============================================
            # 🔥 NUEVO PASO: DETECTAR FINALIZACIÓN DE ESCALAMIENTO
            # ============================================
            logger.info(f"🔍 Verificando si quiere finalizar escalamiento...")

            quiere_finalizar = escalamiento_service.detectar_finalizacion_escalamiento(payload.message)

            if quiere_finalizar:
                logger.info(f"🔚 Intención de finalizar escalamiento detectada: '{payload.message}'")
                
                try:
                    # Finalizar escalamiento
                    resultado_finalizacion = await escalamiento_service.finalizar_escalamiento(
                        session_id=payload.session_id,
                        motivo="Solicitado por usuario"
                    )
                    
                    if resultado_finalizacion.get('ok', False):
                        # ✅ FINALIZACIÓN EXITOSA
                        mensaje_finalizacion = (
                            "✅ **Escalamiento finalizado**\n\n"
                            "**Has vuelto al agente virtual.** Ahora puedes continuar tu conversación normalmente. 😊\n\n"
                            "**Recuerda:** Desde ahora tus mensajes serán procesados por la IA."
                        )
                        
                        # 🔥 ENVIAR MENSAJE AL WIDGET (con efecto de escritura)
                        for char in mensaje_finalizacion:
                            yield f"data: {safe_json_dumps({'type': 'token', 'content': char})}\n\n"
                            await asyncio.sleep(0.01)
                        
                        # 🔥 FINALIZAR
                        yield f"data: {safe_json_dumps({'type': 'done', 'content': mensaje_finalizacion})}\n\n"
                        yield f"data: {safe_json_dumps({'type': 'finalizacion_escalamiento', 'content': 'Escalamiento finalizado'})}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    else:
                        # ❌ ERROR EN FINALIZACIÓN
                        logger.error(f"❌ Error finalizando escalamiento")
                        
                        mensaje_error = (
                            "❌ **No se pudo finalizar el escalamiento**\n\n"
                            "Ocurrió un error. Por favor intenta de nuevo."
                        )
                        
                        yield f"data: {safe_json_dumps({'type': 'error', 'content': mensaje_error})}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                        
                except Exception as e:
                    logger.error(f"❌ Error finalizando escalamiento: {e}")
                    
                    mensaje_error = "❌ Error al finalizar escalamiento"
                    yield f"data: {safe_json_dumps({'type': 'error', 'content': mensaje_error})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

            # ============================================
            # 🔥 PASO 2: SI NO HAY CONFIRMACIÓN PENDIENTE, DETECTAR ESCALAMIENTO
            # ============================================
            logger.info(f"🔍 No hay confirmación pendiente, verificando si es solicitud de escalamiento...")
            
            quiere_humano = escalamiento_service.detectar_intencion_escalamiento(payload.message)
            
            logger.info(f"🔔 ¿Quiere humano? {quiere_humano}")
            
            if quiere_humano:
                logger.info(f"🔔 Intención de escalamiento detectada: '{payload.message[:50]}...'")
                
                # Marcar como pendiente
                escalamiento_service.marcar_confirmacion_pendiente(payload.session_id)
                
                # Enviar MODAL de confirmación
                modal_confirmacion = escalamiento_service.obtener_modal_confirmacion()
                
                yield f"data: {safe_json_dumps(modal_confirmacion)}\n\n"
                yield f"data: {safe_json_dumps({'type': 'done'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            # ============================================
            # PASO 3: FLUJO NORMAL (NO ES ESCALAMIENTO NI CONFIRMACIÓN)
            # ============================================
            logger.info(f"💬 Procesando mensaje normal con agente IA: '{payload.message[:50]}...'")
            
            async for event in service.chat_with_agent_stream(
                id_agente=payload.agent_id,
                pregunta=payload.message,
                session_id=payload.session_id,
                origin=payload.origin,
                ip_origen=ip_origen,
                user_agent=user_agent,
                dispositivo=dispositivo,
                navegador=navegador,
                sistema_operativo=sistema_operativo,
                guardar_en_bd=visitante_registrado,
                k=payload.k,
                use_reranking=payload.use_reranking,
                temperatura=payload.temperatura,
                max_tokens=payload.max_tokens
            ):
                yield f"data: {safe_json_dumps(event)}\n\n"
            
        except Exception as e:
            logger.error(f"❌ Error en stream: {e}")
            error_event = {
                "type": "error",
                "content": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {safe_json_dumps(error_event)}\n\n"
        
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "text/event-stream; charset=utf-8"
        }
    )


@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    service = GroqAgentService(db)
    models = service.list_available_models()
    
    return {
        "ok": True,
        "models": models,
        "total": len(models)
    }