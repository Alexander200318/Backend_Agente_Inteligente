from datetime import date

from typing import Optional
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

class UnidadContenidoUpdate(BaseModel):
    titulo: Optional[str] = None
    contenido: Optional[str] = None
    resumen: Optional[str] = None
    palabras_clave: Optional[str] = None
    etiquetas: Optional[str] = None
    prioridad: Optional[int] = None
    estado: Optional[str] = None
    fecha_vigencia_inicio: Optional[date] = None
    fecha_vigencia_fin: Optional[date] = None

class UnidadContenidoResponse(UnidadContenidoBase):
    id_contenido: int
    id_agente: int
    id_categoria: int
    estado: str
    version: int
    fecha_creacion: datetime
    class Config:
        from_attributes = True