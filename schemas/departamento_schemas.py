# schemas/departamento_schemas.py
from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional
from datetime import datetime
import re
from html import escape

class DepartamentoBase(BaseModel):
    nombre: str = Field(..., min_length=5, max_length=100, description="Nombre del departamento")
    descripcion: Optional[str] = Field(None, max_length=500, description="Descripción del departamento")
    codigo: str = Field(..., min_length=3, max_length=50, description="Código único del departamento")
    email: Optional[EmailStr] = Field(None, max_length=100, description="Email de contacto")
    telefono: Optional[str] = Field(None, max_length=20, description="Número de teléfono")
    ubicacion: Optional[str] = Field(None, max_length=200, description="Ubicación física")
    facultad: Optional[str] = Field(None, max_length=100, description="Facultad a la que pertenece")
    
    # 🔒 SECURITY: Sanitización XSS para TODOS los campos de texto
    @field_validator('nombre', 'descripcion', 'codigo', 'telefono', 'ubicacion', 'facultad')
    @classmethod
    def sanitize_input(cls, v: Optional[str]) -> Optional[str]:
        """
        ✅ XSS Protection: Elimina HTML/JS potencialmente peligroso
        Coincide con SecurityUtils.sanitizeInput() del frontend
        """
        if v is None:
            return None
        
        if not isinstance(v, str):
            return str(v)
        
        # Eliminar scripts, iframes, eventos onclick, etc.
        v = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', v, flags=re.IGNORECASE)
        v = re.sub(r'<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>', '', v, flags=re.IGNORECASE)
        v = re.sub(r'<img[^>]*onerror[^>]*>', '', v, flags=re.IGNORECASE)
        v = re.sub(r'javascript:', '', v, flags=re.IGNORECASE)
        v = re.sub(r'on\w+\s*=', '', v, flags=re.IGNORECASE)
        v = re.sub(r'<[^>]*>', '', v)  # Eliminar todos los tags HTML
        
        # Escape HTML entities
        v = escape(v)
        
        return v.strip()

    # 🔒 SECURITY: Detectar SQL Injection
    @field_validator('nombre', 'descripcion', 'codigo', 'telefono', 'ubicacion', 'facultad')
    @classmethod
    def prevent_sql_injection(cls, v: Optional[str]) -> Optional[str]:
        """
        ✅ SQL Injection Protection: Solo detecta patrones REALES y peligrosos
        Coincide con SecurityUtils.detectSqlInjection() del frontend
        """
        if v is None:
            return None
        
        # Patrones específicos de SQL injection (NO guiones normales)
        suspicious_patterns = [
            r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|UNION|WHERE|FROM|BY)\b',
            r'\/\*[\s\S]*?\*\/',  # Comentarios SQL /* */
            r';\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)',  # ; seguido de SQL
            r"(['\"])\s*(OR|AND)\s*(['\"]?1['\"]?|true)\s*=",  # ' OR '1'='1'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("⚠️ Caracteres sospechosos detectados en este campo")
        
        return v

    # 🔒 SECURITY: Validación específica de NOMBRE
    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        """
        Validación de nombre:
        - Mínimo 5 caracteres (coincide con frontend)
        - Máximo 100 caracteres
        - No puede estar vacío
        """
        if not v or not v.strip():
            raise ValueError("El nombre es obligatorio")
        
        if len(v.strip()) < 5:
            raise ValueError("El nombre debe tener al menos 5 caracteres")
        
        if len(v) > 100:
            raise ValueError("El nombre no puede exceder 100 caracteres")
        
        return v.strip()

    # 🔒 SECURITY: Validación específica de CÓDIGO
    @field_validator('codigo')
    @classmethod
    def validate_codigo(cls, v: str) -> str:
        """
        Validación de código:
        - Mínimo 3 caracteres (coincide con frontend)
        - Máximo 50 caracteres (coincide con frontend)
        - Solo letras, números, guiones (-) y guiones bajos (_)
        - Se convierte a mayúsculas
        """
        if not v or not v.strip():
            raise ValueError("El código es obligatorio")
        
        v_stripped = v.strip()
        
        if len(v_stripped) < 3:
            raise ValueError("El código debe tener al menos 3 caracteres")
        
        if len(v_stripped) > 50:
            raise ValueError("El código no puede exceder 50 caracteres")
        
        # Validar formato: solo alfanumérico, guiones y guiones bajos
        codigo_regex = r'^[A-Za-z0-9_-]+$'
        if not re.match(codigo_regex, v_stripped):
            raise ValueError("El código solo puede contener letras, números, guiones y guiones bajos")
        
        # Convertir a mayúsculas (como en el frontend)
        return v_stripped.upper()

    # 🔒 SECURITY: Validación específica de TELÉFONO
    @field_validator('telefono')
    @classmethod
    def validate_telefono(cls, v: Optional[str]) -> Optional[str]:
        """
        Validación de teléfono:
        - Opcional
        - Entre 7 y 15 dígitos (coincide con frontend: /^[0-9+\-\s()]{7,15}$/)
        - Puede contener: números, +, -, espacios, paréntesis
        """
        if not v:
            return None
        
        v_stripped = v.strip()
        
        # Validar formato permitido
        telefono_regex = r'^[0-9+\-\s()]{7,15}$'
        if not re.match(telefono_regex, v_stripped):
            raise ValueError("El teléfono no tiene un formato válido")
        
        # Contar solo dígitos para validar longitud
        solo_digitos = re.sub(r'[^0-9]', '', v_stripped)
        if len(solo_digitos) < 7 or len(solo_digitos) > 15:
            raise ValueError("El teléfono debe tener entre 7 y 15 dígitos")
        
        return v_stripped

    # 🔒 SECURITY: Validación de FACULTAD
    @field_validator('facultad')
    @classmethod
    def validate_facultad(cls, v: Optional[str]) -> Optional[str]:
        """Validación de facultad: máximo 100 caracteres"""
        if not v:
            return None
        
        if len(v) > 100:
            raise ValueError("La facultad no puede exceder 100 caracteres")
        
        return v.strip()

    # 🔒 SECURITY: Validación de UBICACIÓN
    @field_validator('ubicacion')
    @classmethod
    def validate_ubicacion(cls, v: Optional[str]) -> Optional[str]:
        """Validación de ubicación: máximo 200 caracteres"""
        if not v:
            return None
        
        if len(v) > 200:
            raise ValueError("La ubicación no puede exceder 200 caracteres")
        
        return v.strip()

    # 🔒 SECURITY: Validación de DESCRIPCIÓN
    @field_validator('descripcion')
    @classmethod
    def validate_descripcion(cls, v: Optional[str]) -> Optional[str]:
        """Validación de descripción: máximo 500 caracteres"""
        if not v:
            return None
        
        if len(v) > 500:
            raise ValueError("La descripción no puede exceder 500 caracteres")
        
        return v.strip()

    # 🔒 SECURITY: Validación general de longitud (protección adicional)
    @field_validator('nombre', 'descripcion', 'codigo', 'telefono', 'ubicacion', 'facultad')
    @classmethod
    def validate_max_length_security(cls, v: Optional[str]) -> Optional[str]:
        """
        Protección adicional contra buffer overflow:
        Ningún campo puede exceder 1000 caracteres (coincide con frontend)
        """
        if v and len(v) > 1000:
            raise ValueError("El contenido excede el límite permitido (máx 1000 caracteres)")
        
        return v


