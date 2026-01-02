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
from auth.dependencies import get_current_user
from models.usuario import Usuario  

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
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crea una categoría con el usuario autenticado.
    El creado_por se obtiene automáticamente del token JWT.
    """
    data_dict = data.dict()
    data_dict['creado_por'] = current_user.id_usuario  
    
    return CategoriaService(db).crear_categoria_con_usuario(data_dict)

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
    """
    Lista todas las categorías con filtros opcionales.
    Excluye automáticamente las categorías eliminadas.
    """
    return CategoriaService(db).listar_categorias(
        activo=activo,
        id_agente=id_agente,
        incluir_eliminados=False  # ✅ SIEMPRE False (no eliminadas)
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
    """
    Lista categorías de un agente específico.
    Excluye automáticamente las categorías eliminadas.
    """
    return CategoriaService(db).listar_por_agente(
        id_agente=id_agente,
        activo=activo,
        incluir_eliminados=False  # ✅ SIEMPRE False (no eliminadas)
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
    current_user: Usuario = Depends(get_current_user),  
    db: Session = Depends(get_db)
):
    """
    Actualiza una categoría.
    Permite actualizar el campo 'eliminado' para restaurar o eliminar lógicamente.
    """
    data_dict = data.dict(exclude_unset=True)
    
    return CategoriaService(db).actualizar_categoria_con_usuario(
        id_categoria=id_categoria,
        data=data_dict
    )

# ======================================================
# 🔹 Eliminar categoría (ELIMINADO LÓGICO)
# ======================================================
@router.delete(
    "/{id_categoria}",
    status_code=status.HTTP_200_OK
)
def eliminar_categoria(
    id_categoria: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina una categoría de forma LÓGICA (marca eliminado=True).
    La categoría no se borra físicamente de la base de datos.
    Requiere autenticación.
    """
    CategoriaService(db).eliminar_categoria(id_categoria)
    return {
        "detail": "Categoría eliminada correctamente",
        "tipo": "eliminado_logico"
    }

# ======================================================
# 🔹 NUEVO: Restaurar categoría eliminada
# ======================================================
@router.post(
    "/{id_categoria}/restaurar",
    response_model=CategoriaResponse,
    status_code=status.HTTP_200_OK
)
def restaurar_categoria(
    id_categoria: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Restaura una categoría que fue eliminada lógicamente.
    Cambia eliminado=False.
    Solo para administradores.
    """
    return CategoriaService(db).restaurar_categoria(id_categoria)

# ======================================================
# 🔹 SUPERADMIN: Listar TODAS las categorías (incluyendo eliminadas)
# ======================================================
@router.get(
    "/admin/todas",
    response_model=List[CategoriaResponse]
)
def listar_todas_admin(
    activo: Optional[bool] = Query(None),
    id_agente: Optional[int] = Query(None),
    current_user: Usuario = Depends(get_current_user),  
    db: Session = Depends(get_db)
):
    """
    [ADMIN] Lista TODAS las categorías, incluyendo las eliminadas.
    Solo para administradores.
    """
    # TODO: Aquí puedes agregar un check de rol de admin
    # if current_user.rol != "admin":
    #     raise HTTPException(status_code=403, detail="No autorizado")
    
    return CategoriaService(db).listar_categorias(
        activo=activo,
        id_agente=id_agente,
        incluir_eliminados=True  # ✅ Incluye eliminadas
    )