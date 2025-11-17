
from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.metrica_contenido_service import MetricaContenidoService
from schemas.metrica_contenido_schemas import MetricaContenidoResponse, MetricaContenidoCreate

from datetime import date



router = APIRouter(prefix="/metricas/contenidos", tags=["Métricas Contenidos"])

@router.post("/", response_model=MetricaContenidoResponse, status_code=201)
def registrar_metrica(data: MetricaContenidoCreate, db: Session = Depends(get_db)):
    return MetricaContenidoService(db).registrar_metrica(data)

@router.get("/{id_contenido}", response_model=List[MetricaContenidoResponse])
def obtener_metricas(
    id_contenido: int,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    db: Session = Depends(get_db)
):
    return MetricaContenidoService(db).obtener_metricas_contenido(id_contenido, fecha_inicio, fecha_fin)

@router.get("/top/mas-usados", response_model=List[dict])
def obtener_top_contenidos(limit: int = Query(10, le=50), db: Session = Depends(get_db)):
    return MetricaContenidoService(db).obtener_top_contenidos(limit)