class DepartamentoCreate(DepartamentoBase):
    """Schema para crear un departamento"""
    pass


class DepartamentoUpdate(BaseModel):
    """Schema para actualizar un departamento (todos los campos opcionales)"""
    nombre: Optional[str] = Field(None, min_length=5, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    codigo: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = Field(None, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)
    ubicacion: Optional[str] = Field(None, max_length=200)
    facultad: Optional[str] = Field(None, max_length=100)
    jefe_departamento: Optional[int] = Field(None, gt=0)
    activo: Optional[bool] = None

    # 🔒 SECURITY: Aplicar las mismas validaciones que en DepartamentoBase
    @field_validator('nombre', 'descripcion', 'codigo', 'telefono', 'ubicacion', 'facultad')
    @classmethod
    def sanitize_input(cls, v: Optional[str]) -> Optional[str]:
        """✅ XSS Protection"""
        if v is None:
            return None
        
        v = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', v, flags=re.IGNORECASE)
        v = re.sub(r'<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>', '', v, flags=re.IGNORECASE)
        v = re.sub(r'<img[^>]*onerror[^>]*>', '', v, flags=re.IGNORECASE)
        v = re.sub(r'javascript:', '', v, flags=re.IGNORECASE)
        v = re.sub(r'on\w+\s*=', '', v, flags=re.IGNORECASE)
        v = re.sub(r'<[^>]*>', '', v)
        v = escape(v)
        
        return v.strip()

    @field_validator('nombre', 'descripcion', 'codigo', 'telefono', 'ubicacion', 'facultad')
    @classmethod
    def prevent_sql_injection(cls, v: Optional[str]) -> Optional[str]:
        """✅ SQL Injection Protection"""
        if v is None:
            return None
        
        suspicious_patterns = [
            r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|UNION|WHERE|FROM|BY)\b',
            r'\/\*[\s\S]*?\*\/',
            r';\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)',
            r"(['\"])\s*(OR|AND)\s*(['\"]?1['\"]?|true)\s*=",
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("⚠️ Caracteres sospechosos detectados")
        
        return v

    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if len(v.strip()) < 5:
            raise ValueError("El nombre debe tener al menos 5 caracteres")
        if len(v) > 100:
            raise ValueError("El nombre no puede exceder 100 caracteres")
        return v.strip()

    @field_validator('codigo')
    @classmethod
    def validate_codigo(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_stripped = v.strip()
        if len(v_stripped) < 3:
            raise ValueError("El código debe tener al menos 3 caracteres")
        if len(v_stripped) > 50:
            raise ValueError("El código no puede exceder 50 caracteres")
        if not re.match(r'^[A-Za-z0-9_-]+$', v_stripped):
            raise ValueError("El código solo puede contener letras, números, guiones y guiones bajos")
        return v_stripped.upper()

    @field_validator('telefono')
    @classmethod
    def validate_telefono(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v_stripped = v.strip()
        if not re.match(r'^[0-9+\-\s()]{7,15}$', v_stripped):
            raise ValueError("El teléfono no tiene un formato válido")
        solo_digitos = re.sub(r'[^0-9]', '', v_stripped)
        if len(solo_digitos) < 7 or len(solo_digitos) > 15:
            raise ValueError("El teléfono debe tener entre 7 y 15 dígitos")
        return v_stripped

    @field_validator('jefe_departamento')
    @classmethod
    def validate_jefe_id(cls, v: Optional[int]) -> Optional[int]:
        """Validar ID del jefe"""
        if v is not None and (v <= 0 or v > 999999):
            raise ValueError("ID de jefe inválido")
        return v


class DepartamentoResponse(DepartamentoBase):
    """Schema para respuesta de departamento"""
    id_departamento: int
    jefe_departamento: Optional[int] = None
    activo: bool = True
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DepartamentoConEstadisticas(DepartamentoResponse):
    """Schema con estadísticas del departamento"""
    total_personas: int = 0
    total_agentes: int = 0
    total_contenidos: int = 0


class DepartamentoListResponse(BaseModel):
    """Schema simplificado para listados"""
    id_departamento: int
    nombre: str
    codigo: str
    facultad: Optional[str] = None
    activo: bool = True
    total_agentes: int = 0
    
    class Config:
        from_attributes = True


class DeleteDepartamentoResponse(BaseModel):
    """Response para operación de eliminación"""
    ok: bool
    id_departamento: int
    mensaje: str
    agentes_afectados: int = 0
    usuarios_afectados: int = 0