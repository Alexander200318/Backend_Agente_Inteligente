from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal
import re

# 🔒 SECURITY: Patrones XSS
XSS_PATTERNS = [
    r'<script\b',
    r'on\w+\s*=',
    r'<iframe',
    r'javascript:',
    r'eval\s*\(',
    r'onerror\s*=',
    r'onload\s*='
]


class AgenteVirtualBase(BaseModel):
    """Schema base - SOLO para herencia"""
    nombre_agente: str
    tipo_agente: str = "especializado"
    area_especialidad: Optional[str] = None
    id_departamento: Optional[int] = None
    descripcion: Optional[str] = None
    creado_por: Optional[int] = None
    actualizado_por: Optional[int] = None
    avatar_url: Optional[str] = None
    color_tema: str = "#667eea"
    icono: Optional[str] = None
    modelo_ia: str = "llama3:8b"
    prompt_sistema: Optional[str] = None
    temperatura: Decimal = Decimal("0.7")
    max_tokens: int = 4000
    mensaje_bienvenida: Optional[str] = None
    mensaje_despedida: Optional[str] = None
    mensaje_derivacion: Optional[str] = None
    mensaje_fuera_horario: Optional[str] = None
    horarios: Optional[str] = None
    zona_horaria: str = "America/Guayaquil"
    palabras_clave_trigger: Optional[str] = None
    prioridad_routing: int = 0
    puede_ejecutar_acciones: bool = False
    acciones_disponibles: Optional[str] = None
    requiere_autenticacion: bool = False


