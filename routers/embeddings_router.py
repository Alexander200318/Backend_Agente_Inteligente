# app/routers/embeddings_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from rag.rag_service import RAGService
from models.unidad_contenido import UnidadContenido
from models.categoria import Categoria

router = APIRouter(prefix="/embeddings", tags=["Embeddings"])

@router.post("/indexar_unidad/{id_unidad}")
def index_unidad(id_unidad: int, db: Session = Depends(get_db)):
    unidad = db.query(UnidadContenido).filter(UnidadContenido.id_contenido == id_unidad).first()
    if not unidad:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")
    categoria = db.query(Categoria).filter(Categoria.id_categoria == unidad.id_categoria).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")
    rag = RAGService(db)
    return rag.ingest_unidad(unidad, categoria)

@router.post("/indexar_agente/{id_agente}")
def index_agente(id_agente: int, db: Session = Depends(get_db)):
    rag = RAGService(db)
    return rag.reindex_agent(id_agente)
