# conversacion_sync.py
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum

class EstadoConversacionEnum(str, enum.Enum):
    activa = "activa"
    finalizada = "finalizada"
    abandonada = "abandonada"
    escalada_humano = "escalada_humano"

class ConversacionSync(Base):
    __tablename__ = "Conversacion_Sync"

    # Primary Key
    id_conversacion_sync = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Identificador de MongoDB
    mongodb_conversation_id = Column(String(24), unique=True, nullable=False, index=True)
    
    # Foreign Keys
    id_visitante = Column(
        Integer, 
        ForeignKey('Visitante_Anonimo.id_visitante', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    id_agente_inicial = Column(
        Integer, 
        ForeignKey('Agente_Virtual.id_agente', ondelete='RESTRICT'), 
        nullable=False, 
        index=True
    )
    id_agente_actual = Column(
        Integer, 
        ForeignKey('Agente_Virtual.id_agente', ondelete='RESTRICT')
    )
    
    # Estado de la conversación
    estado = Column(Enum(EstadoConversacionEnum), default=EstadoConversacionEnum.activa, index=True)
    fecha_inicio = Column(DateTime, server_default=func.current_timestamp(), index=True)
    fecha_fin = Column(DateTime)
    
    # Métricas
    total_mensajes = Column(Integer, default=0)
    requirio_atencion_humana = Column(Boolean, default=False)
    
    # Sincronización
    ultima_sincronizacion = Column(DateTime, server_default=func.current_timestamp())
    
    # Relationships
    visitante = relationship("VisitanteAnonimo", back_populates="conversaciones")
    agente_inicial = relationship(
        "AgenteVirtual", 
        foreign_keys=[id_agente_inicial],
        back_populates="conversaciones_iniciadas"
    )
    agente_actual = relationship(
        "AgenteVirtual",
        foreign_keys=[id_agente_actual],
        back_populates="conversaciones_actuales"
    )

    def __repr__(self):
        return f"<ConversacionSync(id={self.id_conversacion_sync}, mongodb_id='{self.mongodb_conversation_id}', estado='{self.estado}')>"