# app/routers/chat_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db 
from pydantic import BaseModel
from ollama.ollama_agent_service import OllamaAgentService

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    agent_id: int
    message: str
    k: int = 4  # Número de fuentes RAG
    use_reranking: bool = True

@router.post("/agent")
def chat_with_agent(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Chatea con un agente específico usando RAG + Ollama
    """
    service = OllamaAgentService(db)
    
    try:
        res = service.chat_with_agent(
            id_agente=payload.agent_id,
            pregunta=payload.message,
            k=payload.k,
            use_reranking=payload.use_reranking
        )
        return res
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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