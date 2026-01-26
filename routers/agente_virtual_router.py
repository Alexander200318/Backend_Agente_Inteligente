# agente_virtual_router.py
from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from database.database import get_db
from services.agente_virtual_service import AgenteVirtualService
from schemas.agente_virtual_schemas import AgenteVirtualResponse, AgenteVirtualCreate, AgenteVirtualUpdate

router = APIRouter(prefix="/agentes", tags=["Agentes Virtuales"])

@router.post("/", response_model=AgenteVirtualResponse, status_code=status.HTTP_201_CREATED)
def crear_agente(agente: AgenteVirtualCreate, db: Session = Depends(get_db)):
    """
    Crear un nuevo agente virtual:
    - **nombre_agente**: nombre descriptivo (mínimo 5 caracteres)
    - **tipo_agente**: router, especializado o hibrido
    - **temperatura**: 0-2 (creatividad del modelo IA)
    - **max_tokens**: 100-8000 (longitud de respuestas)
    """
    service = AgenteVirtualService(db)
    return service.crear_agente(agente)

@router.get("/", response_model=List[AgenteVirtualResponse])
def listar_agentes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    activo: Optional[bool] = None,
    tipo_agente: Optional[str] = Query(None, pattern="^(router|especializado|hibrido)$"),
    id_departamento: Optional[int] = None,
    incluir_eliminados: bool = Query(False, description="Incluir agentes eliminados"),
    db: Session = Depends(get_db)
):
    """
    Listar agentes con filtros opcionales.
    Por defecto NO muestra agentes eliminados.
    """
    service = AgenteVirtualService(db)
    return service.listar_agentes(skip, limit, activo, tipo_agente, id_departamento, incluir_eliminados)

@router.get("/estadisticas", response_model=dict)
def obtener_estadisticas_generales(db: Session = Depends(get_db)):
    """Estadísticas generales de todos los agentes activos (excluye eliminados)"""
    service = AgenteVirtualService(db)
    return service.obtener_estadisticas_generales()

@router.get("/buscar", response_model=List[AgenteVirtualResponse])
def buscar_agentes(
    q: str = Query(..., min_length=2),
    incluir_eliminados: bool = Query(False, description="Incluir agentes eliminados en la búsqueda"),
    db: Session = Depends(get_db)
):
    """Buscar agentes por nombre o área de especialidad"""
    service = AgenteVirtualService(db)
    return service.buscar_agentes(q, incluir_eliminados)

@router.get("/{id_agente}", response_model=AgenteVirtualResponse)
def obtener_agente(
    id_agente: int,
    incluir_eliminados: bool = Query(False, description="Permitir obtener agente eliminado"),
    db: Session = Depends(get_db)
):
    """Obtener un agente específico por ID. Por defecto NO incluye eliminados."""
    service = AgenteVirtualService(db)
    return service.obtener_agente(id_agente, incluir_eliminados)

@router.get("/{id_agente}/estadisticas", response_model=dict)
def obtener_estadisticas_agente(id_agente: int, db: Session = Depends(get_db)):
    """
    Obtener estadísticas del agente:
    - Usuarios asignados
    - Categorías
    - Contenidos
    - Conversaciones
    
    Solo disponible para agentes NO eliminados.
    """
    service = AgenteVirtualService(db)
    return service.obtener_estadisticas(id_agente)

@router.put("/{id_agente}", response_model=AgenteVirtualResponse)
def actualizar_agente(
    id_agente: int,
    agente: AgenteVirtualUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar configuración del agente.
    Solo permite actualizar agentes NO eliminados.
    """
    service = AgenteVirtualService(db)
    return service.actualizar_agente(id_agente, agente)

@router.patch("/{id_agente}/desactivar", status_code=status.HTTP_200_OK)
def desactivar_agente(id_agente: int, db: Session = Depends(get_db)):
    """
    Desactivar agente (activo=False).
    El agente sigue existiendo pero no está operativo.
    """
    service = AgenteVirtualService(db)
    return service.desactivar_agente(id_agente)

@router.patch("/{id_agente}/activar", status_code=status.HTTP_200_OK)
def activar_agente(id_agente: int, db: Session = Depends(get_db)):
    """
    Activar agente (activo=True).
    Reactiva un agente previamente desactivado.
    """
    service = AgenteVirtualService(db)
    return service.activar_agente(id_agente)

@router.delete("/{id_agente}", status_code=status.HTTP_200_OK)
def eliminar_agente(
    id_agente: int,
    eliminado_por: Optional[int] = Query(None, description="ID del usuario que elimina"),
    db: Session = Depends(get_db)
):
    """
    Soft delete: Marca el agente como eliminado.
    - Establece eliminado=True
    - Registra fecha_eliminacion
    - Registra eliminado_por (si está disponible)
    - También desactiva el agente (activo=False)
    
    El agente no se elimina físicamente, solo se marca como eliminado.
    """
    service = AgenteVirtualService(db)
    return service.eliminar_agente(id_agente, eliminado_por)

@router.patch("/{id_agente}/restaurar", status_code=status.HTTP_200_OK)
def restaurar_agente(id_agente: int, db: Session = Depends(get_db)):
    """
    Restaurar un agente previamente eliminado (soft delete reverso).
    - Establece eliminado=False
    - Limpia fecha_eliminacion y eliminado_por
    - NO cambia el estado 'activo' automáticamente
    """
    service = AgenteVirtualService(db)
    return service.restaurar_agente(id_agente)

@router.delete("/{id_agente}/permanente", status_code=status.HTTP_200_OK)
def eliminar_agente_permanentemente(id_agente: int, db: Session = Depends(get_db)):
    """
    ⚠️ HARD DELETE - Elimina físicamente el registro de la base de datos.
    Esta acción es IRREVERSIBLE.
    
    Usar solo en casos excepcionales y con extrema precaución.
    """
    service = AgenteVirtualService(db)
    return service.eliminar_agente_permanentemente(id_agente)