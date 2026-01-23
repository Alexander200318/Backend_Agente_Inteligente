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

# 🔥 CORREGIDO: Quitar /agentes/ del path
@router.get("/{id_agente}/welcome")
def get_agent_welcome(id_agente: int, db: Session = Depends(get_db)):
    """Obtiene mensaje de bienvenida de un agente"""
    agente = db.query(AgenteVirtual).filter(
        AgenteVirtual.id_agente == id_agente
    ).first()
    
    if not agente:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    
    mensaje = agente.mensaje_bienvenida or f"Hola, soy {agente.nombre_agente}. ¿En qué puedo ayudarte?"
    
    return {
        "ok": True,
        "mensaje_bienvenida": mensaje,
        "agente_id": id_agente,
        "agente_nombre": agente.nombre_agente
    }

# Agregar en routes/agentes_router.py

@router.post("/reindex-all")
def reindex_all_agents(db: Session = Depends(get_db)):
    """
    Re-indexa TODOS los agentes del sistema
    Útil después de actualizar la estructura de metadata
    """
    from models.agente_virtual import AgenteVirtual
    
    agentes = db.query(AgenteVirtual).filter(
        AgenteVirtual.activo == True
    ).all()
    
    rag = RAGService(db)
    resultados = []
    
    for agente in agentes:
        try:
            resultado = rag.reindex_agent(agente.id_agente)
            resultados.append({
                "id_agente": agente.id_agente,
                "nombre": agente.nombre_agente,
                "status": "✅ OK",
                "total_docs": resultado.get("total_docs", 0)
            })
        except Exception as e:
            resultados.append({
                "id_agente": agente.id_agente,
                "nombre": agente.nombre_agente,
                "status": "❌ ERROR",
                "error": str(e)
            })
    
    return {
        "ok": True,
        "total_agentes": len(agentes),
        "resultados": resultados
    }