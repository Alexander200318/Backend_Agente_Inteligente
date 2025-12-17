# app/routers/chat_auto_router.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.database import get_db
from services.agent_classifier import AgentClassifier
from ollama.ollama_agent_service import OllamaAgentService
from utils.json_utils import safe_json_dumps
from typing import Optional
from datetime import datetime
import asyncio

router = APIRouter(prefix="/chat", tags=["Chat"])

class AutoChatRequest(BaseModel):
    message: str
    departamento_codigo: Optional[str] = None
    session_id: str
    origin: Optional[str] = "web"
    k: Optional[int] = None
    use_reranking: Optional[bool] = None
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None

# ✅ Endpoint SIN streaming
@router.post("/auto")
def chat_auto(payload: AutoChatRequest, db: Session = Depends(get_db)):
    """
    Clasifica automáticamente y responde con el agente apropiado (sin streaming)
    🔥 MODO STATELESS: No guarda en MongoDB, cada pregunta es independiente
    """
    classifier = AgentClassifier(db)
    
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
            k=payload.k,
            use_reranking=payload.use_reranking,
            temperatura=payload.temperatura,
            max_tokens=payload.max_tokens
        )
        
        return {
            **res,
            "auto_classified": True,
            "classified_agent_id": agent_id,
            "stateless_mode": True  # 🔥 Indicar que es modo stateless
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔥 Endpoint CON streaming - MODO STATELESS
@router.post("/auto/stream")
async def chat_auto_stream(payload: AutoChatRequest, db: Session = Depends(get_db)):
    """
    Clasifica automáticamente y responde con streaming
    
    🔥 CARACTERÍSTICAS:
    - NO guarda conversación en MongoDB
    - NO mantiene agente seleccionado
    - Cada pregunta es independiente
    - NO permite escalamiento a humano (requiere seleccionar agente)
    """
    classifier = AgentClassifier(db)
    service = OllamaAgentService(db)
    
    async def event_generator():
        last_event_time = datetime.now()
        heartbeat_interval = 15
        
        try:
            # 1) Clasificar agente
            yield f"data: {safe_json_dumps({'type': 'status', 'content': 'Clasificando agente...'})}\n\n"
            last_event_time = datetime.now()
            
            agent_id = classifier.classify(payload.message)
            
            if not agent_id:
                yield f"data: {safe_json_dumps({'type': 'error', 'content': 'No se pudo clasificar el agente'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            # 2) Enviar info de clasificación
            yield f"data: {safe_json_dumps({'type': 'classification', 'agent_id': agent_id, 'stateless': True})}\n\n"
            last_event_time = datetime.now()
            
            # 3) 🔥 Streaming de respuesta CON save_to_mongo=False
            async for event in service.chat_with_agent_stream(
                id_agente=int(agent_id),
                pregunta=payload.message,
                session_id=payload.session_id,
                origin=payload.origin,
                save_to_mongo=False,  # 🔥 NO GUARDAR EN MONGODB
                k=payload.k,
                use_reranking=payload.use_reranking,
                temperatura=payload.temperatura,
                max_tokens=payload.max_tokens
            ):
                # Agregar info de clasificación al evento final
                if event.get("type") == "done":
                    event["auto_classified"] = True
                    event["classified_agent_id"] = agent_id
                    event["stateless_mode"] = True  # 🔥 Indicar modo stateless
                
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
