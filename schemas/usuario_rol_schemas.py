from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class UsuarioRolBase(BaseModel):
    """Schema base para UsuarioRol"""
    id_usuario: int = Field(..., gt=0, description="ID del usuario")
    id_rol: int = Field(..., gt=0, description="ID del rol")
    motivo: Optional[str] = Field(None, max_length=500, description="Motivo de la asignación")
    fecha_expiracion: Optional[datetime] = Field(None, description="Fecha de expiración del rol (opcional)")
    
    @validator('fecha_expiracion')
    def validar_fecha_expiracion(cls, v):
        if v and v <= datetime.now():
            raise ValueError('La fecha de expiración debe ser futura')
        return v

class UsuarioRolCreate(UsuarioRolBase):
    """Schema para crear asignación de rol a usuario"""
    pass

class UsuarioRolUpdate(BaseModel):
    """Schema para actualizar asignación de rol"""
    fecha_expiracion: Optional[datetime] = None
    motivo: Optional[str] = Field(None, max_length=500)
    activo: Optional[bool] = None
    
    @validator('fecha_expiracion')
    def validar_fecha_expiracion(cls, v):
        if v and v <= datetime.now():
            raise ValueError('La fecha de expiración debe ser futura')
        return v

class UsuarioRolResponse(BaseModel):
    """Schema de respuesta para UsuarioRol"""
    id_usuario_rol: int
    id_usuario: int
    id_rol: int
    fecha_asignacion: datetime
    fecha_expiracion: Optional[datetime]
    motivo: Optional[str]
    activo: bool
    
    # Datos adicionales del usuario
    usuario_username: Optional[str] = None
    usuario_email: Optional[str] = None
    
    # Datos adicionales del rol
    rol_nombre: Optional[str] = None
    rol_nivel_jerarquia: Optional[int] = None
    
    class Config:
        from_attributes = True

class AsignarRolRequest(BaseModel):
    """Schema simplificado para asignar rol desde endpoint de usuario"""
    id_rol: int = Field(..., gt=0, description="ID del rol a asignar")
    motivo: Optional[str] = Field(None, max_length=500, description="Motivo de la asignación")
    fecha_expiracion: Optional[datetime] = Field(None, description="Fecha de expiración (opcional)")
    
    @validator('fecha_expiracion')
    def validar_fecha_expiracion(cls, v):
        if v and v <= datetime.now():
            raise ValueError('La fecha de expiración debe ser futura')
        return v

class AsignarMultiplesRolesRequest(BaseModel):
    """Schema para asignar múltiples roles a un usuario"""
    roles: list[int] = Field(..., min_items=1, description="Lista de IDs de roles")
    motivo: Optional[str] = Field(None, max_length=500)
    fecha_expiracion: Optional[datetime] = None
    
    @validator('roles')
    def validar_roles_unicos(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Los IDs de roles deben ser únicos')
        return v
    
    @validator('fecha_expiracion')
    def validar_fecha_expiracion(cls, v):
        if v and v <= datetime.now():
            raise ValueError('La fecha de expiración debe ser futura')
        return v