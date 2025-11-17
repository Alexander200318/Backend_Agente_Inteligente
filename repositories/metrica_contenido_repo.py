from models.metrica_contenido import MetricaContenido

from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from schemas.metrica_contenido_schemas import MetricaContenidoCreate
from exceptions.base import (

    DatabaseException
)
from datetime import date, datetime

class MetricaContenidoRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create_or_update(self, data: MetricaContenidoCreate):
        try:
            metrica = self.db.query(MetricaContenido).filter(
                MetricaContenido.id_contenido == data.id_contenido,
                MetricaContenido.fecha == data.fecha
            ).first()
            
            if metrica:
                for field, value in data.dict().items():
                    if field not in ['id_contenido', 'fecha']:
                        setattr(metrica, field, value)
            else:
                metrica = MetricaContenido(**data.dict())
                self.db.add(metrica)
            
            self.db.commit()
            self.db.refresh(metrica)
            return metrica
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def get_by_contenido(self, id_contenido: int, fecha_inicio: Optional[date] = None, fecha_fin: Optional[date] = None):
        query = self.db.query(MetricaContenido).filter(MetricaContenido.id_contenido == id_contenido)
        
        if fecha_inicio:
            query = query.filter(MetricaContenido.fecha >= fecha_inicio)
        if fecha_fin:
            query = query.filter(MetricaContenido.fecha <= fecha_fin)
        
        return query.order_by(MetricaContenido.fecha.desc()).all()
    
    def get_contenidos_mas_usados(self, limit: int = 10):
        """Top contenidos por uso"""
        return self.db.query(
            MetricaContenido.id_contenido,
            func.sum(MetricaContenido.veces_usado_dia).label('total_usos')
        ).group_by(
            MetricaContenido.id_contenido
        ).order_by(
            func.sum(MetricaContenido.veces_usado_dia).desc()
        ).limit(limit).all()
