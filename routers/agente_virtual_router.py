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
    db: Session = Depends(get_db)
):
    """Listar agentes con filtros opcionales"""
    service = AgenteVirtualService(db)
    return service.listar_agentes(skip, limit, activo, tipo_agente, id_departamento)

@router.get("/estadisticas", response_model=dict)
def obtener_estadisticas_generales(db: Session = Depends(get_db)):
    """Estadísticas generales de todos los agentes"""
    service = AgenteVirtualService(db)
    return service.obtener_estadisticas_generales()

@router.get("/buscar", response_model=List[AgenteVirtualResponse])
def buscar_agentes(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db)
):
    """Buscar agentes por nombre o área de especialidad"""
    service = AgenteVirtualService(db)
    return service.buscar_agentes(q)

@router.get("/{id_agente}", response_model=AgenteVirtualResponse)
def obtener_agente(id_agente: int, db: Session = Depends(get_db)):
    """Obtener un agente específico por ID"""
    service = AgenteVirtualService(db)
    return service.obtener_agente(id_agente)

@router.get("/{id_agente}/estadisticas", response_model=dict)
def obtener_estadisticas_agente(id_agente: int, db: Session = Depends(get_db)):
    """
    Obtener estadísticas del agente:
    - Usuarios asignados
    - Categorías
    - Contenidos
    - Conversaciones
    """
    service = AgenteVirtualService(db)
    return service.obtener_estadisticas(id_agente)

@router.put("/{id_agente}", response_model=AgenteVirtualResponse)
def actualizar_agente(
    id_agente: int,
    agente: AgenteVirtualUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar configuración del agente"""
    service = AgenteVirtualService(db)
    return service.actualizar_agente(id_agente, agente)

@router.delete("/{id_agente}", status_code=status.HTTP_200_OK)
def eliminar_agente(id_agente: int, db: Session = Depends(get_db)):
    """
    Desactivar agente:
    - No puede tener contenidos asociados
    - Soft delete (no elimina físicamente)
    """
    service = AgenteVirtualService(db)
    return service.eliminar_agente(id_agente)