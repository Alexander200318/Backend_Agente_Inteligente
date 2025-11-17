from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.unidad_contenido_service import UnidadContenidoService
from schemas.unidad_contenido_schemas import UnidadContenidoResponse, UnidadContenidoCreate,UnidadContenidoUpdate

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