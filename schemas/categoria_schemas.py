from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime
import re

# 🔒 SECURITY: Iconos permitidos
ICONOS_PERMITIDOS = [
    'folder', 'document', 'file-tray', 'archive', 'briefcase',
    'cart', 'cash', 'card', 'calculator', 'calendar',
    'clipboard', 'bookmark', 'flag', 'star', 'heart', 'bulb'
]

# 🔒 SECURITY: Colores permitidos
COLORES_PERMITIDOS = [
    '#667eea', '#3b82f6', '#06b6d4', '#10b981', '#84cc16',
    '#fbbf24', '#f97316', '#ef4444', '#ec4899', '#d946ef',
    '#6366f1', '#8b5cf6', '#6b7280', '#059669'
]

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


class CategoriaBase(BaseModel):
    """Schema base - SOLO para herencia, NO para uso directo"""
    nombre: str
    descripcion: Optional[str] = None
    id_categoria_padre: Optional[int] = None
    icono: Optional[str] = None
    color: Optional[str] = None
    orden: int = 0


class CategoriaCreate(BaseModel):
    """
    Schema para CREAR categoría - VALIDACIONES ESTRICTAS
    """
    nombre: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    id_categoria_padre: Optional[int] = None
    icono: Optional[str] = None
    color: Optional[str] = None
    orden: int = Field(default=0, ge=0, le=9999)
    id_agente: int = Field(..., gt=0)
    activo: Optional[bool] = True
    eliminado: Optional[bool] = False
    creado_por: Optional[int] = None
    
    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        """🔒 SECURITY: Validar nombre al CREAR"""
        if not v or len(v.strip()) == 0:
            raise ValueError('⚠️ El nombre es obligatorio')
        
        v = v.strip()
        
        if len(v) < 3:
            raise ValueError('⚠️ El nombre debe tener al menos 3 caracteres')
        
        if len(v) > 100:
            raise ValueError('⚠️ El nombre no puede exceder 100 caracteres')
        
        # 🔒 Detectar XSS
        for pattern in XSS_PATTERNS:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('⚠️ El nombre contiene caracteres no permitidos (posible ataque XSS)')
        
        # 🔒 Validar caracteres permitidos
        if not re.match(r'^[a-zA-Z0-9\sáéíóúÁÉÍÓÚñÑüÜ\-_.,:;()]+$', v):
            raise ValueError('⚠️ El nombre contiene caracteres no permitidos')
        
        return v
    
    @field_validator('descripcion')
    @classmethod
    def validate_descripcion(cls, v: Optional[str]) -> Optional[str]:
        """🔒 SECURITY: Validar descripción al CREAR"""
        if v is None or not v.strip():
            return None
        
        v = v.strip()
        
        if len(v) > 500:
            raise ValueError('⚠️ La descripción no puede exceder 500 caracteres')
        
        # 🔒 Detectar XSS
        for pattern in XSS_PATTERNS:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('⚠️ La descripción contiene caracteres no permitidos (posible ataque XSS)')
        
        return v
    
    @field_validator('id_categoria_padre')
    @classmethod
    def validate_id_categoria_padre(cls, v: Optional[int]) -> Optional[int]:
        """🔒 SECURITY: Validar ID de categoría padre"""
        if v == 0 or v is None:
            return None
        
        if not isinstance(v, int):
            try:
                v = int(v)
            except:
                return None
        
        if v < 0:
            return None
        
        return v
    
    @field_validator('icono')
    @classmethod
    def validate_icono(cls, v: Optional[str]) -> str:
        """🔒 SECURITY: Validar icono al CREAR"""
        if v is None or not v.strip():
            return 'folder'
        
        v = v.strip().lower()
        
        if v not in ICONOS_PERMITIDOS:
            raise ValueError(f'⚠️ Icono no permitido. Debe ser uno de: {", ".join(ICONOS_PERMITIDOS)}')
        
        return v
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> str:
        """🔒 SECURITY: Validar color al CREAR"""
        if v is None or not v.strip():
            return '#667eea'
        
        v = v.strip().lower()
        
        if not v.startswith('#'):
            v = f'#{v}'
        
        if not re.match(r'^#[0-9a-f]{6}$', v):
            raise ValueError('⚠️ El color debe tener formato hexadecimal #RRGGBB')
        
        if v not in COLORES_PERMITIDOS:
            raise ValueError(f'⚠️ Color no permitido. Debe ser uno de los colores predefinidos')
        
        return v
    
    @field_validator('orden')
    @classmethod
    def validate_orden(cls, v: int) -> int:
        """🔒 SECURITY: Validar orden"""
        try:
            v = int(v)
        except:
            return 0
        
        if v < 0:
            return 0
        
        if v > 9999:
            return 9999
        
        return v
    
    @field_validator('id_agente')
    @classmethod
    def validate_id_agente(cls, v: int) -> int:
        """🔒 SECURITY: Validar ID de agente al CREAR"""
        if not isinstance(v, int):
            try:
                v = int(v)
            except:
                raise ValueError('⚠️ ID de agente debe ser un número entero')
        
        if v <= 0:
            raise ValueError('⚠️ ID de agente debe ser positivo')
        
        return v
    
    @field_validator('creado_por')
    @classmethod
    def validate_creado_por(cls, v: Optional[int]) -> Optional[int]:
        """🔒 SECURITY: Validar ID de usuario creador"""
        if v is None or v == 0:
            return None
        
        try:
            v = int(v)
            if v <= 0:
                return None
            return v
        except:
            return None


