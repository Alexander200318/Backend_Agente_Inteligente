# routers/chat_router.py (CORREGIDO)
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

# ✅ Endpoint SIN streaming
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

# 🔥 Endpoint CON streaming (CORREGIDO)
@router.post("/agent/stream")
async def chat_with_agent_stream(payload: ChatRequest, db: Session = Depends(get_db)):
    service = OllamaAgentService(db)
    
    async def event_generator():
        last_event_time = datetime.now()
        heartbeat_interval = 15
        
        try:
            # 🔥 CORREGIDO: Usar async for
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
                # Enviar evento
                yield f"data: {safe_json_dumps(event)}\n\n"
                last_event_time = datetime.now()
                
                # Heartbeat
                await asyncio.sleep(0)
                
                if (datetime.now() - last_event_time).seconds > heartbeat_interval:
                    yield f": heartbeat\n\n"
                    last_event_time = datetime.now()
            
            # Señal de finalización
            yield f"data: {safe_json_dumps({'type': 'complete'})}\n\n"
            
        except Exception as e:
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