class AgenteVirtualCreate(BaseModel):
    """
    Schema para CREAR agente - VALIDACIONES ESTRICTAS
    """
    nombre_agente: str = Field(..., min_length=3, max_length=100)
    tipo_agente: str = Field("especializado", pattern="^(router|especializado|hibrido)$")
    area_especialidad: Optional[str] = Field(None, max_length=100)
    id_departamento: Optional[int] = None
    descripcion: Optional[str] = Field(None, max_length=500)
    
    creado_por: Optional[int] = None
    actualizado_por: Optional[int] = None
    
    avatar_url: Optional[str] = Field(None, max_length=1000)
    color_tema: str = Field("#667eea", max_length=7)
    icono: Optional[str] = Field(None, max_length=50)
    
    modelo_ia: str = Field("llama3:8b", max_length=100)
    prompt_sistema: Optional[str] = Field(None, max_length=2000)
    temperatura: Decimal = Field(Decimal("0.7"), ge=Decimal("0.1"), le=Decimal("2.0"))
    max_tokens: int = Field(4000, ge=100, le=8000)
    
    mensaje_bienvenida: Optional[str] = Field(None, max_length=500)
    mensaje_despedida: Optional[str] = Field(None, max_length=500)
    mensaje_derivacion: Optional[str] = Field(None, max_length=500)
    mensaje_fuera_horario: Optional[str] = Field(None, max_length=500)
    
    horarios: Optional[str] = Field(None, max_length=2000)
    zona_horaria: str = Field("America/Guayaquil", max_length=50)
    
    palabras_clave_trigger: Optional[str] = Field(None, max_length=500)
    prioridad_routing: int = Field(0, ge=0, le=10)
    
    puede_ejecutar_acciones: bool = False
    acciones_disponibles: Optional[str] = Field(None, max_length=500)
    requiere_autenticacion: bool = False
    
    @field_validator('nombre_agente')
    @classmethod
    def validar_nombre_agente(cls, v: str) -> str:
        """🔒 SECURITY: Validar nombre al CREAR"""
        if not v or not v.strip():
            raise ValueError('⚠️ El nombre del agente es obligatorio')
        
        v_limpio = v.strip()
        
        if len(v_limpio) < 3:
            raise ValueError('⚠️ El nombre debe tener al menos 3 caracteres')
        
        if len(v_limpio) > 100:
            raise ValueError('⚠️ El nombre no puede exceder 100 caracteres')
        
        # 🔒 Detectar XSS
        for pattern in XSS_PATTERNS:
            if re.search(pattern, v_limpio, re.IGNORECASE):
                raise ValueError('⚠️ El nombre contiene caracteres no permitidos (posible ataque XSS)')
        
        if not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-_()]+$', v_limpio):
            raise ValueError('⚠️ El nombre contiene caracteres no permitidos')
        
        return v_limpio
    
    @field_validator('area_especialidad')
    @classmethod
    def validar_area_especialidad(cls, v: Optional[str]) -> Optional[str]:
        """🔒 SECURITY: Validar área"""
        if v is None or v.strip() == '':
            return None
        
        v_limpio = v.strip()
        
        if len(v_limpio) < 3:
            raise ValueError('⚠️ El área debe tener al menos 3 caracteres')
        
        if len(v_limpio) > 100:
            raise ValueError('⚠️ El área no puede exceder 100 caracteres')
        
        return v_limpio
    
    @field_validator('descripcion')
    @classmethod
    def validar_descripcion(cls, v: Optional[str]) -> Optional[str]:
        """🔒 SECURITY: Validar descripción"""
        if v is None or v.strip() == '':
            return None
        
        v_limpio = v.strip()
        
        if len(v_limpio) < 10:
            raise ValueError('⚠️ La descripción debe tener al menos 10 caracteres')
        
        if len(v_limpio) > 500:
            raise ValueError('⚠️ La descripción no puede exceder 500 caracteres')
        
        return v_limpio
    
    @field_validator('color_tema')
    @classmethod
    def validar_color_hex(cls, v: str) -> str:
        """🔒 SECURITY: Validar color"""
        if not v or v.strip() == '':
            return "#667eea"
        
        if not v.startswith('#'):
            v = f'#{v}'
        
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('⚠️ El color debe tener formato #RRGGBB')
        
        return v.lower()
    
    @field_validator('temperatura')
    @classmethod
    def validar_temperatura(cls, v: Optional[Decimal]) -> Decimal:
        """🔒 SECURITY: Validar temperatura"""
        if v is None:
            return Decimal("0.7")
        
        if isinstance(v, (int, float, str)):
            v = Decimal(str(v))
        
        if v < Decimal("0.1"):
            raise ValueError('⚠️ La temperatura debe ser al menos 0.1')
        elif v > Decimal("2.0"):
            raise ValueError('⚠️ La temperatura no puede exceder 2.0')
        
        return v
    
    @field_validator('max_tokens')
    @classmethod
    def validar_max_tokens(cls, v: Optional[int]) -> int:
        """🔒 SECURITY: Validar tokens"""
        if v is None:
            return 4000
        
        if v < 100:
            raise ValueError('⚠️ Los tokens deben ser al menos 100')
        elif v > 8000:
            raise ValueError('⚠️ Los tokens no pueden exceder 8000')
        
        return v
    
    @field_validator('id_departamento')
    @classmethod
    def validar_id_departamento(cls, v: Optional[int]) -> Optional[int]:
        """🔒 SECURITY: Validar departamento"""
        if v is None or v == 0:
            return None
        
        if v < 1:
            raise ValueError('⚠️ ID de departamento inválido')
        
        return v


