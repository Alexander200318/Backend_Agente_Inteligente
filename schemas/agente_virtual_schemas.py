from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from decimal import Decimal

class AgenteVirtualBase(BaseModel):
    nombre_agente: str = Field(..., min_length=3, max_length=100)
    tipo_agente: str = Field("especializado", pattern="^(router|especializado|hibrido)$")
    area_especialidad: Optional[str] = Field(None, max_length=100)
    id_departamento: Optional[int] = None
    descripcion: Optional[str] = None
    
    # Auditoría
    creado_por: Optional[int] = None
    actualizado_por: Optional[int] = None
    
    # Apariencia
    avatar_url: Optional[str] = None
    color_tema: str = Field("#3B82F6", max_length=7)
    icono: Optional[str] = None
    
    # Configuración IA
    modelo_ia: str = Field("llama3:8b", max_length=100)
    prompt_sistema: Optional[str] = None
    prompt_especializado: Optional[str] = None
    temperatura: Decimal = Field(Decimal("0.7"), ge=0, le=2)
    max_tokens: int = Field(2000, ge=100, le=8000)
    
    # Mensajes
    mensaje_bienvenida: Optional[str] = None
    mensaje_despedida: Optional[str] = None
    mensaje_derivacion: Optional[str] = None
    mensaje_fuera_horario: Optional[str] = None
    
    # Horarios y zona horaria
    horarios: Optional[str] = None  # JSON string
    zona_horaria: str = Field("America/Guayaquil", max_length=50)
    
    # Routing
    palabras_clave_trigger: Optional[str] = None
    prioridad_routing: int = Field(0, ge=0, le=10)
    
    # Capacidades
    puede_ejecutar_acciones: bool = False
    acciones_disponibles: Optional[str] = None
    
    # Estado
    requiere_autenticacion: bool = False
    
    @validator('color_tema')
    def validar_color_hex(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('El color debe empezar con #')
        if v and len(v) != 7:
            raise ValueError('El color debe tener formato #RRGGBB')
        return v

class AgenteVirtualCreate(AgenteVirtualBase):
    """
    Schema para crear un agente virtual.
    No incluye campos de soft delete (se manejan automáticamente).
    """
    pass

class AgenteVirtualUpdate(BaseModel):
    """
    Schema para actualizar un agente virtual.
    Todos los campos son opcionales.
    NO permite modificar campos de eliminación (se manejan con endpoints específicos).
    """
    nombre_agente: Optional[str] = None
    tipo_agente: Optional[str] = None
    area_especialidad: Optional[str] = None
    id_departamento: Optional[int] = None
    descripcion: Optional[str] = None
    
    # Auditoría
    actualizado_por: Optional[int] = None

    # Apariencia
    avatar_url: Optional[str] = None
    color_tema: Optional[str] = None
    icono: Optional[str] = None
    
    # Configuración IA
    modelo_ia: Optional[str] = None
    prompt_sistema: Optional[str] = None
    prompt_especializado: Optional[str] = None
    temperatura: Optional[Decimal] = None
    max_tokens: Optional[int] = None
    
    # Mensajes
    mensaje_bienvenida: Optional[str] = None
    mensaje_despedida: Optional[str] = None
    mensaje_derivacion: Optional[str] = None
    mensaje_fuera_horario: Optional[str] = None
    
    # Horarios
    horarios: Optional[str] = None
    zona_horaria: Optional[str] = None
    
    # Routing
    palabras_clave_trigger: Optional[str] = None
    prioridad_routing: Optional[int] = None
    
    # Capacidades
    puede_ejecutar_acciones: Optional[bool] = None
    acciones_disponibles: Optional[str] = None
    requiere_autenticacion: Optional[bool] = None
    
    # Estado operacional (activo/inactivo)
    activo: Optional[bool] = None
    
    # NOTA: Los campos de soft delete NO se permiten aquí
    # eliminado, fecha_eliminacion, eliminado_por se manejan con endpoints específicos

class AgenteVirtualResponse(AgenteVirtualBase):
    """
    Schema de respuesta con información completa del agente.
    Incluye campos de auditoría y soft delete.
    """
    id_agente: int
    activo: bool
    
    # Fechas de auditoría
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    
    # Soft delete
    eliminado: bool = False
    fecha_eliminacion: Optional[datetime] = None
    eliminado_por: Optional[int] = None
    
    # Información de usuarios (relaciones)
    creador_nombre: Optional[str] = None
    actualizador_nombre: Optional[str] = None
    eliminador_nombre: Optional[str] = None
    
    class Config:
        from_attributes = True

class AgenteVirtualResponseSimple(BaseModel):
    """
    Schema de respuesta simplificado para listas.
    Solo incluye información básica sin detalles de auditoría completos.
    """
    id_agente: int
    nombre_agente: str
    tipo_agente: str
    area_especialidad: Optional[str] = None
    avatar_url: Optional[str] = None
    color_tema: str
    activo: bool
    eliminado: bool
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

class AgenteConEstadisticas(AgenteVirtualResponse):
    """
    Schema extendido que incluye estadísticas del agente.
    """
    total_usuarios_asignados: int = 0
    total_categorias: int = 0
    total_contenidos: int = 0
    total_conversaciones: int = 0

class AgenteEliminadoInfo(BaseModel):
    """
    Schema específico para información de agentes eliminados.
    """
    id_agente: int
    nombre_agente: str
    tipo_agente: str
    eliminado: bool
    fecha_eliminacion: Optional[datetime] = None
    eliminado_por: Optional[int] = None
    eliminador_nombre: Optional[str] = None
    activo: bool
    
    class Config:
        from_attributes = True

class RestaurarAgenteResponse(BaseModel):
    """
    Schema de respuesta al restaurar un agente.
    """
    message: str
    id_agente: int
    agente: AgenteVirtualResponse

class EliminarAgenteResponse(BaseModel):
    """
    Schema de respuesta al eliminar un agente.
    """
    message: str
    id_agente: int
    fecha_eliminacion: datetime
    eliminado_por: Optional[int] = None