# schemas/unidad_contenido_schemas.py
from datetime import date, datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field

class UnidadContenidoBase(BaseModel):
    titulo: str = Field(..., min_length=5, max_length=200)
    contenido: str = Field(..., min_length=10)
    resumen: Optional[str] = None
    palabras_clave: Optional[str] = None
    etiquetas: Optional[str] = None
    prioridad: int = Field(5, ge=1, le=10)
    fecha_vigencia_inicio: Optional[date] = None
    fecha_vigencia_fin: Optional[date] = None

class UnidadContenidoCreate(UnidadContenidoBase):
    id_agente: int
    id_categoria: int
    id_departamento: Optional[int] = None
    # 🔥 Usar Literal para validar solo valores válidos
    estado: Literal["borrador", "revision", "activo", "inactivo", "archivado"] = "borrador"

class UnidadContenidoUpdate(BaseModel):
    titulo: Optional[str] = None
    contenido: Optional[str] = None
    resumen: Optional[str] = None
    palabras_clave: Optional[str] = None
    etiquetas: Optional[str] = None
    prioridad: Optional[int] = None
    estado: Optional[Literal["borrador", "revision", "activo", "inactivo", "archivado"]] = None
    fecha_vigencia_inicio: Optional[date] = None
    fecha_vigencia_fin: Optional[date] = None
    id_agente: Optional[int] = None
    id_categoria: Optional[int] = None
    id_departamento: Optional[int] = None

class UnidadContenidoResponse(UnidadContenidoBase):
    id_contenido: int
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