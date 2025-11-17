from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional
from datetime import datetime

class DepartamentoBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = None
    codigo: str = Field(..., min_length=2, max_length=20)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = Field(None, max_length=20)
    ubicacion: Optional[str] = Field(None, max_length=255)
    facultad: Optional[str] = Field(None, max_length=100)
    
    @validator('nombre', 'codigo')
    def validar_no_vacio(cls, v):
        if not v or not v.strip():
            raise ValueError('Este campo no puede estar vacío')
        return v.strip()
    
    @validator('codigo')
    def validar_codigo_mayusculas(cls, v):
        return v.upper()
    
    @validator('telefono')
    def validar_telefono(cls, v):
        if v:
            telefono_limpio = v.strip().replace('-', '').replace(' ', '')
            if not telefono_limpio.isdigit():
                raise ValueError('El teléfono debe contener solo números')
            if len(telefono_limpio) < 7 or len(telefono_limpio) > 15:
                raise ValueError('Número de teléfono inválido')
        return v

class DepartamentoCreate(DepartamentoBase):
    pass

class DepartamentoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = None
    codigo: Optional[str] = Field(None, min_length=2, max_length=20)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    ubicacion: Optional[str] = None
    facultad: Optional[str] = None
    jefe_departamento: Optional[int] = None
    activo: Optional[bool] = None

class DepartamentoResponse(DepartamentoBase):
    id_departamento: int
    jefe_departamento: Optional[int]
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime]
    
    class Config:
        from_attributes = True

class DepartamentoConEstadisticas(DepartamentoResponse):
    total_personas: int = 0
    total_agentes: int = 0
    total_contenidos: int = 0