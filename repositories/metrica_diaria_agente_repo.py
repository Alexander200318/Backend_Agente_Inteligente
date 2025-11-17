from sqlalchemy.orm import Session
from sqlalchemy import func
from models.metrica_diaria_agente import MetricaDiariaAgente
from exceptions.base import *

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from schemas.metrica_diaria_agente_schemas import MetricaDiariaAgenteCreate
from typing import Optional
from datetime import date



class MetricaDiariaAgenteRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create_or_update(self, data: MetricaDiariaAgenteCreate):
        try:
            # Buscar métrica existente
            metrica = self.db.query(MetricaDiariaAgente).filter(
                MetricaDiariaAgente.id_agente == data.id_agente,
                MetricaDiariaAgente.fecha == data.fecha
            ).first()
            
            if metrica:
                # Actualizar
                for field, value in data.dict().items():
                    if field not in ['id_agente', 'fecha']:
                        setattr(metrica, field, value)
            else:
                # Crear nueva
                metrica = MetricaDiariaAgente(**data.dict())
                self.db.add(metrica)
            
            self.db.commit()
            self.db.refresh(metrica)
            return metrica
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def get_by_agente_fecha(self, id_agente: int, fecha: date):
        return self.db.query(MetricaDiariaAgente).filter(
            MetricaDiariaAgente.id_agente == id_agente,
            MetricaDiariaAgente.fecha == fecha
        ).first()
    
    def get_by_agente(self, id_agente: int, fecha_inicio: Optional[date] = None, fecha_fin: Optional[date] = None):
        query = self.db.query(MetricaDiariaAgente).filter(MetricaDiariaAgente.id_agente == id_agente)
        
        if fecha_inicio:
            query = query.filter(MetricaDiariaAgente.fecha >= fecha_inicio)
        if fecha_fin:
            query = query.filter(MetricaDiariaAgente.fecha <= fecha_fin)
        
        return query.order_by(MetricaDiariaAgente.fecha.desc()).all()
    
    def get_resumen_agente(self, id_agente: int, fecha_inicio: date, fecha_fin: date):
        """Obtiene resumen agregado de métricas"""
        result = self.db.query(
            func.sum(MetricaDiariaAgente.visitantes_unicos).label('total_visitantes'),
            func.sum(MetricaDiariaAgente.conversaciones_iniciadas).label('total_conversaciones'),
            func.avg(MetricaDiariaAgente.satisfaccion_promedio).label('satisfaccion_promedio'),
            func.avg(MetricaDiariaAgente.tiempo_respuesta_promedio_ms).label('tiempo_respuesta_promedio')
        ).filter(
            MetricaDiariaAgente.id_agente == id_agente,
            MetricaDiariaAgente.fecha >= fecha_inicio,
            MetricaDiariaAgente.fecha <= fecha_fin
        ).first()
        
        return {
            "total_visitantes": result.total_visitantes or 0,
            "total_conversaciones": result.total_conversaciones or 0,
            "satisfaccion_promedio": float(result.satisfaccion_promedio) if result.satisfaccion_promedio else 0,
            "tiempo_respuesta_promedio_ms": float(result.tiempo_respuesta_promedio) if result.tiempo_respuesta_promedio else 0
        }