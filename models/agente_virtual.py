# agente_virtual.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum

class TipoAgenteEnum(str, enum.Enum):
    router = "router"
    especializado = "especializado"
    hibrido = "hibrido"

class AgenteVirtual(Base):
    __tablename__ = "Agente_Virtual"

    # Primary Key
    id_agente = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Información básica
    nombre_agente = Column(String(100), nullable=False)
    tipo_agente = Column(Enum(TipoAgenteEnum), default=TipoAgenteEnum.especializado)
    area_especialidad = Column(String(100), index=True)
    id_departamento = Column(
        Integer, 
        ForeignKey('Departamento.id_departamento', ondelete='SET NULL'),
        index=True,
        comment='Departamento responsable del agente'
    )
    descripcion = Column(Text)
    
    # Apariencia
    avatar_url = Column(String(255))
    color_tema = Column(String(7), default='#3B82F6')
    icono = Column(String(100))
    
    # Configuración de IA
    modelo_ia = Column(String(100), default='llama3:8b')
    prompt_sistema = Column(Text)
    prompt_especializado = Column(Text)
    temperatura = Column(DECIMAL(3, 2), default=0.7)
    max_tokens = Column(Integer, default=2000)
    
    # Mensajes predefinidos
    mensaje_bienvenida = Column(Text)
    mensaje_despedida = Column(Text)
    mensaje_derivacion = Column(Text)
    mensaje_fuera_horario = Column(Text)
    
    # Horarios (JSON format)
    horarios = Column(
        Text,
        comment='JSON: {"lunes": [{"inicio": "08:00", "fin": "17:00"}], "martes": [...]}'
    )
    zona_horaria = Column(String(50), default='America/Guayaquil')
    
    # Routing y triggers
    palabras_clave_trigger = Column(Text)
    prioridad_routing = Column(Integer, default=0)
    
    # Capacidades
    puede_ejecutar_acciones = Column(Boolean, default=False)
    acciones_disponibles = Column(Text)
    
    # Estado y permisos
    activo = Column(Boolean, default=True, index=True)
    requiere_autenticacion = Column(Boolean, default=False)
    
    # Auditoría
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp())
    fecha_actualizacion = Column(DateTime, onupdate=func.current_timestamp())
    creado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))
    actualizado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))
    
    # Relationships
    departamento = relationship("Departamento", back_populates="agentes")
    categorias = relationship("Categoria", back_populates="agente", cascade="all, delete-orphan")
    contenidos = relationship("UnidadContenido", back_populates="agente", cascade="all, delete-orphan")
    usuarios_asignados = relationship("UsuarioAgente", back_populates="agente", cascade="all, delete-orphan")
    metricas = relationship("MetricaDiariaAgente", back_populates="agente", cascade="all, delete-orphan")
    widgets = relationship("WidgetConfig", back_populates="agente", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="agente", cascade="all, delete-orphan")
    conversaciones_iniciadas = relationship(
        "ConversacionSync", 
        foreign_keys="[ConversacionSync.id_agente_inicial]",
        back_populates="agente_inicial"
    )
    conversaciones_actuales = relationship(
        "ConversacionSync",
        foreign_keys="[ConversacionSync.id_agente_actual]",
        back_populates="agente_actual"
    )

    def __repr__(self):
        return f"<AgenteVirtual(id={self.id_agente}, nombre='{self.nombre_agente}', tipo='{self.tipo_agente}')>"