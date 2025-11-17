from fastapi import APIRouter, Depends, Query


from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.metrica_diaria_agente_service import MetricaDiariaAgenteService
from schemas.metrica_diaria_agente_schemas import MetricaDiariaAgenteResponse, MetricaDiariaAgenteCreate

from datetime import date




router = APIRouter(prefix="/metricas/agentes", tags=["Métricas Agentes"])

@router.post("/", response_model=MetricaDiariaAgenteResponse, status_code=201)
def registrar_metrica(data: MetricaDiariaAgenteCreate, db: Session = Depends(get_db)):
    return MetricaDiariaAgenteService(db).registrar_metrica(data)

@router.get("/{id_agente}", response_model=List[MetricaDiariaAgenteResponse])
def obtener_metricas(
    id_agente: int,
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    return MetricaDiariaAgenteService(db).obtener_metricas_agente(id_agente, fecha_inicio, fecha_fin)

@router.get("/{id_agente}/resumen", response_model=dict)
def obtener_resumen(
    id_agente: int,
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    db: Session = Depends(get_db)
):
    return MetricaDiariaAgenteService(db).obtener_resumen_agente(id_agente, fecha_inicio, fecha_fin)

