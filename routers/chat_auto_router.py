# app/routers/chat_auto_router.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.database import get_db
from services.agent_classifier import AgentClassifier
from ollama.ollama_agent_service import OllamaAgentService

router = APIRouter(prefix="/chat", tags=["Chat"])

class AutoChatRequest(BaseModel):
    departamento_codigo: str = None  # opcional, para acotar
    message: str

@router.post("/auto")
def chat_auto(payload: AutoChatRequest, db: Session = Depends(get_db)):
    classifier = AgentClassifier(db)
    agent_id = classifier.classify(payload.message)
    if not agent_id:
        raise HTTPException(status_code=404, detail="No se pudo determinar el agente")
    service = OllamaAgentService(db)
    try:
        res = service.chat_with_agent(int(agent_id), payload.message)
        return {"ok": True, "agent_id": agent_id, "response": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