class CategoriaUpdate(BaseModel):
    """
    Schema para ACTUALIZAR - VALIDACIONES ESTRICTAS solo en lo que se envía
    """
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    id_categoria_padre: Optional[int] = None
    icono: Optional[str] = None
    color: Optional[str] = None
    orden: Optional[int] = Field(None, ge=0, le=9999)
    activo: Optional[bool] = None
    eliminado: Optional[bool] = None
    id_agente: Optional[int] = Field(None, gt=0)
    creado_por: Optional[int] = None
    
    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v: Optional[str]) -> Optional[str]:
        """🔒 SECURITY: Validar nombre al ACTUALIZAR"""
        if v is None:
            return v
        
        v = v.strip()
        
        if len(v) < 3:
            raise ValueError('⚠️ El nombre debe tener al menos 3 caracteres')
        
        if len(v) > 100:
            raise ValueError('⚠️ El nombre no puede exceder 100 caracteres')
        
        # 🔒 Detectar XSS
        for pattern in XSS_PATTERNS:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('⚠️ El nombre contiene caracteres no permitidos (posible ataque XSS)')
        
        if not re.match(r'^[a-zA-Z0-9\sáéíóúÁÉÍÓÚñÑüÜ\-_.,:;()]+$', v):
            raise ValueError('⚠️ El nombre contiene caracteres no permitidos')
        
        return v
    
    @field_validator('descripcion')
    @classmethod
    def validate_descripcion(cls, v: Optional[str]) -> Optional[str]:
        """🔒 SECURITY: Validar descripción al ACTUALIZAR"""
        if v is None or not v.strip():
            return None
        
        v = v.strip()
        
        if len(v) > 500:
            raise ValueError('⚠️ La descripción no puede exceder 500 caracteres')
        
        for pattern in XSS_PATTERNS:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('⚠️ La descripción contiene caracteres no permitidos')
        
        return v
    
    @field_validator('icono')
    @classmethod
    def validate_icono(cls, v: Optional[str]) -> Optional[str]:
        """🔒 SECURITY: Validar icono al ACTUALIZAR"""
        if v is None or not v.strip():
            return None
        
        v = v.strip().lower()
        
        if v not in ICONOS_PERMITIDOS:
            raise ValueError(f'⚠️ Icono no permitido')
        
        return v
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """🔒 SECURITY: Validar color al ACTUALIZAR"""
        if v is None or not v.strip():
            return None
        
        v = v.strip().lower()
        
        if not v.startswith('#'):
            v = f'#{v}'
        
        if not re.match(r'^#[0-9a-f]{6}$', v):
            raise ValueError('⚠️ El color debe tener formato hexadecimal')
        
        if v not in COLORES_PERMITIDOS:
            raise ValueError(f'⚠️ Color no permitido')
        
        return v
    
    @field_validator('id_categoria_padre')
    @classmethod
    def validate_id_categoria_padre(cls, v: Optional[int]) -> Optional[int]:
        """🔒 SECURITY: Validar ID de categoría padre"""
        if v == 0 or v is None:
            return None
        
        try:
            v = int(v)
            if v < 0:
                return None
            return v
        except:
            return None
    
    @field_validator('id_agente')
    @classmethod
    def validate_id_agente(cls, v: Optional[int]) -> Optional[int]:
        """🔒 SECURITY: Validar ID de agente"""
        if v is None:
            return v
        
        try:
            v = int(v)
            if v <= 0:
                raise ValueError('⚠️ ID de agente debe ser positivo')
            return v
        except ValueError as e:
            raise e
        except:
            raise ValueError('⚠️ ID de agente debe ser un número entero')
    
    @field_validator('creado_por')
    @classmethod
    def validate_creado_por(cls, v: Optional[int]) -> Optional[int]:
        """🔒 SECURITY: Validar ID de usuario creador"""
        if v is None or v == 0:
            return None
        
        try:
            v = int(v)
            if v <= 0:
                return None
            return v
        except:
            return None
    
    @model_validator(mode='after')
    def validate_at_least_one_field(self):
        """🔒 SECURITY: Al menos un campo debe estar presente"""
        if not any([
            self.nombre is not None,
            self.descripcion is not None,
            self.id_categoria_padre is not None,
            self.icono is not None,
            self.color is not None,
            self.orden is not None,
            self.activo is not None,
            self.eliminado is not None,
            self.id_agente is not None,
            self.creado_por is not None
        ]):
            raise ValueError('⚠️ Debe proporcionar al menos un campo para actualizar')
        
        return self


