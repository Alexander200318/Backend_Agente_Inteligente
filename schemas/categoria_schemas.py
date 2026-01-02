from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class CategoriaBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = None
    id_categoria_padre: Optional[int] = None
    creado_por: Optional[int] = None
    icono: Optional[str] = None
    color: Optional[str] = None
    orden: int = 0
    
    @field_validator('id_categoria_padre')
    @classmethod
    def convert_zero_to_none(cls, v):
        """Convierte 0 a None para categorías raíz"""
        return None if v == 0 else v

class CategoriaCreate(CategoriaBase):
    id_agente: int
    eliminado: Optional[bool] = False  # ✅ NUEVO

class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    id_categoria_padre: Optional[int] = None
    icono: Optional[str] = None
    creado_por: Optional[int] = None
    color: Optional[str] = None
    orden: Optional[int] = None
    activo: Optional[bool] = None
    eliminado: Optional[bool] = None
    id_agente: Optional[int] = None 

    @field_validator('id_categoria_padre')
    @classmethod
    def convert_zero_to_none(cls, v):
        return None if v == 0 else v


class CategoriaResponse(CategoriaBase):
    id_categoria: int
    id_agente: int
    activo: bool
    eliminado: bool  # ✅ NUEVO
    creado_por: Optional[int] = None
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True