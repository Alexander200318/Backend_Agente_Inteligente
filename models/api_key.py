from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum

class TipoIntegracionEnum(str, enum.Enum):
    wordpress = "wordpress"
    mobile_app = "mobile_app"
    webhook = "webhook"
    custom = "custom"

class APIKey(Base):
    __tablename__ = "API_Key"

    # Primary Key
    id_api_key = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # API Key
    key_value = Column(String(64), unique=True, nullable=False, index=True)
    key_name = Column(String(100), nullable=False)
    
    # Asociación
    id_agente = Column(
        Integer, 
        ForeignKey('Agente_Virtual.id_agente', ondelete='CASCADE'),
        index=True
    )
    origen_permitido = Column(String(255))
    tipo_integracion = Column(Enum(TipoIntegracionEnum), default=TipoIntegracionEnum.wordpress)
    
    # Seguridad y límites
    activa = Column(Boolean, default=True, index=True)
    rate_limit_por_minuto = Column(Integer, default=60)
    ip_whitelist = Column(Text, comment='JSON array de IPs permitidas')
    
    # Métricas de uso
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp())
    fecha_expiracion = Column(DateTime, index=True)
    ultimo_uso = Column(DateTime)
    total_llamadas = Column(Integer, default=0)
    total_errores = Column(Integer, default=0)
    
    # Auditoría
    creado_por = Column(
        Integer, 
        ForeignKey('Usuario.id_usuario', ondelete='RESTRICT'), 
        nullable=False
    )
    
    # Relationships
    agente = relationship("AgenteVirtual", back_populates="api_keys")
    creador = relationship("Usuario")

    def __repr__(self):
        return f"<APIKey(id={self.id_api_key}, name='{self.key_name}', activa={self.activa})>"