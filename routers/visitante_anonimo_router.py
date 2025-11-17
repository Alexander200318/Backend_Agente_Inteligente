from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from datetime import  datetime

from sqlalchemy.orm import Session

from database.database import get_db
from services.visitante_anonimo_service import VisitanteAnonimoService
from schemas.visitante_anonimo_schemas import VisitanteAnonimoResponse, VisitanteAnonimoCreate, VisitanteAnonimoUpdate

router = APIRouter(prefix="/visitantes", tags=["Visitantes Anónimos"])

@router.post("/", response_model=VisitanteAnonimoResponse, status_code=status.HTTP_201_CREATED)
def crear_visitante(visitante: VisitanteAnonimoCreate, db: Session = Depends(get_db)):
    """
    Registrar un nuevo visitante anónimo.
    Se crea cuando un usuario accede al chatbot sin autenticarse.
    """
    service = VisitanteAnonimoService(db)
    return service.crear_visitante(visitante)

@router.get("/", response_model=List[VisitanteAnonimoResponse])
def listar_visitantes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    dispositivo: Optional[str] = Query(None, pattern="^(desktop|mobile|tablet)$"),
    pais: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Listar visitantes con filtros opcionales"""
    service = VisitanteAnonimoService(db)
    return service.listar_visitantes(skip, limit, dispositivo, pais, fecha_desde)

@router.get("/estadisticas", response_model=dict)
def obtener_estadisticas_generales(db: Session = Depends(get_db)):
    """Estadísticas generales de visitantes"""
    service = VisitanteAnonimoService(db)
    return service.obtener_estadisticas_generales()

@router.get("/activos", response_model=List[VisitanteAnonimoResponse])
def obtener_visitantes_activos(
    minutos: int = Query(30, ge=1, le=1440),
    db: Session = Depends(get_db)
):
    """Obtener visitantes activos en los últimos X minutos"""
    service = VisitanteAnonimoService(db)
    return service.obtener_visitantes_activos(minutos)

@router.get("/sesion/{identificador_sesion}", response_model=VisitanteAnonimoResponse)
def obtener_por_sesion(identificador_sesion: str, db: Session = Depends(get_db)):
    """Obtener visitante por su identificador de sesión"""
    service = VisitanteAnonimoService(db)
    return service.obtener_por_sesion(identificador_sesion)

@router.get("/{id_visitante}", response_model=VisitanteAnonimoResponse)
def obtener_visitante(id_visitante: int, db: Session = Depends(get_db)):
    """Obtener un visitante específico"""
    service = VisitanteAnonimoService(db)
    return service.obtener_visitante(id_visitante)

@router.get("/{id_visitante}/estadisticas", response_model=dict)
def obtener_estadisticas_visitante(id_visitante: int, db: Session = Depends(get_db)):
    """Obtener estadísticas detalladas del visitante"""
    service = VisitanteAnonimoService(db)
    return service.obtener_estadisticas_visitante(id_visitante)

@router.put("/{id_visitante}", response_model=VisitanteAnonimoResponse)
def actualizar_visitante(
    id_visitante: int,
    visitante: VisitanteAnonimoUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar información del visitante"""
    service = VisitanteAnonimoService(db)
    return service.actualizar_visitante(id_visitante, visitante)

@router.post("/{id_visitante}/actividad", response_model=VisitanteAnonimoResponse)
def registrar_actividad(id_visitante: int, db: Session = Depends(get_db)):
    """Registrar actividad del visitante (actualizar última visita)"""
    service = VisitanteAnonimoService(db)
    return service.registrar_actividad(id_visitante)

@router.post("/{id_visitante}/nueva-conversacion", response_model=VisitanteAnonimoResponse)
def incrementar_conversacion(id_visitante: int, db: Session = Depends(get_db)):
    """Incrementar contador de conversaciones"""
    service = VisitanteAnonimoService(db)
    return service.incrementar_conversacion(id_visitante)

@router.post("/{id_visitante}/mensajes", response_model=VisitanteAnonimoResponse)
def incrementar_mensajes(
    id_visitante: int,
    cantidad: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    """Incrementar contador de mensajes"""
    service = VisitanteAnonimoService(db)
    return service.incrementar_mensajes(id_visitante, cantidad)