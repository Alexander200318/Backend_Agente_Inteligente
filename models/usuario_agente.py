from sqlalchemy import Column, Integer, DateTime, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class UsuarioAgente(Base):
    __tablename__ = "Usuario_Agente"
    __table_args__ = (
        UniqueConstraint('id_usuario', 'id_agente', name='unique_usuario_agente'),
    )

    # Primary Key
    id_usuario_agente = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Keys
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='CASCADE'), nullable=False, index=True)
    id_agente = Column(Integer, ForeignKey('Agente_Virtual.id_agente', ondelete='CASCADE'), nullable=False, index=True)
    
    # Permisos sobre contenido
    puede_ver_contenido = Column(Boolean, default=True)
    puede_crear_contenido = Column(Boolean, default=True)
    puede_editar_contenido = Column(Boolean, default=True)
    puede_eliminar_contenido = Column(Boolean, default=False)
    puede_publicar_contenido = Column(Boolean, default=False)
    
    # Permisos sobre métricas
    puede_ver_metricas = Column(Boolean, default=True)
    puede_exportar_datos = Column(Boolean, default=False)
    
    # Permisos sobre configuración
    puede_configurar_agente = Column(Boolean, default=False)
    puede_gestionar_permisos = Column(Boolean, default=False)
    puede_gestionar_categorias = Column(Boolean, default=False)
    
    # Permisos sobre widgets
    puede_gestionar_widgets = Column(Boolean, default=False)
    
    # Información de asignación
    fecha_asignacion = Column(DateTime, server_default=func.current_timestamp())
    fecha_expiracion = Column(DateTime)
    asignado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))
    notas = Column(Text)
    activo = Column(Boolean, default=True, index=True)
    
    # Relationships
    usuario = relationship("Usuario", foreign_keys=[id_usuario], back_populates="agentes_asignados")
    agente = relationship("AgenteVirtual", back_populates="usuarios_asignados")
    asignador = relationship("Usuario", foreign_keys=[asignado_por])

    def __repr__(self):
        return f"<UsuarioAgente(usuario_id={self.id_usuario}, agente_id={self.id_agente})>"