# app/routers/chat_router.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database.database import get_db 
from pydantic import BaseModel
from ollama.ollama_agent_service import OllamaAgentService
from typing import Optional
import json

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    agent_id: int
    message: str
    k: Optional[int] = None              # 🔥 CAMBIO: Ahora opcional
    use_reranking: Optional[bool] = None # 🔥 CAMBIO: Ahora opcional
    temperatura: Optional[float] = None  # 🔥 NUEVO
    max_tokens: Optional[int] = None     # 🔥 NUEVO

# ✅ Endpoint SIN streaming (mantiene compatibilidad)
@router.post("/agent")
def chat_with_agent(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Chatea con un agente específico usando RAG + Ollama (sin streaming)
    """
    service = OllamaAgentService(db)
    
    try:
        res = service.chat_with_agent(
            id_agente=payload.agent_id,
            pregunta=payload.message,
            k=payload.k,
            use_reranking=payload.use_reranking,
            temperatura=payload.temperatura,
            max_tokens=payload.max_tokens
        )
        return res
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔥 NUEVO: Endpoint CON streaming
@router.post("/agent/stream")
def chat_with_agent_stream(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Chatea con un agente específico usando RAG + Ollama (con streaming)
    
    Retorna Server-Sent Events (SSE) con formato:
    data: {"type": "token", "content": "texto"}
    """
    service = OllamaAgentService(db)
    
    def event_generator():
        """Genera eventos SSE"""
        try:
            for event in service.chat_with_agent_stream(
                id_agente=payload.agent_id,
                pregunta=payload.message,
                k=payload.k,
                use_reranking=payload.use_reranking,
                temperatura=payload.temperatura,
                max_tokens=payload.max_tokens
            ):
                # Formato SSE: data: {json}\n\n
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            # Enviar error como evento
            error_event = {
                "type": "error",
                "content": str(e)
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginx: desactivar buffering
        }
    )

@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    """
    Lista modelos disponibles en Ollama
    """
    service = OllamaAgentService(db)
    models = service.list_available_models()
    
    return {
        "ok": True,
        "models": models,
        "total": len(models)
    }