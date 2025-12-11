# schemas/unidad_contenido.py
from datetime import date
from typing import Optional, Literal
from datetime import date, datetime
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
    estado: str
    version: int
    fecha_creacion: datetime
    
    agente_nombre: Optional[str] = None
    categoria_nombre: Optional[str] = None
    
    class Config:
        from_attributes = True