class CategoriaResponse(BaseModel):
    """
    Schema de RESPUESTA - VALIDACIONES PERMISIVAS
    
    ⚠️ IMPORTANTE: Este schema se usa para LEER datos de la BD.
    Debe ser MÁS PERMISIVO porque puede haber datos legacy o 
    datos creados antes de implementar las validaciones estrictas.
    """
    id_categoria: int
    nombre: str
    descripcion: Optional[str] = None
    id_categoria_padre: Optional[int] = None
    icono: str = 'folder'
    color: str = '#667eea'
    orden: int = 0
    id_agente: int
    activo: bool = True
    eliminado: bool = False
    creado_por: Optional[int] = None
    fecha_creacion: datetime
    
    @field_validator('nombre', mode='before')
    @classmethod
    def clean_nombre(cls, v) -> str:
        """Limpiar nombre al LEER - MUY PERMISIVO"""
        if v is None or v == '':
            return 'Sin nombre'
        return str(v).strip()[:100]
    
    @field_validator('descripcion', mode='before')
    @classmethod
    def clean_descripcion(cls, v) -> Optional[str]:
        """Limpiar descripción al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return None
        return str(v).strip()[:500]
    
    @field_validator('icono', mode='before')
    @classmethod
    def clean_icono(cls, v) -> str:
        """Limpiar icono al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return 'folder'
        
        v_clean = str(v).strip().lower()
        
        # Si el icono está en la lista, usarlo
        if v_clean in ICONOS_PERMITIDOS:
            return v_clean
        
        # Si no está, usar el default
        return 'folder'
    
    @field_validator('color', mode='before')
    @classmethod
    def clean_color(cls, v) -> str:
        """Limpiar color al LEER - MUY PERMISIVO"""
        if v is None or str(v).strip() == '':
            return '#667eea'
        
        v_clean = str(v).strip().lower()
        
        # Agregar # si no lo tiene
        if not v_clean.startswith('#'):
            v_clean = f'#{v_clean}'
        
        # Verificar formato hex básico
        if not re.match(r'^#[0-9a-f]{6}$', v_clean):
            return '#667eea'
        
        # Si el color está en la lista, usarlo
        if v_clean in COLORES_PERMITIDOS:
            return v_clean
        
        # Si no está, usar el default
        return '#667eea'
    
    @field_validator('orden', mode='before')
    @classmethod
    def clean_orden(cls, v) -> int:
        """Limpiar orden al LEER - MUY PERMISIVO"""
        try:
            orden = int(v)
            if orden < 0:
                return 0
            if orden > 9999:
                return 9999
            return orden
        except:
            return 0
    
    @field_validator('id_categoria_padre', mode='before')
    @classmethod
    def clean_id_categoria_padre(cls, v) -> Optional[int]:
        """Limpiar ID padre al LEER - MUY PERMISIVO"""
        if v is None or v == 0 or v == '0':
            return None
        try:
            id_padre = int(v)
            if id_padre <= 0:
                return None
            return id_padre
        except:
            return None
    
    @field_validator('activo', mode='before')
    @classmethod
    def clean_activo(cls, v) -> bool:
        """Limpiar activo al LEER - MUY PERMISIVO"""
        if v is None:
            return True
        return bool(v)
    
    @field_validator('eliminado', mode='before')
    @classmethod
    def clean_eliminado(cls, v) -> bool:
        """Limpiar eliminado al LEER - MUY PERMISIVO"""
        if v is None:
            return False
        return bool(v)
    
    @field_validator('creado_por', mode='before')
    @classmethod
    def clean_creado_por(cls, v) -> Optional[int]:
        """Limpiar creado_por al LEER - MUY PERMISIVO"""
        if v is None or v == 0:
            return None
        try:
            return int(v)
        except:
            return None
    
    class Config:
        from_attributes = True