class AgenteVirtualUpdate(BaseModel):
    """Schema para ACTUALIZAR - VALIDACIONES ESTRICTAS"""
    nombre_agente: Optional[str] = Field(None, min_length=3, max_length=100)
    tipo_agente: Optional[str] = Field(None, pattern="^(router|especializado|hibrido)$")
    area_especialidad: Optional[str] = Field(None, max_length=100)
    id_departamento: Optional[int] = None
    descripcion: Optional[str] = Field(None, max_length=500)
    
    actualizado_por: Optional[int] = None
    
    avatar_url: Optional[str] = Field(None, max_length=1000)
    color_tema: Optional[str] = Field(None, max_length=7)
    icono: Optional[str] = Field(None, max_length=50)
    
    modelo_ia: Optional[str] = Field(None, max_length=100)
    prompt_sistema: Optional[str] = Field(None, max_length=2000)
    temperatura: Optional[Decimal] = Field(None, ge=Decimal("0.1"), le=Decimal("2.0"))
    max_tokens: Optional[int] = Field(None, ge=100, le=8000)
    
    mensaje_bienvenida: Optional[str] = Field(None, max_length=500)
    mensaje_despedida: Optional[str] = Field(None, max_length=500)
    mensaje_derivacion: Optional[str] = Field(None, max_length=500)
    mensaje_fuera_horario: Optional[str] = Field(None, max_length=500)
    
    horarios: Optional[str] = Field(None, max_length=2000)
    zona_horaria: Optional[str] = Field(None, max_length=50)
    
    palabras_clave_trigger: Optional[str] = Field(None, max_length=500)
    prioridad_routing: Optional[int] = Field(None, ge=0, le=10)
    
    puede_ejecutar_acciones: Optional[bool] = None
    acciones_disponibles: Optional[str] = Field(None, max_length=500)
    requiere_autenticacion: Optional[bool] = None
    
    activo: Optional[bool] = None
    
    # Aplicar los mismos validadores que Create
    _validar_nombre = field_validator('nombre_agente')(AgenteVirtualCreate.validar_nombre_agente.__func__)
    _validar_area = field_validator('area_especialidad')(AgenteVirtualCreate.validar_area_especialidad.__func__)
    _validar_descripcion = field_validator('descripcion')(AgenteVirtualCreate.validar_descripcion.__func__)
    _validar_color = field_validator('color_tema')(AgenteVirtualCreate.validar_color_hex.__func__)
    _validar_temperatura = field_validator('temperatura')(AgenteVirtualCreate.validar_temperatura.__func__)
    _validar_tokens = field_validator('max_tokens')(AgenteVirtualCreate.validar_max_tokens.__func__)
    _validar_departamento = field_validator('id_departamento')(AgenteVirtualCreate.validar_id_departamento.__func__)


