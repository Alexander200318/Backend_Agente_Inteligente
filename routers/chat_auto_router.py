# app/routers/chat_auto_router.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.database import get_db
from services.agent_classifier import AgentClassifier
from ollama.ollama_agent_service import OllamaAgentService
from typing import Optional
import json

router = APIRouter(prefix="/chat", tags=["Chat"])

class AutoChatRequest(BaseModel):
    message: str
    departamento_codigo: Optional[str] = None
    k: Optional[int] = None              # 🔥 CAMBIO: Ahora opcional
    use_reranking: Optional[bool] = None # 🔥 NUEVO
    temperatura: Optional[float] = None  # 🔥 NUEVO
    max_tokens: Optional[int] = None     # 🔥 NUEVO

# ✅ Endpoint SIN streaming (mantiene compatibilidad)
@router.post("/auto")
def chat_auto(payload: AutoChatRequest, db: Session = Depends(get_db)):
    """
    Clasifica automáticamente y responde con el agente apropiado (sin streaming)
    """
    classifier = AgentClassifier(db)
    
    # Clasificar agente
    agent_id = classifier.classify(payload.message)
    
    if not agent_id:
        raise HTTPException(
            status_code=404, 
            detail="No se pudo determinar el agente apropiado"
        )
    
    # Chatear con el agente clasificado
    service = OllamaAgentService(db)
    
    try:
        res = service.chat_with_agent(
            id_agente=int(agent_id),
            pregunta=payload.message,
            k=payload.k,
            use_reranking=payload.use_reranking,
            temperatura=payload.temperatura,
            max_tokens=payload.max_tokens
        )
        
        return {
            **res,
            "auto_classified": True,
            "classified_agent_id": agent_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔥 NUEVO: Endpoint CON streaming
@router.post("/auto/stream")
def chat_auto_stream(payload: AutoChatRequest, db: Session = Depends(get_db)):
    """
    Clasifica automáticamente y responde con streaming
    """
    classifier = AgentClassifier(db)
    service = OllamaAgentService(db)
    
    def event_generator():
        try:
            # 1) Clasificar agente
            yield f"data: {json.dumps({'type': 'status', 'content': 'Clasificando agente...'}, ensure_ascii=False)}\n\n"
            
            agent_id = classifier.classify(payload.message)
            
            if not agent_id:
                yield f"data: {json.dumps({'type': 'error', 'content': 'No se pudo clasificar el agente'}, ensure_ascii=False)}\n\n"
                return
            
            # 2) Enviar info de clasificación
            yield f"data: {json.dumps({'type': 'classification', 'agent_id': agent_id}, ensure_ascii=False)}\n\n"
            
            # 3) Streaming de respuesta
            for event in service.chat_with_agent_stream(
                id_agente=int(agent_id),
                pregunta=payload.message,
                k=payload.k,
                use_reranking=payload.use_reranking,
                temperatura=payload.temperatura,
                max_tokens=payload.max_tokens
            ):
                # Agregar info de clasificación al evento final
                if event.get("type") == "done":
                    event["auto_classified"] = True
                    event["classified_agent_id"] = agent_id
                
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                
        except Exception as e:
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
            "X-Accel-Buffering": "no"
        }
    )