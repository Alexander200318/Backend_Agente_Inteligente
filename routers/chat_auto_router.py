# app/routers/chat_auto_router.py
from fastapi import APIRouter, Depends, HTTPException, Request  # ← AGREGAR Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.database import get_db
from services.agent_classifier import AgentClassifier
from services.escalamiento_service import EscalamientoService
from ollama.ollama_agent_service import OllamaAgentService
from utils.json_utils import safe_json_dumps
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# 🔥 NUEVO: Modelo para información del cliente
class ClientInfo(BaseModel):
    """Información del cliente/navegador"""
    user_agent: str
    dispositivo: str  # 'desktop', 'mobile', 'tablet'
    navegador: str
    sistema_operativo: str
    pantalla: Optional[Dict[str, int]] = None
    idioma: Optional[str] = None

class AutoChatRequest(BaseModel):
    message: str
    departamento_codigo: Optional[str] = None
    session_id: str
    origin: Optional[str] = "web"
    client_info: Optional[ClientInfo] = None  # 🔥 NUEVO
    k: Optional[int] = None
    use_reranking: Optional[bool] = None
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None

@router.post("/auto")
def chat_auto(
    request: Request,  # 🔥 AGREGAR
    payload: AutoChatRequest, 
    db: Session = Depends(get_db)
):
    """
    Clasifica automáticamente y responde con el agente apropiado (sin streaming)
    🔥 MODO STATELESS: No guarda en MongoDB, cada pregunta es independiente
    """
    classifier = AgentClassifier(db)
    
    # 🔥 EXTRAER INFORMACIÓN DEL REQUEST
    ip_origen = request.client.host if request.client else None
    user_agent = payload.client_info.user_agent if payload.client_info else request.headers.get("user-agent")
    dispositivo = payload.client_info.dispositivo if payload.client_info else None
    navegador = payload.client_info.navegador if payload.client_info else None
    sistema_operativo = payload.client_info.sistema_operativo if payload.client_info else None

    # 🔥 NUEVO: NO crear visitante antes de los 3 mensajes
    # Solo pasar información, el servicio decidirá si guardar o no
    visitante_registrado = False
    try:
        from services.visitante_anonimo_service import VisitanteAnonimoService
        visitante_service = VisitanteAnonimoService(db)
        visitante = visitante_service.obtener_por_sesion(payload.session_id)
        visitante_registrado = True
        logger.info(f"✅ Visitante registrado encontrado: {visitante.id_visitante}")
    except:
        logger.info(f"⚠️ No hay visitante registrado (primeros 3 mensajes)")
        visitante_registrado = False

    
    agent_id = classifier.classify(payload.message)
    
    if not agent_id:
        raise HTTPException(
            status_code=404, 
            detail="No se pudo determinar el agente apropiado"
        )
    
    service = OllamaAgentService(db)
    
    try:
        res = service.chat_with_agent(
            id_agente=int(agent_id),
            pregunta=payload.message,
            session_id=payload.session_id,
            origin=payload.origin,
            ip_origen=ip_origen,  # 🔥 NUEVO
            user_agent=user_agent,  # 🔥 NUEVO
            dispositivo=dispositivo,  # 🔥 NUEVO
            navegador=navegador,  # 🔥 NUEVO
            sistema_operativo=sistema_operativo,  # 🔥 NUEVO
            guardar_en_bd=visitante_registrado,
            k=payload.k,
            use_reranking=payload.use_reranking,
            temperatura=payload.temperatura,
            max_tokens=payload.max_tokens
        )
        
        return {
            **res,
            "auto_classified": True,
            "classified_agent_id": agent_id,
            "stateless_mode": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auto/stream")
async def chat_auto_stream(
    request: Request,  # 🔥 AGREGAR
    payload: AutoChatRequest, 
    db: Session = Depends(get_db)
):
    """
    Clasifica automáticamente y responde con streaming
    
    🔥 MODO STATELESS:
    - NO permite escalamiento (requiere seleccionar agente específico)
    - Si detecta intención de escalamiento, informa que debe seleccionar agente
    """
    classifier = AgentClassifier(db)
    service = OllamaAgentService(db)
    escalamiento_service = EscalamientoService(db)
    
    # 🔥 EXTRAER INFORMACIÓN DEL REQUEST
    ip_origen = request.client.host if request.client else None
    user_agent = payload.client_info.user_agent if payload.client_info else request.headers.get("user-agent")
    dispositivo = payload.client_info.dispositivo if payload.client_info else None
    navegador = payload.client_info.navegador if payload.client_info else None
    sistema_operativo = payload.client_info.sistema_operativo if payload.client_info else None

    # 🔥 NUEVO: NO crear visitante antes de los 3 mensajes
    # Solo pasar información, el servicio decidirá si guardar o no
    visitante_registrado = False
    try:
        from services.visitante_anonimo_service import VisitanteAnonimoService
        visitante_service = VisitanteAnonimoService(db)
        visitante = visitante_service.obtener_por_sesion(payload.session_id)
        visitante_registrado = True
        logger.info(f"✅ Visitante registrado encontrado: {visitante.id_visitante}")
    except:
        logger.info(f"⚠️ No hay visitante registrado (primeros 3 mensajes)")
        visitante_registrado = False
    
    async def event_generator():
        last_event_time = datetime.now()
        heartbeat_interval = 15
        
        try:
            # 1. DETECTAR SI QUIERE HABLAR CON HUMANO
            quiere_humano = escalamiento_service.detectar_intencion_escalamiento(payload.message)
            
            if quiere_humano:
                logger.info("⚠️ Escalamiento detectado en modo AUTO (no permitido)")

                evento_error_escalamiento = {
                    "type": "error",
                    "content": (
                        "⚠️ Para hablar con un agente humano, primero debes seleccionar un agente "
                        "específico del menú. El modo automático no permite escalamiento."
                    ),
                    "stateless_mode": True,
                    "auto_mode": True
                }

                yield f"data: {safe_json_dumps(evento_error_escalamiento)}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            # 2. Clasificar agente
            yield f"data: {safe_json_dumps({'type': 'status', 'content': 'Clasificando agente...'})}\n\n"
            last_event_time = datetime.now()
            
            agent_id = classifier.classify(payload.message)
            
            if not agent_id:
                yield f"data: {safe_json_dumps({'type': 'error', 'content': 'No se pudo clasificar el agente'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            # 3. Enviar info de clasificación
            yield f"data: {safe_json_dumps({'type': 'classification', 'agent_id': agent_id, 'stateless': True})}\n\n"
            last_event_time = datetime.now()
            
            # 4. Streaming de respuesta
            async for event in service.chat_with_agent_stream(
                id_agente=int(agent_id),
                pregunta=payload.message,
                session_id=payload.session_id,
                origin=payload.origin,
                ip_origen=ip_origen,  # 🔥 NUEVO
                user_agent=user_agent,  # 🔥 NUEVO
                dispositivo=dispositivo,  # 🔥 NUEVO
                navegador=navegador,  # 🔥 NUEVO
                sistema_operativo=sistema_operativo,  # 🔥 NUEVO
                guardar_en_bd=visitante_registrado,
                k=payload.k,
                use_reranking=payload.use_reranking,
                temperatura=payload.temperatura,
                max_tokens=payload.max_tokens
            ):
                if event.get("type") == "done":
                    event["auto_classified"] = True
                    event["classified_agent_id"] = agent_id
                    event["stateless_mode"] = True
                
                yield f"data: {safe_json_dumps(event)}\n\n"
                last_event_time = datetime.now()
                
                await asyncio.sleep(0)
                
                if (datetime.now() - last_event_time).seconds > heartbeat_interval:
                    yield f": heartbeat\n\n"
                    last_event_time = datetime.now()
            
            yield f"data: {safe_json_dumps({'type': 'complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"❌ Error en auto stream: {e}")
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