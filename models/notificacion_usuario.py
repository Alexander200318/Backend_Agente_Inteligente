# notificacion_usuario.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum

class TipoNotificacionEnum(str, enum.Enum):
    info = "info"
    alerta = "alerta"
    error = "error"
    exito = "exito"
    urgente = "urgente"

class NotificacionUsuario(Base):
    __tablename__ = "Notificacion_Usuario"
    __table_args__ = (
        Index('idx_no_leidas', 'id_usuario', 'leida', 'fecha_creacion'),
    )

    # Primary Key
    id_notificacion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Keys
    id_usuario = Column(
        Integer, 
        ForeignKey('Usuario.id_usuario', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    id_agente = Column(
        Integer, 
        ForeignKey('Agente_Virtual.id_agente', ondelete='SET NULL')
    )
    
    # Tipo y contenido
    tipo = Column(Enum(TipoNotificacionEnum), default=TipoNotificacionEnum.info, index=True)
    titulo = Column(String(200), nullable=False)
    mensaje = Column(Text, nullable=False)
    
    # Metadata
    icono = Column(String(50))
    url_accion = Column(String(255))
    
    # Estado
    leida = Column(Boolean, default=False, index=True)
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp(), index=True)
    fecha_lectura = Column(DateTime)
    
    # Datos adicionales (JSON)
    datos_adicionales = Column(Text)
    
    # Relationships
    usuario = relationship("Usuario")
    agente = relationship("AgenteVirtual")

    def __repr__(self):
        return f"<NotificacionUsuario(id={self.id_notificacion}, usuario_id={self.id_usuario}, tipo='{self.tipo}')>"