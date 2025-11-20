# app/rag/ingestion.py
from sqlalchemy.orm import Session
from rag.rag_service import RAGService

def reindex_all_agents(db: Session):
    rag = RAGService(db)
    agentes = db.query("AgenteVirtual")  # si tu modelo está importable, reemplaza por model
    # Mejor llamar desde un punto que tenga acceso al modelo real.
    # Implementación ejemplo (depende de tus imports):
    from models.agente_virtual import AgenteVirtual
    agentes = db.query(AgenteVirtual).filter(AgenteVirtual.activo==True).all()
    stats = {}
    for a in agentes:
        res = rag.reindex_agent(a.id_agente)
        stats[a.id_agente] = res
    return stats
