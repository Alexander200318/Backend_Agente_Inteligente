from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum

class EstadoUsuarioEnum(str, enum.Enum):
    activo = "activo"
    inactivo = "inactivo"
    suspendido = "suspendido"
    bloqueado = "bloqueado"

class Usuario(Base):
    __tablename__ = "Usuario"

    # Primary Key
    id_usuario = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Key a Persona
    id_persona = Column(Integer, ForeignKey('Persona.id_persona', ondelete='CASCADE'), nullable=False, index=True)
    
    # Credenciales
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    
    # Estado de cuenta
    estado = Column(Enum(EstadoUsuarioEnum), default=EstadoUsuarioEnum.activo, index=True)
    requiere_cambio_password = Column(Boolean, default=False)
    intentos_fallidos = Column(Integer, default=0)
    fecha_ultimo_intento_fallido = Column(DateTime)
    fecha_bloqueo = Column(DateTime)
    
    # Sesiones
    ultimo_acceso = Column(DateTime)
    ultimo_ip = Column(String(45))
    token_recuperacion = Column(String(255))
    token_expiracion = Column(DateTime)
    
    # Auditoría
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp())
    fecha_actualizacion = Column(DateTime, onupdate=func.current_timestamp())
    creado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    persona = relationship("Persona", back_populates="usuario", foreign_keys=[id_persona])
    roles = relationship(
        "UsuarioRol", 
        back_populates="usuario", 
        cascade="all, delete-orphan",
        foreign_keys="[UsuarioRol.id_usuario]"
    )
    agentes_asignados = relationship(
        "UsuarioAgente", 
        back_populates="usuario", 
        cascade="all, delete-orphan",
        foreign_keys="[UsuarioAgente.id_usuario]"
    )
    
    # Self-referential para creado_por
    creador = relationship("Usuario", remote_side=[id_usuario], foreign_keys=[creado_por])

    def __repr__(self):
        return f"<Usuario(id={self.id_usuario}, username='{self.username}', email='{self.email}')>"