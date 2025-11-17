from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class MetricaContenido(Base):
    __tablename__ = "Metrica_Contenido"
    __table_args__ = (
        UniqueConstraint('id_contenido', 'fecha', name='unique_contenido_fecha'),
    )

    # Primary Key
    id_metrica_contenido = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Key
    id_contenido = Column(
        Integer, 
        ForeignKey('Unidad_Contenido.id_contenido', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    fecha = Column(Date, nullable=False, index=True)
    
    # Uso del contenido
    veces_usado_dia = Column(Integer, default=0)
    veces_util_dia = Column(Integer, default=0)
    veces_no_util_dia = Column(Integer, default=0)
    
    # Alcance
    total_agentes_usaron = Column(Integer, default=0)
    conversaciones_donde_usado = Column(Integer, default=0)
    
    # Auditoría
    fecha_calculo = Column(DateTime, server_default=func.current_timestamp())
    
    # Relationships
    contenido = relationship("UnidadContenido", back_populates="metricas")

    def __repr__(self):
        return f"<MetricaContenido(contenido_id={self.id_contenido}, fecha={self.fecha})>"