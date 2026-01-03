from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum

class EstadoContenidoEnum(str, enum.Enum):
    borrador = "borrador"
    revision = "revision"
    activo = "activo"
    inactivo = "inactivo"
    archivado = "archivado"

class UnidadContenido(Base):
    __tablename__ = "Unidad_Contenido"
    __table_args__ = (
        Index('idx_agente_estado_prioridad', 'id_agente', 'estado', 'prioridad'),
        Index('idx_fulltext', 'titulo', 'contenido', 'resumen', mysql_prefix='FULLTEXT'),
        Index('idx_eliminado', 'eliminado'),  # 🔥 NUEVO: Índice para soft delete
    )

    # Primary Key
    id_contenido = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Keys
    id_agente = Column(
        Integer, 
        ForeignKey('Agente_Virtual.id_agente', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    id_categoria = Column(
        Integer, 
        ForeignKey('Categoria.id_categoria', ondelete='RESTRICT'), 
        nullable=False, 
        index=True
    )
    id_departamento = Column(
        Integer, 
        ForeignKey('Departamento.id_departamento', ondelete='SET NULL'),
        index=True,
        comment='Departamento responsable del contenido'
    )
    
    # Contenido principal
    titulo = Column(String(200), nullable=False)
    contenido = Column(Text, nullable=False)
    resumen = Column(Text)
    
    # Metadata para búsqueda
    palabras_clave = Column(Text)
    etiquetas = Column(Text)
    prioridad = Column(Integer, default=5, index=True)
    
    # Recursos adicionales
    archivos_adjuntos = Column(Text)
    imagenes = Column(Text)
    enlaces_externos = Column(Text)
    
    # Vigencia temporal
    fecha_vigencia_inicio = Column(Date, index=True)
    fecha_vigencia_fin = Column(Date, index=True)
    mostrar_fecha_vigencia = Column(Boolean, default=False)
    
    # Versionado
    version = Column(Integer, default=1)
    
    # Estado del contenido
    estado = Column(Enum(EstadoContenidoEnum), default=EstadoContenidoEnum.borrador, index=True)
    
    # 🔥 SOFT DELETE - Campos nuevos
    eliminado = Column(Boolean, default=False, nullable=False, index=True, 
        comment='Indica si el contenido fue eliminado lógicamente')
    fecha_eliminacion = Column(DateTime, nullable=True, 
        comment='Fecha y hora de eliminación')
    eliminado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'), 
        nullable=True, 
        comment='Usuario que eliminó el contenido')
    
    # Auditoría
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp())
    fecha_actualizacion = Column(DateTime, onupdate=func.current_timestamp())
    creado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='RESTRICT'), nullable=True)
    actualizado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'), nullable=True)
    revisado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'), nullable=True)
    publicado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'), nullable=True)
    fecha_publicacion = Column(DateTime)
    
    # Gestión de revisiones
    notas_internas = Column(Text)
    requiere_revision = Column(Boolean, default=False)
    fecha_proxima_revision = Column(Date)
    
    # Relationships
    agente = relationship("AgenteVirtual", back_populates="contenidos")
    categoria = relationship("Categoria", back_populates="contenidos")
    departamento = relationship("Departamento", back_populates="contenidos")
    creador = relationship("Usuario", foreign_keys=[creado_por])
    actualizador = relationship("Usuario", foreign_keys=[actualizado_por])
    revisor = relationship("Usuario", foreign_keys=[revisado_por])
    publicador = relationship("Usuario", foreign_keys=[publicado_por])
    eliminador = relationship("Usuario", foreign_keys=[eliminado_por])  # 🔥 NUEVO
    metricas = relationship("MetricaContenido", back_populates="contenido", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UnidadContenido(id={self.id_contenido}, titulo='{self.titulo}', estado='{self.estado}', eliminado={self.eliminado})>"