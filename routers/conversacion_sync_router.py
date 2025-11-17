from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session

from database.database import get_db
from services.conversacion_sync_service import ConversacionSyncService
from schemas.conversacion_sync_schemas import ConversacionSyncResponse, ConversacionSyncCreate, ConversacionSyncUpdate

router = APIRouter(prefix="/conversaciones", tags=["Conversaciones"])

@router.post("/", response_model=ConversacionSyncResponse, status_code=status.HTTP_201_CREATED)
def crear_conversacion(conversacion: ConversacionSyncCreate, db: Session = Depends(get_db)):
    """
    Crear registro de sincronización de conversación.
    El mongodb_conversation_id debe ser el ObjectId de MongoDB (24 caracteres hex).
    """
    service = ConversacionSyncService(db)
    return service.crear_conversacion(conversacion)

@router.get("/activas", response_model=List[ConversacionSyncResponse])
def listar_conversaciones_activas(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Listar todas las conversaciones activas"""
    service = ConversacionSyncService(db)
    return service.listar_activas(limit)

@router.get("/estadisticas", response_model=dict)
def obtener_estadisticas_generales(db: Session = Depends(get_db)):
    """Estadísticas generales de conversaciones"""
    service = ConversacionSyncService(db)
    return service.obtener_estadisticas_generales()

@router.get("/estadisticas/fecha/{fecha}", response_model=dict)
def obtener_estadisticas_fecha(fecha: date, db: Session = Depends(get_db)):
    """Estadísticas de conversaciones por fecha específica"""
    service = ConversacionSyncService(db)
    return service.obtener_estadisticas_fecha(fecha)

@router.get("/visitante/{id_visitante}", response_model=List[ConversacionSyncResponse])
def listar_por_visitante(
    id_visitante: int,
    estado: Optional[str] = Query(None, pattern="^(activa|finalizada|abandonada|escalada_humano)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Listar conversaciones de un visitante"""
    service = ConversacionSyncService(db)
    return service.listar_por_visitante(id_visitante, estado, skip, limit)

@router.get("/agente/{id_agente}", response_model=List[ConversacionSyncResponse])
def listar_por_agente(
    id_agente: int,
    estado: Optional[str] = Query(None, pattern="^(activa|finalizada|abandonada|escalada_humano)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Listar conversaciones de un agente (inicial o actual)"""
    service = ConversacionSyncService(db)
    return service.listar_por_agente(id_agente, estado, skip, limit)

@router.get("/mongodb/{mongodb_id}", response_model=ConversacionSyncResponse)
def obtener_por_mongodb_id(mongodb_id: str, db: Session = Depends(get_db)):
    """Obtener conversación por su ID de MongoDB"""
    service = ConversacionSyncService(db)
    return service.obtener_por_mongodb_id(mongodb_id)

@router.get("/{id_conversacion_sync}", response_model=ConversacionSyncResponse)
def obtener_conversacion(id_conversacion_sync: int, db: Session = Depends(get_db)):
    """Obtener una conversación específica"""
    service = ConversacionSyncService(db)
    return service.obtener_conversacion(id_conversacion_sync)

@router.put("/{id_conversacion_sync}", response_model=ConversacionSyncResponse)
def actualizar_conversacion(
    id_conversacion_sync: int,
    conversacion: ConversacionSyncUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar datos de la conversación"""
    service = ConversacionSyncService(db)
    return service.actualizar_conversacion(id_conversacion_sync, conversacion)

@router.post("/{id_conversacion_sync}/finalizar", response_model=ConversacionSyncResponse)
def finalizar_conversacion(id_conversacion_sync: int, db: Session = Depends(get_db)):
    """Finalizar una conversación activa"""
    service = ConversacionSyncService(db)
    return service.finalizar_conversacion(id_conversacion_sync)

@router.post("/{id_conversacion_sync}/derivar/{id_nuevo_agente}", response_model=ConversacionSyncResponse)
def derivar_conversacion(
    id_conversacion_sync: int,
    id_nuevo_agente: int,
    db: Session = Depends(get_db)
):
    """Derivar conversación a otro agente"""
    service = ConversacionSyncService(db)
    return service.derivar_a_agente(id_conversacion_sync, id_nuevo_agente)

@router.post("/{id_conversacion_sync}/mensajes", response_model=ConversacionSyncResponse)
def registrar_mensajes(
    id_conversacion_sync: int,
    cantidad: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    """Incrementar contador de mensajes de la conversación"""
    service = ConversacionSyncService(db)
    return service.registrar_mensaje(id_conversacion_sync, cantidad)