# app/routers/agentes_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from services.agent_classifier import AgentClassifier
from rag.rag_service import RAGService
from ollama.ollama_agent_service import OllamaAgentService
from models.agente_virtual import AgenteVirtual

router = APIRouter(prefix="/agentes", tags=["Agentes"])

@router.post("/{id_agente}/reindex")
def reindex_agent(id_agente: int, db: Session = Depends(get_db)):
    rag = RAGService(db)
    res = rag.reindex_agent(id_agente)
    return res

@router.post("/{id_agente}/build_model")
def build_agent_model(id_agente: int, db: Session = Depends(get_db)):
    service = OllamaAgentService(db)
    try:
        result = service.crear_o_actualizar_modelo(id_agente)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rebuild_agents_index")
def rebuild_agents_index(db: Session = Depends(get_db)):
    classifier = AgentClassifier(db)
    return classifier.build_index()
