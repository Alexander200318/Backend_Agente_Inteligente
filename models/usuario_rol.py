from sqlalchemy import Column, Integer, DateTime, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class UsuarioRol(Base):
    __tablename__ = "Usuario_Rol"
    __table_args__ = (
        UniqueConstraint('id_usuario', 'id_rol', name='unique_usuario_rol'),
    )

    # Primary Key
    id_usuario_rol = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Keys
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='CASCADE'), nullable=False, index=True)
    id_rol = Column(Integer, ForeignKey('Rol.id_rol', ondelete='CASCADE'), nullable=False, index=True)
    
    # Información de asignación
    fecha_asignacion = Column(DateTime, server_default=func.current_timestamp())
    fecha_expiracion = Column(DateTime)
    asignado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))
    motivo = Column(Text)
    activo = Column(Boolean, default=True, index=True)
    
    # Relationships
    usuario = relationship(
        "Usuario", 
        foreign_keys=[id_usuario], 
        back_populates="roles"
    )
    rol = relationship("Rol", back_populates="usuarios_rol")
    asignador = relationship(
        "Usuario", 
        foreign_keys=[asignado_por]
    )

    def __repr__(self):
        return f"<UsuarioRol(usuario_id={self.id_usuario}, rol_id={self.id_rol})>"