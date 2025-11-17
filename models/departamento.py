from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class Departamento(Base):
    __tablename__ = "Departamento"

    # Primary Key
    id_departamento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Información básica
    nombre = Column(String(100), unique=True, nullable=False, index=True)
    descripcion = Column(Text)
    codigo = Column(String(20), unique=True, index=True)
    email = Column(String(150))
    telefono = Column(String(20))
    ubicacion = Column(String(255))
    facultad = Column(String(100), index=True)
    
    # Jefe de departamento
    jefe_departamento = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))
    
    # Estado
    activo = Column(Boolean, default=True, index=True)
    
    # Auditoría
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp())
    fecha_actualizacion = Column(DateTime, onupdate=func.current_timestamp())
    creado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))
    actualizado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))
    
    # Relationships
    personas = relationship("Persona", back_populates="departamento", foreign_keys="[Persona.id_departamento]")
    agentes = relationship("AgenteVirtual", back_populates="departamento")
    contenidos = relationship("UnidadContenido", back_populates="departamento")

    def __repr__(self):
        return f"<Departamento(id={self.id_departamento}, nombre='{self.nombre}', codigo='{self.codigo}')>"