class AgenteVirtualResponse(BaseModel):
    """
    Schema de RESPUESTA - VALIDACIONES MUY PERMISIVAS
    
    ⚠️ IMPORTANTE: Este schema se usa para LEER datos de la BD.
    Debe ser MUY PERMISIVO porque puede haber datos legacy.
    """
    id_agente: int
    nombre_agente: str
    tipo_agente: str = "especializado"
    area_especialidad: Optional[str] = None
    id_departamento: Optional[int] = None
    descripcion: Optional[str] = None
    
    creado_por: Optional[int] = None
    actualizado_por: Optional[int] = None
    
    avatar_url: Optional[str] = None
    color_tema: str = "#667eea"
    icono: Optional[str] = None
    
    modelo_ia: str = "llama3:8b"
    prompt_sistema: Optional[str] = None
    temperatura: Decimal = Decimal("0.7")
    max_tokens: int = 4000
    
    mensaje_bienvenida: Optional[str] = None
    mensaje_despedida: Optional[str] = None
    mensaje_derivacion: Optional[str] = None
    mensaje_fuera_horario: Optional[str] = None
    
    horarios: Optional[str] = None
    zona_horaria: str = "America/Guayaquil"
    
    palabras_clave_trigger: Optional[str] = None
    prioridad_routing: int = 0
    
    puede_ejecutar_acciones: bool = False
    acciones_disponibles: Optional[str] = None
    
    requiere_autenticacion: bool = False
    activo: bool = True
    
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    
    eliminado: bool = False
    fecha_eliminacion: Optional[datetime] = None
    eliminado_por: Optional[int] = None
    
    creador_nombre: Optional[str] = None
    actualizador_nombre: Optional[str] = None
    eliminador_nombre: Optional[str] = None
    
    # ============ VALIDADORES PERMISIVOS ============
    
    @field_validator('nombre_agente', mode='before')
    @classmethod
    def clean_nombre_agente(cls, v) -> str:
        """Limpiar nombre al LEER - MUY PERMISIVO"""
        if v is None or v == '':
            return 'Agente sin nombre'
        return str(v).strip()[:100]
    
    @field_validator('tipo_agente', mode='before')
    @classmethod
    def clean_tipo_agente(cls, v) -> str:
        """Limpiar tipo al LEER - MUY PERMISIVO"""
        if v is None or v == '':
            return 'especializado'
        v_clean = str(v).strip().lower()
        if v_clean in ['router', 'especializado', 'hibrido']:
            return v_clean
        return 'especializado'
    
    @field_validator('area_especialidad', mode='before')
    @classmethod
    def clean_area_especialidad(cls, v) -> Optional[str]:
        """Limpiar área al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return None
        return str(v).strip()[:100]
    
    @field_validator('descripcion', mode='before')
    @classmethod
    def clean_descripcion(cls, v) -> Optional[str]:
        """Limpiar descripción al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return None
        return str(v).strip()[:500]
    
    @field_validator('color_tema', mode='before')
    @classmethod
    def clean_color_tema(cls, v) -> str:
        """Limpiar color al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return "#667eea"
        
        v_clean = str(v).strip()
        if not v_clean.startswith('#'):
            v_clean = f'#{v_clean}'
        
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v_clean):
            return "#667eea"
        
        return v_clean.lower()
    
    @field_validator('icono', mode='before')
    @classmethod
    def clean_icono(cls, v) -> Optional[str]:
        """Limpiar icono al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return '🤖'
        return str(v).strip()[:50]
    
    @field_validator('avatar_url', mode='before')
    @classmethod
    def clean_avatar_url(cls, v) -> Optional[str]:
        """Limpiar avatar al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return None
        return str(v).strip()[:1000]
    
    @field_validator('modelo_ia', mode='before')
    @classmethod
    def clean_modelo_ia(cls, v) -> str:
        """Limpiar modelo al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return "llama3:8b"
        return str(v).strip()[:100]
    
    @field_validator('prompt_sistema', mode='before')
    @classmethod
    def clean_prompt_sistema(cls, v) -> Optional[str]:
        """Limpiar prompt al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return None
        return str(v).strip()[:2000]
    
    @field_validator('temperatura', mode='before')
    @classmethod
    def clean_temperatura(cls, v) -> Decimal:
        """Limpiar temperatura al LEER - MUY PERMISIVO"""
        try:
            if v is None:
                return Decimal("0.7")
            temp = Decimal(str(v))
            if temp < Decimal("0.1"):
                return Decimal("0.1")
            if temp > Decimal("2.0"):
                return Decimal("2.0")
            return temp
        except:
            return Decimal("0.7")
    
    @field_validator('max_tokens', mode='before')
    @classmethod
    def clean_max_tokens(cls, v) -> int:
        """Limpiar tokens al LEER - MUY PERMISIVO"""
        try:
            if v is None:
                return 4000
            tokens = int(v)
            if tokens < 100:
                return 100
            if tokens > 8000:
                return 8000
            return tokens
        except:
            return 4000
    
    @field_validator('mensaje_bienvenida', 'mensaje_despedida', 'mensaje_derivacion', 'mensaje_fuera_horario', mode='before')
    @classmethod
    def clean_mensajes(cls, v) -> Optional[str]:
        """Limpiar mensajes al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return None
        return str(v).strip()[:500]
    
    @field_validator('horarios', mode='before')
    @classmethod
    def clean_horarios(cls, v) -> Optional[str]:
        """Limpiar horarios al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return None
        # No validar formato, solo aceptar
        return str(v).strip()[:2000]
    
    @field_validator('zona_horaria', mode='before')
    @classmethod
    def clean_zona_horaria(cls, v) -> str:
        """Limpiar zona horaria al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return "America/Guayaquil"
        return str(v).strip()[:50]
    
    @field_validator('palabras_clave_trigger', mode='before')
    @classmethod
    def clean_palabras_clave(cls, v) -> Optional[str]:
        """Limpiar palabras clave al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return None
        return str(v).strip()[:500]
    
    @field_validator('acciones_disponibles', mode='before')
    @classmethod
    def clean_acciones(cls, v) -> Optional[str]:
        """Limpiar acciones al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return None
        return str(v).strip()[:500]
    
    @field_validator('prioridad_routing', mode='before')
    @classmethod
    def clean_prioridad(cls, v) -> int:
        """Limpiar prioridad al LEER - MUY PERMISIVO"""
        try:
            prio = int(v)
            if prio < 0:
                return 0
            if prio > 10:
                return 10
            return prio
        except:
            return 0
    
    @field_validator('id_departamento', 'creado_por', 'actualizado_por', 'eliminado_por', mode='before')
    @classmethod
    def clean_ids_opcionales(cls, v) -> Optional[int]:
        """Limpiar IDs opcionales al LEER - MUY PERMISIVO"""
        if v is None or v == 0:
            return None
        try:
            id_val = int(v)
            if id_val <= 0:
                return None
            return id_val
        except:
            return None
    
    @field_validator('activo', 'eliminado', 'puede_ejecutar_acciones', 'requiere_autenticacion', mode='before')
    @classmethod
    def clean_booleans(cls, v) -> bool:
        """Limpiar booleanos al LEER - MUY PERMISIVO"""
        if v is None:
            return False
        return bool(v)
    
    class Config:
        from_attributes = True


