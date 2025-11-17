from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional

from sqlalchemy.orm import Session

from database.database import get_db
from services.departamento_agente_service import DepartamentoAgenteService
from schemas.departamento_agente_schemas import DepartamentoAgenteCreate, DepartamentoAgenteResponse, DepartamentoAgenteUpdate


router = APIRouter(prefix="/departamento-agente", tags=["Departamento-Agente"])

@router.post("/", response_model=DepartamentoAgenteResponse, status_code=status.HTTP_201_CREATED)
def asignar_departamento_agente(data: DepartamentoAgenteCreate, db: Session = Depends(get_db)):
    """
    Asignar permisos heredados de un departamento sobre un agente.
    Los usuarios del departamento heredarán estos permisos por defecto.
    """
    service = DepartamentoAgenteService(db)
    return service.asignar_departamento_agente(data)

@router.get("/departamento/{id_departamento}", response_model=List[DepartamentoAgenteResponse])
def listar_agentes_departamento(
    id_departamento: int,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Listar todos los agentes asignados a un departamento"""
    service = DepartamentoAgenteService(db)
    return service.listar_por_departamento(id_departamento, activo)

@router.get("/agente/{id_agente}", response_model=List[DepartamentoAgenteResponse])
def listar_departamentos_agente(
    id_agente: int,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Listar todos los departamentos con permisos sobre un agente"""
    service = DepartamentoAgenteService(db)
    return service.listar_por_agente(id_agente, activo)

@router.get("/{id_depto_agente}", response_model=DepartamentoAgenteResponse)
def obtener_asignacion(id_depto_agente: int, db: Session = Depends(get_db)):
    """Obtener una asignación específica"""
    service = DepartamentoAgenteService(db)
    return service.obtener_asignacion(id_depto_agente)

@router.put("/{id_depto_agente}", response_model=DepartamentoAgenteResponse)
def actualizar_permisos(
    id_depto_agente: int,
    data: DepartamentoAgenteUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar permisos heredados del departamento"""
    service = DepartamentoAgenteService(db)
    return service.actualizar_permisos(id_depto_agente, data)

@router.delete("/{id_depto_agente}", status_code=status.HTTP_200_OK)
def revocar_acceso(id_depto_agente: int, db: Session = Depends(get_db)):
    """Revocar acceso del departamento al agente"""
    service = DepartamentoAgenteService(db)
    return service.revocar_acceso(id_depto_agente)