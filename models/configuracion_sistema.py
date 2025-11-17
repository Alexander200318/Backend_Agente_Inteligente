from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum

class TipoDatoConfigEnum(str, enum.Enum):
    string = "string"
    number = "number"
    boolean = "boolean"
    json = "json"

class ConfiguracionSistema(Base):
    __tablename__ = "Configuracion_Sistema"

    # Primary Key
    id_config = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Configuración
    clave = Column(String(100), unique=True, nullable=False, index=True)
    valor = Column(Text)
    tipo_dato = Column(Enum(TipoDatoConfigEnum), default=TipoDatoConfigEnum.string)
    categoria = Column(String(50), index=True)
    descripcion = Column(Text)
    modificable = Column(Boolean, default=True)
    
    # Auditoría
    modificado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))
    fecha_modificacion = Column(DateTime)
    
    # Relationships
    modificador = relationship("Usuario")

    def __repr__(self):
        return f"<ConfiguracionSistema(clave='{self.clave}', valor='{self.valor[:50] if self.valor else None}...')>"