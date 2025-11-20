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

@router.post("/agent")
def chat_with_agent(payload: ChatRequest, db: Session = Depends(get_db)):
    service = OllamaAgentService(db)
    try:
        res = service.chat_with_agent(payload.agent_id, payload.message)
        return {"ok": True, "response": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
