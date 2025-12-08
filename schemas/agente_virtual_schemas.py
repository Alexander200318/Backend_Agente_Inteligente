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
    pass

class AgenteVirtualUpdate(BaseModel):
    nombre_agente: Optional[str] = None
    tipo_agente: Optional[str] = None
    area_especialidad: Optional[str] = None
    id_departamento: Optional[int] = None
    descripcion: Optional[str] = None
    
    creado_por: Optional[int] = None
    actualizado_por: Optional[int] = None

    avatar_url: Optional[str] = None
    color_tema: Optional[str] = None
    icono: Optional[str] = None
    modelo_ia: Optional[str] = None
    prompt_sistema: Optional[str] = None
    prompt_especializado: Optional[str] = None
    temperatura: Optional[Decimal] = None
    max_tokens: Optional[int] = None
    mensaje_bienvenida: Optional[str] = None
    mensaje_despedida: Optional[str] = None
    mensaje_derivacion: Optional[str] = None
    mensaje_fuera_horario: Optional[str] = None
    horarios: Optional[str] = None
    zona_horaria: Optional[str] = None
    palabras_clave_trigger: Optional[str] = None
    prioridad_routing: Optional[int] = None
    puede_ejecutar_acciones: Optional[bool] = None
    acciones_disponibles: Optional[str] = None
    requiere_autenticacion: Optional[bool] = None
    activo: Optional[bool] = None

class AgenteVirtualResponse(AgenteVirtualBase):
    id_agente: int
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime]
    
    creador_nombre: Optional[str] = None
    actualizador_nombre: Optional[str] = None
    
    class Config:
        from_attributes = True

class AgenteConEstadisticas(AgenteVirtualResponse):
    total_usuarios_asignados: int = 0
    total_categorias: int = 0
    total_contenidos: int = 0
    total_conversaciones: int = 0