class CategoriaResponseSimple(BaseModel):
    """Schema simplificado para listas - MUY PERMISIVO"""
    id_categoria: int
    nombre: str
    icono: str = 'folder'
    color: str = '#667eea'
    id_agente: int
    activo: bool = True
    eliminado: bool = False
    
    @field_validator('nombre', mode='before')
    @classmethod
    def clean_nombre(cls, v) -> str:
        if v is None or v == '':
            return 'Sin nombre'
        return str(v).strip()[:100]
    
    @field_validator('icono', mode='before')
    @classmethod
    def clean_icono(cls, v) -> str:
        if v is None or str(v).strip() == '':
            return 'folder'
        v_clean = str(v).strip().lower()
        return v_clean if v_clean in ICONOS_PERMITIDOS else 'folder'
    
    @field_validator('color', mode='before')
    @classmethod
    def clean_color(cls, v) -> str:
        if v is None or str(v).strip() == '':
            return '#667eea'
        v_clean = str(v).strip().lower()
        if not v_clean.startswith('#'):
            v_clean = f'#{v_clean}'
        if not re.match(r'^#[0-9a-f]{6}$', v_clean):
            return '#667eea'
        return v_clean if v_clean in COLORES_PERMITIDOS else '#667eea'
    
    class Config:
        from_attributes = True


class CategoriaConSubcategorias(CategoriaResponse):
    """Schema con subcategorías"""
    total_subcategorias: int = 0
    total_contenidos: int = 0


class CategoriaEliminadaInfo(BaseModel):
    """Schema para categorías eliminadas"""
    id_categoria: int
    nombre: str
    eliminado: bool
    fecha_creacion: datetime
    id_agente: int
    activo: bool
    
    class Config:
        from_attributes = True


class RestaurarCategoriaResponse(BaseModel):
    """Schema de respuesta al restaurar"""
    message: str
    id_categoria: int
    categoria: CategoriaResponse


class EliminarCategoriaResponse(BaseModel):
    """Schema de respuesta al eliminar"""
    message: str
    id_categoria: int


class ValidarEliminacionCategoria(BaseModel):
    """Validar que categoría pueda ser eliminada"""
    id_categoria: int
    forzar: bool = False
    
    @field_validator('id_categoria')
    @classmethod
    def validar_id(cls, v: int) -> int:
        if v < 1:
            raise ValueError('⚠️ ID de categoría inválido')
        return v