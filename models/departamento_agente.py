from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class DepartamentoAgente(Base):
    __tablename__ = "Departamento_Agente"
    __table_args__ = (
        UniqueConstraint('id_departamento', 'id_agente', name='unique_depto_agente'),
    )

    # Primary Key
    id_depto_agente = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Keys
    id_departamento = Column(
        Integer, 
        ForeignKey('Departamento.id_departamento', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    id_agente = Column(
        Integer, 
        ForeignKey('Agente_Virtual.id_agente', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Permisos heredados por defecto para usuarios del departamento
    puede_ver_contenido = Column(Boolean, default=True)
    puede_crear_contenido = Column(Boolean, default=True)
    puede_editar_contenido = Column(Boolean, default=False)
    puede_eliminar_contenido = Column(Boolean, default=False)
    puede_ver_metricas = Column(Boolean, default=True)
    
    # Información de asignación
    fecha_asignacion = Column(DateTime, server_default=func.current_timestamp())
    asignado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))
    activo = Column(Boolean, default=True)
    
    # Relationships
    departamento = relationship("Departamento")
    agente = relationship("AgenteVirtual")
    asignador = relationship("Usuario")

    def __repr__(self):
        return f"<DepartamentoAgente(depto_id={self.id_departamento}, agente_id={self.id_agente})>"