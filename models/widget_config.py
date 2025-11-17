from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum

class PosicionWidgetEnum(str, enum.Enum):
    bottom_right = "bottom-right"
    bottom_left = "bottom-left"
    top_right = "top-right"
    top_left = "top-left"
    center = "center"

class TamanoWidgetEnum(str, enum.Enum):
    small = "small"
    medium = "medium"
    large = "large"

class AnimacionEntradaEnum(str, enum.Enum):
    fade = "fade"
    slide = "slide"
    bounce = "bounce"
    none = "none"

class WidgetConfig(Base):
    __tablename__ = "Widget_Config"

    # Primary Key
    id_widget = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Key
    id_agente = Column(
        Integer, 
        ForeignKey('Agente_Virtual.id_agente', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Identificación
    nombre_widget = Column(String(100), nullable=False)
    sitio_web = Column(String(255))
    dominio_permitido = Column(String(255), index=True)
    
    # Apariencia
    color_primario = Column(String(7), default='#3B82F6')
    color_secundario = Column(String(7), default='#1E40AF')
    color_fondo = Column(String(7), default='#FFFFFF')
    posicion = Column(Enum(PosicionWidgetEnum), default=PosicionWidgetEnum.bottom_right)
    tamano = Column(Enum(TamanoWidgetEnum), default=TamanoWidgetEnum.medium)
    
    # Elementos visuales
    mostrar_avatar = Column(Boolean, default=True)
    mostrar_nombre_agente = Column(Boolean, default=True)
    animacion_entrada = Column(Enum(AnimacionEntradaEnum), default=AnimacionEntradaEnum.slide)
    
    # Comportamiento
    autoabrir_despues_segundos = Column(Integer, default=0)
    mostrar_mensaje_bienvenida = Column(Boolean, default=True)
    permitir_adjuntos = Column(Boolean, default=False)
    permitir_audio = Column(Boolean, default=False)
    
    # Horarios
    respetar_horario = Column(Boolean, default=True)
    mensaje_fuera_horario = Column(Text)
    
    # Script de integración
    script_embed = Column(Text)
    
    # Estado
    activo = Column(Boolean, default=True, index=True)
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp())
    fecha_actualizacion = Column(DateTime, onupdate=func.current_timestamp())
    creado_por = Column(
        Integer, 
        ForeignKey('Usuario.id_usuario', ondelete='RESTRICT'), 
        nullable=False
    )
    
    # Relationships
    agente = relationship("AgenteVirtual", back_populates="widgets")
    creador = relationship("Usuario")

    def __repr__(self):
        return f"<WidgetConfig(id={self.id_widget}, nombre='{self.nombre_widget}', agente_id={self.id_agente})>"