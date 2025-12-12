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
import time  # Para generar session_id único

router = APIRouter(prefix="/chat", tags=["Chat"])


# ============================
# 📌 MODELO DE REQUEST
# ============================
class ChatRequest(BaseModel):
    agent_id: int
    message: str
    k: Optional[int] = None
    use_reranking: Optional[bool] = None
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None
    
    # ID de sesión (web, móvil, otra pestaña)
    session_id: Optional[str] = None


# ============================
# 🚀 CHAT SIN STREAMING
# ============================
@router.post("/agent")
def chat_with_agent(payload: ChatRequest, db: Session = Depends(get_db)):
    service = OllamaAgentService(db)

    try:
        return service.chat_with_agent(
            id_agente=payload.agent_id,
            pregunta=payload.message,
            k=payload.k,
            use_reranking=payload.use_reranking,
            temperatura=payload.temperatura,
            max_tokens=payload.max_tokens
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ============================
# 🔥 CHAT CON STREAMING SSE
# ============================
@router.post("/agent/stream")
async def chat_with_agent_stream(payload: ChatRequest, db: Session = Depends(get_db)):
    service = OllamaAgentService(db)

    # Crear session_id único si no lo envía el cliente
    session_id = payload.session_id or f"{payload.agent_id}-{int(time.time() * 1000)}"

    async def event_generator():
        last_event_time = datetime.now()
        heartbeat_interval = 15  # segundos sin actividad

        try:
            # Iterar sobre el generador del servicio
            for event in service.chat_with_agent_stream(
                id_agente=payload.agent_id,
                pregunta=payload.message,
                k=payload.k,
                use_reranking=payload.use_reranking,
                temperatura=payload.temperatura,
                max_tokens=payload.max_tokens
            ):
                # Adjuntar session_id al evento
                enriched_event = {
                    "session_id": session_id,
                    **event
                }

                # Enviar evento SSE
                yield f"data: {safe_json_dumps(enriched_event)}\n\n"
                last_event_time = datetime.now()

                # Permitir a FastAPI/o asyncio continuar
                await asyncio.sleep(0)

                # Heartbeat automático
                if (datetime.now() - last_event_time).seconds > heartbeat_interval:
                    yield f": heartbeat {session_id}\n\n"
                    last_event_time = datetime.now()

            # Evento de finalización
            complete_evt = {
                "session_id": session_id,
                "type": "complete"
            }
            yield f"data: {safe_json_dumps(complete_evt)}\n\n"

        except Exception as e:
            error_evt = {
                "session_id": session_id,
                "type": "error",
                "content": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {safe_json_dumps(error_evt)}\n\n"

        finally:
            # Notificar cierre definitivo
            done_evt = {
                "session_id": session_id,
                "type": "done"
            }
            yield f"data: {safe_json_dumps(done_evt)}\n\n"

    # Retornar streaming SSE
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
# 📌 LISTAR MODELOS OLLAMA
# ============================
@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    service = OllamaAgentService(db)
    models = service.list_available_models()

    return {
        "ok": True,
        "models": models,
        "total": len(models)
    }