class AgenteVirtualResponseSimple(BaseModel):
    """Schema simplificado para listas - MUY PERMISIVO"""
    id_agente: int
    nombre_agente: str
    tipo_agente: str = "especializado"
    area_especialidad: Optional[str] = None
    avatar_url: Optional[str] = None
    color_tema: str = "#667eea"
    activo: bool = True
    eliminado: bool = False
    fecha_creacion: datetime
    
    @field_validator('nombre_agente', mode='before')
    @classmethod
    def clean_nombre(cls, v) -> str:
        if v is None or v == '':
            return 'Agente sin nombre'
        return str(v).strip()[:100]
    
    @field_validator('tipo_agente', mode='before')
    @classmethod
    def clean_tipo(cls, v) -> str:
        if v is None or v == '':
            return 'especializado'
        v_clean = str(v).strip().lower()
        return v_clean if v_clean in ['router', 'especializado', 'hibrido'] else 'especializado'
    
    @field_validator('area_especialidad', mode='before')
    @classmethod
    def clean_area(cls, v) -> Optional[str]:
        if v is None or str(v).strip() == '':
            return None
        return str(v).strip()[:100]
    
    @field_validator('avatar_url', mode='before')
    @classmethod
    def clean_avatar(cls, v) -> Optional[str]:
        if v is None or str(v).strip() == '':
            return None
        return str(v).strip()[:1000]
    
    @field_validator('color_tema', mode='before')
    @classmethod
    def clean_color(cls, v) -> str:
        if v is None or str(v).strip() == '':
            return "#667eea"
        v_clean = str(v).strip()
        if not v_clean.startswith('#'):
            v_clean = f'#{v_clean}'
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v_clean):
            return "#667eea"
        return v_clean.lower()
    
    @field_validator('activo', 'eliminado', mode='before')
    @classmethod
    def clean_bool(cls, v) -> bool:
        return bool(v) if v is not None else False
    
    class Config:
        from_attributes = True


class AgenteConEstadisticas(AgenteVirtualResponse):
    """Schema con estadísticas"""
    total_usuarios_asignados: int = 0
    total_categorias: int = 0
    total_contenidos: int = 0
    total_conversaciones: int = 0


class AgenteEliminadoInfo(BaseModel):
    """Schema para agentes eliminados"""
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
    """Schema de respuesta al restaurar"""
    message: str
    id_agente: int
    agente: AgenteVirtualResponse


class EliminarAgenteResponse(BaseModel):
    """Schema de respuesta al eliminar"""
    message: str
    id_agente: int
    fecha_eliminacion: datetime
    eliminado_por: Optional[int] = None


class ValidarDepartamentoUnico(BaseModel):
    """Validar que departamento no tenga agente"""
    id_departamento: int
    id_agente_actual: Optional[int] = None
    
    @field_validator('id_departamento')
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v < 1:
            raise ValueError('ID de departamento inválido')
        return v


class ValidarEliminacionAgente(BaseModel):
    """Validar que agente pueda ser eliminado"""
    id_agente: int
    forzar: bool = False
    
    @field_validator('id_agente')
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v < 1:
            raise ValueError('ID de agente inválido')
        return v