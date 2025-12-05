from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database.database import get_db
from services.categoria_service import CategoriaService
from schemas.categoria_schemas import (
    CategoriaResponse,
    CategoriaCreate,
    CategoriaUpdate,
)

router = APIRouter(
    prefix="/categorias",
    tags=["Categorías"]
)

# ======================================================
# 🔹 Crear categoría
# ======================================================
@router.post(
    "/",
    response_model=CategoriaResponse,
    status_code=status.HTTP_201_CREATED
)
def crear_categoria(
    data: CategoriaCreate,
    db: Session = Depends(get_db)
):
    return CategoriaService(db).crear_categoria(data)

# ======================================================
# 🔹 Listar categorías con filtros opcionales
# GET /categorias?activo=true&id_agente=1
# ======================================================
@router.get(
    "/",
    response_model=List[CategoriaResponse]
)
def listar_categorias(
    activo: Optional[bool] = Query(
        None,
        description="Filtrar por estado activo (true / false)"
    ),
    id_agente: Optional[int] = Query(
        None,
        description="Filtrar por ID de agente"
    ),
    db: Session = Depends(get_db)
):
    return CategoriaService(db).listar_categorias(
        activo=activo,
        id_agente=id_agente
    )

# ======================================================
# 🔹 Listar categorías por agente
# GET /categorias/agente/1?activo=true
# ======================================================
@router.get(
    "/agente/{id_agente}",
    response_model=List[CategoriaResponse]
)
def listar_por_agente(
    id_agente: int,
    activo: Optional[bool] = Query(
        None,
        description="Filtrar por estado activo (true / false)"
    ),
    db: Session = Depends(get_db)
):
    return CategoriaService(db).listar_por_agente(
        id_agente=id_agente,
        activo=activo
    )

# ======================================================
# 🔹 Actualizar categoría
# ======================================================
@router.put(
    "/{id_categoria}",
    response_model=CategoriaResponse
)
def actualizar_categoria(
    id_categoria: int,
    data: CategoriaUpdate,
    db: Session = Depends(get_db)
):
    return CategoriaService(db).actualizar_categoria(
        id_categoria=id_categoria,
        data=data
    )

# ======================================================
# 🔹 Eliminar categoría
# ======================================================
@router.delete(
    "/{id_categoria}",
    status_code=status.HTTP_200_OK
)
def eliminar_categoria(
    id_categoria: int,
    db: Session = Depends(get_db)
):
    CategoriaService(db).eliminar_categoria(id_categoria)
    return {"detail": "Categoría eliminada correctamente"}
