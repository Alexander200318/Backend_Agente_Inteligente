# app/routers/unidad_contenido_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.unidad_contenido_service import UnidadContenidoService
from schemas.unidad_contenido_schemas import UnidadContenidoResponse, UnidadContenidoCreate,UnidadContenidoUpdate
from exceptions.base import NotFoundException
from datetime import date

router = APIRouter(prefix="/contenidos", tags=["Contenidos"])

@router.post("/", response_model=UnidadContenidoResponse, status_code=201)
def crear_contenido(data: UnidadContenidoCreate, db: Session = Depends(get_db)):
    return UnidadContenidoService(db).crear_contenido(data, creado_por=1)  # TODO: get from JWT

@router.get("/agente/{id_agente}", response_model=List[UnidadContenidoResponse])
def listar_contenidos(id_agente: int, estado: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return UnidadContenidoService(db).listar_por_agente(id_agente, estado, skip, limit)

@router.put("/{id_contenido}", response_model=UnidadContenidoResponse)
def actualizar_contenido(id_contenido: int, data: UnidadContenidoUpdate, db: Session = Depends(get_db)):
    return UnidadContenidoService(db).actualizar_contenido(id_contenido, data, actualizado_por=1)

@router.post("/{id_contenido}/publicar", response_model=UnidadContenidoResponse)
def publicar_contenido(id_contenido: int, db: Session = Depends(get_db)):
    return UnidadContenidoService(db).publicar_contenido(id_contenido, publicado_por=1)


@router.delete("/{id_contenido}")
def eliminar_contenido(
    id_contenido: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un contenido de la BD y ChromaDB
    """
    service = UnidadContenidoService(db)
    
    try:
        resultado = service.eliminar_contenido(id_contenido)
        return resultado
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# app/routers/unidad_contenido_router.py

@router.post("/reindex/all")
def reindexar_todo_contenido(db: Session = Depends(get_db)):
    """
    Re-indexa TODOS los contenidos activos en ChromaDB
    Útil después de resetear ChromaDB
    """
    from models.unidad_contenido import UnidadContenido
    from models.categoria import Categoria
    
    service = UnidadContenidoService(db)
    
    # Obtener todos los contenidos activos
    contenidos = db.query(UnidadContenido).filter(
        UnidadContenido.estado == "activo"
    ).all()
    
    reindexados = 0
    errores = []
    
    for contenido in contenidos:
        try:
            # Obtener categoría
            categoria = db.query(Categoria).filter(
                Categoria.id_categoria == contenido.id_categoria
            ).first()
            
            if categoria:
                service.rag.ingest_unidad(contenido, categoria)
                reindexados += 1
        except Exception as e:
            errores.append({
                "id_contenido": contenido.id_contenido,
                "error": str(e)
            })
    
    return {
        "ok": True,
        "total_contenidos": len(contenidos),
        "reindexados": reindexados,
        "errores": errores
    }