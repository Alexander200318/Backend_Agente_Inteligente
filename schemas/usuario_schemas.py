from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum
from schemas.persona_schemas import PersonaCreate, PersonaResponse

class EstadoUsuarioEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"
    suspendido = "suspendido"
    bloqueado = "bloqueado"

class UsuarioBase(BaseModel):
    username: str = Field(..., min_length=4, max_length=50)
    email: EmailStr

    @validator('username')
    def validar_username(cls, v):
        if not v.strip():
            raise ValueError('El username no puede estar vacío')
        # Solo alfanuméricos, guiones y guiones bajos
        if not all(c.isalnum() or c in ['_', '-'] for c in v):
            raise ValueError('Username solo puede contener letras, números, guiones y guiones bajos')
        return v.strip().lower()

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8, max_length=100)
    persona: PersonaCreate
    
    @validator('password')
    def validar_password(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

class UsuarioUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=4, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    estado: Optional[EstadoUsuarioEnum] = None

class UsuarioResponse(UsuarioBase):
    id_usuario: int
    id_persona: int
    estado: EstadoUsuarioEnum
    requiere_cambio_password: bool
    intentos_fallidos: int
    ultimo_acceso: Optional[datetime]
    fecha_creacion: datetime
    persona: Optional[PersonaResponse]

    class Config:
        from_attributes = True

class UsuarioLogin(BaseModel):
    username: str = Field(..., min_length=4)
    password: str = Field(..., min_length=8)

class UsuarioLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse

class CambioPasswordRequest(BaseModel):
    password_actual: str = Field(..., min_length=8)
    password_nueva: str = Field(..., min_length=8)
    
    @validator('password_nueva')
    def validar_password_nueva(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v