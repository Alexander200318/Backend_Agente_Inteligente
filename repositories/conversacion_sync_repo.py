from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime, date
from models.conversacion_sync import ConversacionSync
from schemas.conversacion_sync_schemas import ConversacionSyncCreate, ConversacionSyncUpdate
from exceptions.base import *

class ConversacionSyncRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, conversacion_data: ConversacionSyncCreate) -> ConversacionSync:
        try:
            # Verificar si ya existe el ID de MongoDB
            existing = self.get_by_mongodb_id(conversacion_data.mongodb_conversation_id)
            if existing:
                raise AlreadyExistsException(
                    "Conversación",
                    "mongodb_id",
                    conversacion_data.mongodb_conversation_id
                )
            
            conversacion = ConversacionSync(**conversacion_data.dict())
            
            # Si no se especifica agente actual, usar el inicial
            if not conversacion.id_agente_actual:
                conversacion.id_agente_actual = conversacion.id_agente_inicial
            
            self.db.add(conversacion)
            self.db.commit()
            self.db.refresh(conversacion)
            return conversacion
        except IntegrityError:
            self.db.rollback()
            raise AlreadyExistsException("Conversación", "mongodb_id", "duplicado")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al crear conversación: {str(e)}")
    
    def get_by_id(self, id_conversacion_sync: int) -> ConversacionSync:
        conversacion = self.db.query(ConversacionSync).filter(
            ConversacionSync.id_conversacion_sync == id_conversacion_sync
        ).first()
        
        if not conversacion:
            raise NotFoundException("Conversación", id_conversacion_sync)
        return conversacion
    
    def get_by_mongodb_id(self, mongodb_id: str) -> Optional[ConversacionSync]:
        return self.db.query(ConversacionSync).filter(
            ConversacionSync.mongodb_conversation_id == mongodb_id
        ).first()
    
    def get_by_visitante(
        self,
        id_visitante: int,
        estado: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConversacionSync]:
        query = self.db.query(ConversacionSync).filter(
            ConversacionSync.id_visitante == id_visitante
        )
        
        if estado:
            query = query.filter(ConversacionSync.estado == estado)
        
        return query.order_by(ConversacionSync.fecha_inicio.desc()).offset(skip).limit(limit).all()
    
    def get_by_agente(
        self,
        id_agente: int,
        estado: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConversacionSync]:
        query = self.db.query(ConversacionSync).filter(
            (ConversacionSync.id_agente_inicial == id_agente) |
            (ConversacionSync.id_agente_actual == id_agente)
        )
        
        if estado:
            query = query.filter(ConversacionSync.estado == estado)
        
        return query.order_by(ConversacionSync.fecha_inicio.desc()).offset(skip).limit(limit).all()
    
    def get_activas(self, limit: int = 100) -> List[ConversacionSync]:
        return self.db.query(ConversacionSync).filter(
            ConversacionSync.estado == "activa"
        ).order_by(ConversacionSync.fecha_inicio.desc()).limit(limit).all()
    
    def update(self, id_conversacion_sync: int, conversacion_data: ConversacionSyncUpdate) -> ConversacionSync:
        try:
            conversacion = self.get_by_id(id_conversacion_sync)
            
            for field, value in conversacion_data.dict(exclude_unset=True).items():
                setattr(conversacion, field, value)
            
            # Actualizar última sincronización
            conversacion.ultima_sincronizacion = datetime.now()
            
            self.db.commit()
            self.db.refresh(conversacion)
            return conversacion
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar conversación: {str(e)}")
    
    def finalizar_conversacion(self, id_conversacion_sync: int) -> ConversacionSync:
        """Finalizar una conversación activa"""
        conversacion = self.get_by_id(id_conversacion_sync)
        
        if conversacion.estado != "activa":
            raise ValidationException(f"La conversación ya está en estado '{conversacion.estado}'")
        
        conversacion.estado = "finalizada"
        conversacion.fecha_fin = datetime.now()
        conversacion.ultima_sincronizacion = datetime.now()
        
        self.db.commit()
        self.db.refresh(conversacion)
        return conversacion
    
    def derivar_agente(self, id_conversacion_sync: int, id_nuevo_agente: int) -> ConversacionSync:
        """Derivar conversación a otro agente"""
        conversacion = self.get_by_id(id_conversacion_sync)
        
        if conversacion.estado != "activa":
            raise ValidationException("Solo se pueden derivar conversaciones activas")
        
        conversacion.id_agente_actual = id_nuevo_agente
        conversacion.ultima_sincronizacion = datetime.now()
        
        self.db.commit()
        self.db.refresh(conversacion)
        return conversacion
    
    def incrementar_mensajes(self, id_conversacion_sync: int, cantidad: int = 1) -> ConversacionSync:
        """Incrementar contador de mensajes"""
        conversacion = self.get_by_id(id_conversacion_sync)
        conversacion.total_mensajes += cantidad
        conversacion.ultima_sincronizacion = datetime.now()
        
        self.db.commit()
        self.db.refresh(conversacion)
        return conversacion
    
    def count(self, estado: Optional[str] = None) -> int:
        query = self.db.query(ConversacionSync)
        if estado:
            query = query.filter(ConversacionSync.estado == estado)
        return query.count()
    
    def get_estadisticas_por_fecha(self, fecha: date) -> dict:
        """Estadísticas de conversaciones por fecha"""
        result = self.db.query(
            func.count(ConversacionSync.id_conversacion_sync).label('total'),
            func.count(func.distinct(ConversacionSync.id_visitante)).label('visitantes_unicos'),
            func.avg(ConversacionSync.total_mensajes).label('mensajes_promedio')
        ).filter(
            func.date(ConversacionSync.fecha_inicio) == fecha
        ).first()
        
        return {
            "fecha": fecha.isoformat(),
            "total_conversaciones": result.total or 0,
            "visitantes_unicos": result.visitantes_unicos or 0,
            "mensajes_promedio": float(result.mensajes_promedio) if result.mensajes_promedio else 0
        }
