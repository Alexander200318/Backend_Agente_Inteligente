from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey, DECIMAL, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class MetricaDiariaAgente(Base):
    __tablename__ = "Metrica_Diaria_Agente"
    __table_args__ = (
        UniqueConstraint('id_agente', 'fecha', name='unique_agente_fecha'),
    )

    # Primary Key
    id_metrica = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Key
    id_agente = Column(
        Integer, 
        ForeignKey('Agente_Virtual.id_agente', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    fecha = Column(Date, nullable=False, index=True)
    
    # Volumen de interacciones
    visitantes_unicos = Column(Integer, default=0)
    conversaciones_iniciadas = Column(Integer, default=0)
    conversaciones_finalizadas = Column(Integer, default=0)
    conversaciones_abandonadas = Column(Integer, default=0)
    mensajes_enviados = Column(Integer, default=0)
    mensajes_recibidos = Column(Integer, default=0)
    
    # Derivaciones y escalamientos
    derivaciones_salientes = Column(Integer, default=0)
    derivaciones_entrantes = Column(Integer, default=0)
    escalamientos_humanos = Column(Integer, default=0)
    escalamientos_resueltos = Column(Integer, default=0)
    
    # Performance
    tiempo_respuesta_promedio_ms = Column(DECIMAL(10, 2))
    duracion_conversacion_promedio_segundos = Column(DECIMAL(10, 2))
    
    # Satisfacción
    satisfaccion_promedio = Column(DECIMAL(3, 2))
    total_calificaciones = Column(Integer, default=0)
    
    # Efectividad
    tasa_resolucion = Column(DECIMAL(5, 2))
    conversaciones_resueltas = Column(Integer, default=0)
    
    # Contenido más usado
    contenido_mas_usado_id = Column(
        Integer, 
        ForeignKey('Unidad_Contenido.id_contenido', ondelete='SET NULL')
    )
    veces_usado_contenido_top = Column(Integer, default=0)
    
    # Patrones de uso
    hora_pico = Column(Integer)
    conversaciones_hora_pico = Column(Integer, default=0)
    
    # Auditoría
    fecha_calculo = Column(DateTime, server_default=func.current_timestamp())
    
    # Relationships
    agente = relationship("AgenteVirtual", back_populates="metricas")
    contenido_mas_usado = relationship("UnidadContenido")

    def __repr__(self):
        return f"<MetricaDiariaAgente(agente_id={self.id_agente}, fecha={self.fecha})>"