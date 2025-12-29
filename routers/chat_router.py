# routers/chat_router.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database.database import get_db 
from pydantic import BaseModel
from ollama.ollama_agent_service import OllamaAgentService
from services.escalamiento_service import EscalamientoService  # ← AGREGAR
from utils.json_utils import safe_json_dumps
from typing import Optional
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    agent_id: int
    message: str
    session_id: str
    origin: Optional[str] = "web"
    k: Optional[int] = None
    use_reranking: Optional[bool] = None
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None

@router.post("/agent")
def chat_with_agent(payload: ChatRequest, db: Session = Depends(get_db)):
    service = OllamaAgentService(db)
    
    try:
        res = service.chat_with_agent(
            id_agente=payload.agent_id,
            pregunta=payload.message,
            session_id=payload.session_id,
            origin=payload.origin,
            k=payload.k,
            use_reranking=payload.use_reranking,
            temperatura=payload.temperatura,
            max_tokens=payload.max_tokens
        )
        return res
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/agent/stream")
async def chat_with_agent_stream(payload: ChatRequest, db: Session = Depends(get_db)):
    service = OllamaAgentService(db)
    escalamiento_service = EscalamientoService(db)
    
    async def event_generator():
        last_event_time = datetime.now()
        heartbeat_interval = 15
        
        try:
            # 🔥 1. DETECTAR SI EL USUARIO QUIERE HABLAR CON HUMANO
            quiere_humano = escalamiento_service.detectar_intencion_escalamiento(payload.message)
            
            if quiere_humano:
                logger.info(f"🔔 Escalamiento detectado en mensaje: '{payload.message[:50]}...'")
                
                # Enviar status
                yield f"data: {safe_json_dumps({'type': 'status', 'content': 'Escalando a agente humano...'})}\n\n"
                last_event_time = datetime.now()
                
                try:
                    # 🔥 2. ESCALAR CONVERSACIÓN (crea nueva con sufijo -esc-)
                    resultado_escalamiento = await escalamiento_service.escalar_conversacion(
                        session_id=payload.session_id,
                        id_agente=payload.agent_id,
                        motivo="Usuario solicitó hablar con humano"
                    )
                    
                    logger.info(f"✅ Escalamiento exitoso:")
                    logger.info(f"   Original: {payload.session_id}")
                    logger.info(f"   Nuevo:    {resultado_escalamiento['session_id']}")
                    
                    # 🔥 3. ENVIAR EVENTO DE ESCALAMIENTO con NUEVO session_id
                    funcionario = resultado_escalamiento.get('funcionario_asignado', {})
                    nombre_funcionario = funcionario.get('nombre', 'Un agente')
                    
                    # Construir el evento FUERA del yield
                    evento_escalamiento = {
                        'type': 'escalamiento',
                        'session_id': payload.session_id,
                        'nuevo_session_id': resultado_escalamiento['session_id'],
                        'content': f"🔔 Tu conversación ha sido escalada a atención humana. {nombre_funcionario} te atenderá en breve.",
                        'metadata': {
                            'usuario_id': funcionario.get('id'),
                            'usuario_nombre': funcionario.get('nombre')
                        }
                    }
                    
                    yield f"data: {safe_json_dumps(evento_escalamiento)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                    
                except Exception as esc_error:
                    logger.error(f"❌ Error escalando: {esc_error}")
                    
                    evento_error = {
                        'type': 'error',
                        'content': 'No se pudo escalar la conversación. Intenta de nuevo.'
                    }
                    
                    yield f"data: {safe_json_dumps(evento_error)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
            
            # 🔥 4. SI NO ES ESCALAMIENTO, CONTINUAR NORMAL
            async for event in service.chat_with_agent_stream(
                id_agente=payload.agent_id,
                pregunta=payload.message,
                session_id=payload.session_id,
                origin=payload.origin,
                k=payload.k,
                use_reranking=payload.use_reranking,
                temperatura=payload.temperatura,
                max_tokens=payload.max_tokens
            ):
                yield f"data: {safe_json_dumps(event)}\n\n"
                last_event_time = datetime.now()
                
                await asyncio.sleep(0)
                
                if (datetime.now() - last_event_time).seconds > heartbeat_interval:
                    yield f": heartbeat\n\n"
                    last_event_time = datetime.now()
            
            yield f"data: {safe_json_dumps({'type': 'complete'})}\n\n"
            
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
    service = OllamaAgentService(db)
    models = service.list_available_models()
    
    return {
        "ok": True,
        "models": models,
        "total": len(models)
    }