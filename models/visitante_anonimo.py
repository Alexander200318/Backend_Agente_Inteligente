from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum

class DispositivoEnum(str, enum.Enum):
    desktop = "desktop"
    mobile = "mobile"
    tablet = "tablet"

class VisitanteAnonimo(Base):
    __tablename__ = "Visitante_Anonimo"

    # Primary Key
    id_visitante = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Identificador único de sesión
    identificador_sesion = Column(String(255), unique=True, nullable=False, index=True)
    
    # Información técnica
    ip_origen = Column(String(45))
    user_agent = Column(Text)
    dispositivo = Column(Enum(DispositivoEnum))
    navegador = Column(String(50))
    sistema_operativo = Column(String(50))
    
    # Geolocalización
    pais = Column(String(50))
    ciudad = Column(String(100))
    
    # Métricas de uso
    primera_visita = Column(DateTime, server_default=func.current_timestamp(), index=True)
    ultima_visita = Column(DateTime, index=True)
    total_conversaciones = Column(Integer, default=0)
    total_mensajes = Column(Integer, default=0)
    
    # Relationships
    conversaciones = relationship("ConversacionSync", back_populates="visitante", cascade="all, delete-orphan")

    # ===============================
    # NUEVOS ATRIBUTOS (ANALÍTICA Y PERFIL)
    # ===============================

    # Canal de acceso
    canal_acceso = Column(String(50), index=True)

    # Datos opcionales del visitante
    nombre = Column(String(100))
    apellido = Column(String(100))
    edad = Column(String(20))
    ocupacion = Column(String(100))
    pertenece_instituto = Column(Boolean, default=False)

    # Calidad de la interacción
    satisfaccion_estimada = Column(Integer)
    email = Column(String(100))

    def __repr__(self):
        return f"<VisitanteAnonimo(id={self.id_visitante}, sesion='{self.identificador_sesion[:20]}...')>"