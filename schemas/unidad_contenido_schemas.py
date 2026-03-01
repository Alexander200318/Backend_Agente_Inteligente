# schemas/unidad_contenido_schemas.py
from datetime import date, datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
import re
from html import escape

class UnidadContenidoBase(BaseModel):
    titulo: str = Field(..., min_length=5, max_length=200, description="Título del contenido")
    contenido: str = Field(..., min_length=1, max_length=50000, description="Contenido detallado")
    resumen: Optional[str] = Field(None, min_length=10, max_length=2000, description="Resumen breve")
    palabras_clave: Optional[str] = Field(None, min_length=3, max_length=1000, description="Palabras clave separadas por comas")
    etiquetas: Optional[str] = Field(None, min_length=3, max_length=1000, description="Etiquetas separadas por comas")
    prioridad: int = Field(5, ge=1, le=10, description="Prioridad del contenido (1-10)")
    fecha_vigencia_inicio: Optional[date] = Field(None, description="Fecha de inicio de vigencia")
    fecha_vigencia_fin: Optional[date] = Field(None, description="Fecha de fin de vigencia")

    # 🔒 SECURITY: Sanitización XSS
    @field_validator('titulo', 'contenido', 'resumen', 'palabras_clave', 'etiquetas')
    @classmethod
    def sanitize_input(cls, v: Optional[str]) -> Optional[str]:
        """
        ✅ XSS Protection: Elimina HTML/JS potencialmente peligroso
        """
        if v is None:
            return None
        
        if not isinstance(v, str):
            return str(v)
        
        # Eliminar scripts, iframes, javascript:
        v = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', v, flags=re.IGNORECASE)
        v = re.sub(r'<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>', '', v, flags=re.IGNORECASE)
        v = re.sub(r'javascript:', '', v, flags=re.IGNORECASE)
        v = re.sub(r'on\w+\s*=', '', v, flags=re.IGNORECASE)
        
        # Eliminar tags HTML (excepto en contenido que puede necesitarlos)
        # v = re.sub(r'<[^>]*>', '', v)
        
        # Escape HTML entities para seguridad adicional
        v = escape(v)
        
        return v.strip()

    # 🔒 SECURITY: Validación de SQL Injection
    @field_validator('titulo', 'contenido', 'resumen', 'palabras_clave', 'etiquetas')
    @classmethod
    def prevent_sql_injection(cls, v: Optional[str]) -> Optional[str]:
        """
        ✅ SQL Injection Protection: Detecta patrones sospechosos
        """
        if v is None:
            return None
        
        # Patrones sospechosos de SQL injection
        suspicious_patterns = [
            r"('\s*(OR|AND)\s*'?\d)",
            r"(--|\#|\/\*|\*\/)",
            r"(UNION\s+SELECT)",
            r"(DROP\s+TABLE)",
            r"(INSERT\s+INTO)",
            r"(DELETE\s+FROM)",
            r"(UPDATE\s+\w+\s+SET)",
            r"(EXEC\s*\()",
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Contenido sospechoso detectado. Por favor, verifica tu entrada.")
        
        return v

    # 🔒 SECURITY: Validación de longitud máxima
    @field_validator('titulo')
    @classmethod
    def validate_titulo_length(cls, v: str) -> str:
        """Validación específica de título"""
        if len(v.strip()) < 5:
            raise ValueError(f"El título debe tener al menos 5 caracteres (actual: {len(v.strip())})")
        if len(v) > 500:
            raise ValueError(f"El título es demasiado largo (máx 500 caracteres)")
        return v

    @field_validator('contenido')
    @classmethod
    def validate_contenido_length(cls, v: str) -> str:
        """Validación específica de contenido"""
        if len(v.strip()) < 1:
            raise ValueError(f"El contenido no puede estar vacío")
        if len(v) > 50000:
            raise ValueError(f"El contenido es demasiado largo (máx 50000 caracteres)")
        return v

    @field_validator('resumen')
    @classmethod
    def validate_resumen_length(cls, v: Optional[str]) -> Optional[str]:
        """Validación específica de resumen"""
        if v is None:
            return None
        if len(v.strip()) < 10:
            raise ValueError(f"El resumen debe tener al menos 10 caracteres (actual: {len(v.strip())})")
        if len(v) > 2000:
            raise ValueError(f"El resumen es demasiado largo (máx 2000 caracteres)")
        return v

    @field_validator('palabras_clave', 'etiquetas')
    @classmethod
    def validate_keywords_tags(cls, v: Optional[str]) -> Optional[str]:
        """Validación de palabras clave y etiquetas"""
        if v is None:
            return None
        if len(v.strip()) < 3:
            raise ValueError("Debe tener al menos 3 caracteres")
        if len(v) > 1000:
            raise ValueError("Demasiado largo (máx 1000 caracteres)")
        return v

    # 🔒 SECURITY: Validación de fechas
    @model_validator(mode='after')
    def validate_date_range(self):
        """
        ✅ Validación de rango de fechas:
        - Fecha fin debe ser mayor que fecha inicio
        - Rango máximo de 10 años
        """
        if self.fecha_vigencia_inicio and self.fecha_vigencia_fin:
            # Validar que fin > inicio
            if self.fecha_vigencia_fin < self.fecha_vigencia_inicio:
                raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")
            
            # Validar rango máximo de 10 años
            delta = (self.fecha_vigencia_fin - self.fecha_vigencia_inicio).days
            max_days = 10 * 365  # 10 años
            
            if delta > max_days:
                raise ValueError(f"El rango de fechas no puede superar 10 años (actual: {delta} días)")
            
            if delta < 0:
                raise ValueError("El rango de fechas debe ser positivo")
        
        # Si solo hay una fecha, advertir
        elif self.fecha_vigencia_inicio and not self.fecha_vigencia_fin:
            raise ValueError("Si defines fecha de inicio, debes definir fecha de fin")
        elif not self.fecha_vigencia_inicio and self.fecha_vigencia_fin:
            raise ValueError("Si defines fecha de fin, debes definir fecha de inicio")
        
        return self

    # 🔒 SECURITY: Validación de prioridad
    @field_validator('prioridad')
    @classmethod
    def validate_prioridad(cls, v: int) -> int:
        """Validación de prioridad 1-10"""
        if not isinstance(v, int):
            raise ValueError("La prioridad debe ser un número entero")
        if v < 1 or v > 10:
            raise ValueError(f"La prioridad debe estar entre 1 y 10 (actual: {v})")
        return v


class UnidadContenidoCreate(UnidadContenidoBase):
    id_agente: int = Field(..., gt=0, description="ID del agente asociado")
    id_categoria: int = Field(..., gt=0, description="ID de la categoría")
    id_departamento: Optional[int] = Field(None, gt=0, description="ID del departamento")
    
    # 🔥 Usar Literal para validar solo valores válidos
    estado: Literal["activo", "inactivo"] = Field("activo", description="Estado del contenido")

    # 🔒 SECURITY: Validación de IDs
    @field_validator('id_agente', 'id_categoria', 'id_departamento')
    @classmethod
    def validate_ids(cls, v: Optional[int]) -> Optional[int]:
        """
        ✅ Validación de IDs: Deben ser números positivos
        """
        if v is None:
            return None
        
        if not isinstance(v, int):
            raise ValueError("El ID debe ser un número entero")
        
        if v <= 0:
            raise ValueError(f"El ID debe ser mayor que 0 (actual: {v})")
        
        if v > 999999:
            raise ValueError(f"El ID es demasiado grande (máx: 999999)")
        
        return v


class UnidadContenidoUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=5, max_length=200)
    contenido: Optional[str] = Field(None, min_length=1, max_length=50000)
    resumen: Optional[str] = Field(None, min_length=10, max_length=2000)
    palabras_clave: Optional[str] = Field(None, min_length=3, max_length=1000)
    etiquetas: Optional[str] = Field(None, min_length=3, max_length=1000)
    prioridad: Optional[int] = Field(None, ge=1, le=10)
    estado: Optional[Literal["activo", "inactivo"]] = None
    fecha_vigencia_inicio: Optional[date] = None
    fecha_vigencia_fin: Optional[date] = None
    id_agente: Optional[int] = Field(None, gt=0)
    id_categoria: Optional[int] = Field(None, gt=0)
    id_departamento: Optional[int] = Field(None, gt=0)

    # 🔒 SECURITY: Aplicar las mismas validaciones que en Create
    @field_validator('titulo', 'contenido', 'resumen', 'palabras_clave', 'etiquetas')
    @classmethod
    def sanitize_input(cls, v: Optional[str]) -> Optional[str]:
        """✅ XSS Protection"""
        if v is None:
            return None
        
        if not isinstance(v, str):
            return str(v)
        
        v = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', v, flags=re.IGNORECASE)
        v = re.sub(r'<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>', '', v, flags=re.IGNORECASE)
        v = re.sub(r'javascript:', '', v, flags=re.IGNORECASE)
        v = re.sub(r'on\w+\s*=', '', v, flags=re.IGNORECASE)
        v = escape(v)
        
        return v.strip()

    @field_validator('titulo', 'contenido', 'resumen', 'palabras_clave', 'etiquetas')
    @classmethod
    def prevent_sql_injection(cls, v: Optional[str]) -> Optional[str]:
        """✅ SQL Injection Protection"""
        if v is None:
            return None
        
        suspicious_patterns = [
            r"('\s*(OR|AND)\s*'?\d)",
            r"(--|\#|\/\*|\*\/)",
            r"(UNION\s+SELECT)",
            r"(DROP\s+TABLE)",
            r"(INSERT\s+INTO)",
            r"(DELETE\s+FROM)",
            r"(UPDATE\s+\w+\s+SET)",
            r"(EXEC\s*\()",
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Contenido sospechoso detectado")
        
        return v

    @field_validator('id_agente', 'id_categoria', 'id_departamento')
    @classmethod
    def validate_ids(cls, v: Optional[int]) -> Optional[int]:
        """✅ Validación de IDs"""
        if v is None:
            return None
        if v <= 0 or v > 999999:
            raise ValueError(f"ID inválido: {v}")
        return v

    @model_validator(mode='after')
    def validate_date_range(self):
        """✅ Validación de rango de fechas"""
        if self.fecha_vigencia_inicio and self.fecha_vigencia_fin:
            if self.fecha_vigencia_fin < self.fecha_vigencia_inicio:
                raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")
            
            delta = (self.fecha_vigencia_fin - self.fecha_vigencia_inicio).days
            if delta > 10 * 365:
                raise ValueError("El rango de fechas no puede superar 10 años")
        
        elif self.fecha_vigencia_inicio and not self.fecha_vigencia_fin:
            raise ValueError("Si defines fecha de inicio, debes definir fecha de fin")
        elif not self.fecha_vigencia_inicio and self.fecha_vigencia_fin:
            raise ValueError("Si defines fecha de fin, debes definir fecha de inicio")
        
        return self


class UnidadContenidoResponse(BaseModel):
    """Response sin validaciones estrictas (para lectura de datos existentes)"""
    id_contenido: int
    titulo: str
    contenido: str
    resumen: Optional[str] = None
    palabras_clave: Optional[str] = None
    etiquetas: Optional[str] = None
    prioridad: int
    fecha_vigencia_inicio: Optional[date] = None
    fecha_vigencia_fin: Optional[date] = None
    
    id_agente: int
    id_categoria: int
    id_departamento: Optional[int] = None
    estado: str
    version: int
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    
    # 🔥 Campos de soft delete
    eliminado: bool = False
    fecha_eliminacion: Optional[datetime] = None
    eliminado_por: Optional[int] = None
    
    # Campos de auditoría adicionales
    creado_por: Optional[int] = None
    actualizado_por: Optional[int] = None
    publicado_por: Optional[int] = None
    fecha_publicacion: Optional[datetime] = None
    
    # Nombres relacionados (joins)
    agente_nombre: Optional[str] = None
    categoria_nombre: Optional[str] = None
    area_especialidad: Optional[str] = None
    
    class Config:
        from_attributes = True


class UnidadContenidoListResponse(BaseModel):
    """Schema simplificado para listados (sin contenido completo)"""
    id_contenido: int
    titulo: str
    resumen: Optional[str] = None
    id_agente: int
    id_categoria: int
    estado: str
    prioridad: int
    fecha_creacion: datetime
    eliminado: bool = False
    fecha_eliminacion: Optional[datetime] = None
    
    agente_nombre: Optional[str] = None
    categoria_nombre: Optional[str] = None
    
    class Config:
        from_attributes = True


class UnidadContenidoPapeleraResponse(BaseModel):
    """Schema específico para la papelera"""
    id_contenido: int
    titulo: str
    id_agente: int
    agente_nombre: Optional[str] = None
    estado: str
    fecha_creacion: datetime
    fecha_eliminacion: datetime
    eliminado_por: Optional[int] = None
    
    class Config:
        from_attributes = True


class DeleteResponse(BaseModel):
    """Response para operaciones de eliminación"""
    ok: bool
    id_contenido: int
    tipo_eliminacion: Literal["logica", "fisica"]
    deleted_from_chromadb: Optional[bool] = None
    deleted_from_database: bool
    mensaje: Optional[str] = None


class RestoreResponse(BaseModel):
    """Response para operación de restauración"""
    ok: bool
    id_contenido: int
    mensaje: str
    contenido: UnidadContenidoResponse


# 🔒 SECURITY: Schema para detección de duplicados
class DuplicateCheckRequest(BaseModel):
    """Request para verificar contenido duplicado"""
    titulo: str = Field(..., min_length=5)
    contenido: str = Field(..., min_length=50)
    id_contenido_excluir: Optional[int] = None  # Para excluir al editar


class DuplicateCheckResponse(BaseModel):
    """Response con información de duplicados"""
    tiene_duplicados: bool
    similitud: float  # Porcentaje de similitud (0-1)
    contenidos_similares: list[UnidadContenidoListResponse]
    mensaje: Optional[str] = None