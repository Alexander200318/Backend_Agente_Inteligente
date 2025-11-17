from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime, timedelta
from models.visitante_anonimo import VisitanteAnonimo
from models.conversacion_sync import ConversacionSync
from schemas.visitante_anonimo_schemas import VisitanteAnonimoCreate, VisitanteAnonimoUpdate
from exceptions.base import *

class VisitanteAnonimoRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, visitante_data: VisitanteAnonimoCreate) -> VisitanteAnonimo:
        try:
            # Verificar si ya existe el identificador de sesión
            existing = self.get_by_sesion(visitante_data.identificador_sesion)
            if existing:
                raise AlreadyExistsException(
                    "Visitante",
                    "sesión",
                    visitante_data.identificador_sesion[:20] + "..."
                )
            
            visitante = VisitanteAnonimo(**visitante_data.dict())
            self.db.add(visitante)
            self.db.commit()
            self.db.refresh(visitante)
            return visitante
        except IntegrityError:
            self.db.rollback()
            raise AlreadyExistsException("Visitante", "sesión", "duplicada")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al crear visitante: {str(e)}")
    
    def get_by_id(self, id_visitante: int) -> VisitanteAnonimo:
        visitante = self.db.query(VisitanteAnonimo).filter(
            VisitanteAnonimo.id_visitante == id_visitante
        ).first()
        
        if not visitante:
            raise NotFoundException("Visitante", id_visitante)
        return visitante
    
    def get_by_sesion(self, identificador_sesion: str) -> Optional[VisitanteAnonimo]:
        return self.db.query(VisitanteAnonimo).filter(
            VisitanteAnonimo.identificador_sesion == identificador_sesion
        ).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        dispositivo: Optional[str] = None,
        pais: Optional[str] = None,
        fecha_desde: Optional[datetime] = None
    ) -> List[VisitanteAnonimo]:
        query = self.db.query(VisitanteAnonimo)
        
        if dispositivo:
            query = query.filter(VisitanteAnonimo.dispositivo == dispositivo)
        if pais:
            query = query.filter(VisitanteAnonimo.pais == pais)
        if fecha_desde:
            query = query.filter(VisitanteAnonimo.primera_visita >= fecha_desde)
        
        return query.order_by(VisitanteAnonimo.primera_visita.desc()).offset(skip).limit(limit).all()
    
    def update(self, id_visitante: int, visitante_data: VisitanteAnonimoUpdate) -> VisitanteAnonimo:
        try:
            visitante = self.get_by_id(id_visitante)
            
            for field, value in visitante_data.dict(exclude_unset=True).items():
                setattr(visitante, field, value)
            
            self.db.commit()
            self.db.refresh(visitante)
            return visitante
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar visitante: {str(e)}")
    
    def registrar_actividad(self, id_visitante: int) -> VisitanteAnonimo:
        """Actualizar última visita"""
        visitante = self.get_by_id(id_visitante)
        visitante.ultima_visita = datetime.now()
        self.db.commit()
        self.db.refresh(visitante)
        return visitante
    
    def incrementar_conversaciones(self, id_visitante: int) -> VisitanteAnonimo:
        """Incrementar contador de conversaciones"""
        visitante = self.get_by_id(id_visitante)
        visitante.total_conversaciones += 1
        self.db.commit()
        self.db.refresh(visitante)
        return visitante
    
    def incrementar_mensajes(self, id_visitante: int, cantidad: int = 1) -> VisitanteAnonimo:
        """Incrementar contador de mensajes"""
        visitante = self.get_by_id(id_visitante)
        visitante.total_mensajes += cantidad
        self.db.commit()
        self.db.refresh(visitante)
        return visitante
    
    def get_estadisticas_visitante(self, id_visitante: int) -> dict:
        """Estadísticas del visitante"""
        visitante = self.get_by_id(id_visitante)
        
        conversaciones_activas = self.db.query(func.count(ConversacionSync.id_conversacion_sync)).filter(
            ConversacionSync.id_visitante == id_visitante,
            ConversacionSync.estado == "activa"
        ).scalar()
        
        conversaciones_finalizadas = self.db.query(func.count(ConversacionSync.id_conversacion_sync)).filter(
            ConversacionSync.id_visitante == id_visitante,
            ConversacionSync.estado == "finalizada"
        ).scalar()
        
        return {
            "conversaciones_activas": conversaciones_activas or 0,
            "conversaciones_finalizadas": conversaciones_finalizadas or 0
        }
    
    def count(self, dispositivo: Optional[str] = None) -> int:
        query = self.db.query(VisitanteAnonimo)
        if dispositivo:
            query = query.filter(VisitanteAnonimo.dispositivo == dispositivo)
        return query.count()
    
    def get_visitantes_activos(self, minutos: int = 30) -> List[VisitanteAnonimo]:
        """Obtener visitantes activos en los últimos X minutos"""
        tiempo_limite = datetime.now() - timedelta(minutes=minutos)
        return self.db.query(VisitanteAnonimo).filter(
            VisitanteAnonimo.ultima_visita >= tiempo_limite
        ).all()
