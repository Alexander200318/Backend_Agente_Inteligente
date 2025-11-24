# app/routers/chat_auto_router.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.database import get_db
from services.agent_classifier import AgentClassifier
from ollama.ollama_agent_service import OllamaAgentService
from typing import Optional

router = APIRouter(prefix="/chat", tags=["Chat"])

class AutoChatRequest(BaseModel):
    message: str
    departamento_codigo: Optional[str] = None
    k: int = 4

@router.post("/auto")
def chat_auto(payload: AutoChatRequest, db: Session = Depends(get_db)):
    """
    Clasifica automáticamente y responde con el agente apropiado
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
            k=payload.k
        )
        
        return {
            **res,
            "auto_classified": True,
            "classified_agent_id": agent_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))