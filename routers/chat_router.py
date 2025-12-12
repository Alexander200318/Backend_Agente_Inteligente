# routers/chat_router.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database.database import get_db 
from pydantic import BaseModel
from ollama.ollama_agent_service import OllamaAgentService
from utils.json_utils import safe_json_dumps
from typing import Optional
from datetime import datetime
import asyncio
import time

# ============================
# 🔧 PREFIJO DEL ROUTER
# ============================
router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


# ============================
# 📌 MODELOS DE REQUEST
# ============================
class ChatRequest(BaseModel):
    """Modelo para chat con agente específico"""
    agent_id: int
    message: str
    k: Optional[int] = None
    use_reranking: Optional[bool] = None
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None
    session_id: Optional[str] = None


class AutoChatRequest(BaseModel):
    """Modelo para chat automático (router de agentes)"""
    message: str
    departamento_codigo: Optional[str] = ""
    k: Optional[int] = None
    use_reranking: Optional[bool] = None
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None
    session_id: Optional[str] = None


# ============================
# 🚀 CHAT SIN STREAMING
# ============================
@router.post("/agent")
def chat_with_agent(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat con agente específico (sin streaming)
    
    Endpoint: POST /api/v1/chat/agent
    Body: { "agent_id": 1, "message": "Hola" }
    """
    service = OllamaAgentService(db)

    try:
        result = service.chat_with_agent(
            id_agente=payload.agent_id,
            pregunta=payload.message,
            k=payload.k,
            use_reranking=payload.use_reranking,
            temperatura=payload.temperatura,
            max_tokens=payload.max_tokens
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================
# 🔥 CHAT CON STREAMING - AGENTE ESPECÍFICO
# ============================
@router.post("/agent/stream")
async def chat_with_agent_stream(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat con agente específico (con streaming SSE)
    
    Endpoint: POST /api/v1/chat/agent/stream
    Body: { "agent_id": 1, "message": "Hola", "session_id": "sess-xxx" }
    Retorna: Server-Sent Events (SSE) stream
    """
    service = OllamaAgentService(db)

    session_id = payload.session_id or f"agent-{payload.agent_id}-{int(time.time() * 1000)}"
    
    print(f"🔵 [AGENT STREAM] Session: {session_id}, Agent: {payload.agent_id}")

    async def event_generator():
        last_event_time = datetime.now()
        heartbeat_interval = 15

        try:
            # Iterar sobre el stream del servicio
            for event in service.chat_with_agent_stream(
                id_agente=payload.agent_id,
                pregunta=payload.message,
                k=payload.k,
                use_reranking=payload.use_reranking,
                temperatura=payload.temperatura,
                max_tokens=payload.max_tokens
            ):
                enriched_event = {
                    "session_id": session_id,
                    **event
                }

                yield f"data: {safe_json_dumps(enriched_event)}\n\n"
                last_event_time = datetime.now()
                await asyncio.sleep(0)

                if (datetime.now() - last_event_time).seconds > heartbeat_interval:
                    yield f": heartbeat {session_id}\n\n"
                    last_event_time = datetime.now()

            complete_evt = {
                "session_id": session_id,
                "type": "complete"
            }
            yield f"data: {safe_json_dumps(complete_evt)}\n\n"

        except Exception as e:
            print(f"❌ [AGENT STREAM] Error: {str(e)}")
            error_evt = {
                "session_id": session_id,
                "type": "error",
                "content": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {safe_json_dumps(error_evt)}\n\n"

        finally:
            done_evt = {
                "session_id": session_id,
                "type": "done"
            }
            yield f"data: {safe_json_dumps(done_evt)}\n\n"
            print(f"✅ [AGENT STREAM] Finalizado: {session_id}")

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


# ============================
# 🤖 CHAT AUTOMÁTICO (ROUTER DE AGENTES)
# ============================
@router.post("/auto/stream")
async def chat_auto_stream(payload: AutoChatRequest, db: Session = Depends(get_db)):
    """
    Chat automático con selección de agente
    
    Endpoint: POST /api/v1/chat/auto/stream
    Body: { "message": "Hola", "departamento_codigo": "soporte" }
    """
    service = OllamaAgentService(db)
    session_id = payload.session_id or f"auto-{int(time.time() * 1000)}"
    
    print(f"🔵 [AUTO STREAM] Session: {session_id}, Dept: {payload.departamento_codigo}")

    async def event_generator():
        last_event_time = datetime.now()
        heartbeat_interval = 15

        try:
            for event in service.chat_auto_stream(
                pregunta=payload.message,
                departamento_codigo=payload.departamento_codigo,
                k=payload.k,
                use_reranking=payload.use_reranking,
                temperatura=payload.temperatura,
                max_tokens=payload.max_tokens
            ):
                enriched_event = {
                    "session_id": session_id,
                    **event
                }

                yield f"data: {safe_json_dumps(enriched_event)}\n\n"
                last_event_time = datetime.now()
                await asyncio.sleep(0)

                if (datetime.now() - last_event_time).seconds > heartbeat_interval:
                    yield f": heartbeat {session_id}\n\n"
                    last_event_time = datetime.now()

            complete_evt = {
                "session_id": session_id,
                "type": "complete"
            }
            yield f"data: {safe_json_dumps(complete_evt)}\n\n"

        except Exception as e:
            print(f"❌ [AUTO STREAM] Error: {str(e)}")
            error_evt = {
                "session_id": session_id,
                "type": "error",
                "content": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {safe_json_dumps(error_evt)}\n\n"

        finally:
            done_evt = {
                "session_id": session_id,
                "type": "done"
            }
            yield f"data: {safe_json_dumps(done_evt)}\n\n"
            print(f"✅ [AUTO STREAM] Finalizado: {session_id}")

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


# ============================
# 📌 LISTAR MODELOS DISPONIBLES
# ============================
@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    """
    Lista todos los modelos disponibles en Ollama
    
    Endpoint: GET /api/v1/chat/models
    Retorna: { "ok": true, "models": [...], "total": 5 }
    """
    service = OllamaAgentService(db)
    
    try:
        models = service.list_available_models()
        
        # Validar que models sea una lista
        if not isinstance(models, list):
            models = []
        
        return {
            "ok": True,
            "models": models,
            "total": len(models)
        }
    except Exception as e:
        print(f"❌ Error listando modelos: {str(e)}")
        # Retornar respuesta en lugar de error 500
        return {
            "ok": False,
            "models": [],
            "total": 0,
            "error": str(e)
        }