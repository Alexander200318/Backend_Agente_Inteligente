from fastapi import APIRouter, Depends

from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.categoria_service import CategoriaService
from schemas.categoria_schemas import CategoriaResponse, CategoriaCreate, CategoriaUpdate


router = APIRouter(prefix="/categorias", tags=["Categorías"])

@router.post("/", response_model=CategoriaResponse, status_code=201)
def crear_categoria(data: CategoriaCreate, db: Session = Depends(get_db)):
    return CategoriaService(db).crear_categoria(data)

@router.get("/agente/{id_agente}", response_model=List[CategoriaResponse])
def listar_por_agente(id_agente: int, activo: Optional[bool] = None, db: Session = Depends(get_db)):
    return CategoriaService(db).listar_por_agente(id_agente, activo)

@router.put("/{id_categoria}", response_model=CategoriaResponse)
def actualizar_categoria(id_categoria: int, data: CategoriaUpdate, db: Session = Depends(get_db)):
    return CategoriaService(db).actualizar_categoria(id_categoria, data)

@router.delete("/{id_categoria}")
def eliminar_categoria(id_categoria: int, db: Session = Depends(get_db)):
    return CategoriaService(db).eliminar_categoria(id_categoria)

