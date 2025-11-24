from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum

class GeneroEnum(str, enum.Enum):
    masculino = "masculino"
    femenino = "femenino"
    otro = "otro"
    prefiero_no_decir = "prefiero_no_decir"

class TipoPersonaEnum(str, enum.Enum):
    docente = "docente"
    administrativo = "administrativo"
    estudiante = "estudiante"
    externo = "externo"

class EstadoPersonaEnum(str, enum.Enum):
    activo = "activo"
    inactivo = "inactivo"
    retirado = "retirado"

class Persona(Base):
    __tablename__ = "Persona"

    # Primary Key
    id_persona = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Datos personales básicos
    cedula = Column(String(20), unique=True, nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date)
    genero = Column(Enum(GeneroEnum))
    
    # Contacto
    telefono = Column(String(20))
    celular = Column(String(20))
    email_personal = Column(String(150))
    direccion = Column(Text)
    ciudad = Column(String(100))
    provincia = Column(String(100))
    
    # Información institucional
    tipo_persona = Column(Enum(TipoPersonaEnum), default=TipoPersonaEnum.administrativo)
    id_departamento = Column(Integer, ForeignKey('Departamento.id_departamento', ondelete='SET NULL'), nullable=True)
    cargo = Column(String(100))
    fecha_ingreso_institucion = Column(Date)
    
    # Contacto de emergencia
    contacto_emergencia_nombre = Column(String(150))
    contacto_emergencia_telefono = Column(String(20))
    contacto_emergencia_relacion = Column(String(50))
    
    # Metadata
    foto_perfil = Column(String(255))
    estado = Column(Enum(EstadoPersonaEnum), default=EstadoPersonaEnum.activo, index=True)
    
    # Auditoría
    fecha_registro = Column(DateTime, server_default=func.current_timestamp())
    fecha_actualizacion = Column(DateTime, onupdate=func.current_timestamp())
    
    # Relationships
    departamento = relationship("Departamento", back_populates="personas", foreign_keys=[id_departamento])
    usuario = relationship("Usuario", back_populates="persona", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Persona(id={self.id_persona}, nombre='{self.nombre} {self.apellido}', cedula='{self.cedula}')>"