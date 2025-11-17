from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CategoriaBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = None
    id_categoria_padre: Optional[int] = None
    icono: Optional[str] = None
    color: Optional[str] = None
    orden: int = 0

class CategoriaCreate(CategoriaBase):
    id_agente: int

class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    id_categoria_padre: Optional[int] = None
    icono: Optional[str] = None
    color: Optional[str] = None
    orden: Optional[int] = None
    activo: Optional[bool] = None

class CategoriaResponse(CategoriaBase):
    id_categoria: int
    id_agente: int
    activo: bool
    fecha_creacion: datetime
    class Config:
        from_attributes = True