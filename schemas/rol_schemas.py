from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class RolBase(BaseModel):
    nombre_rol: str = Field(..., min_length=3, max_length=50)
    descripcion: Optional[str] = None
    nivel_jerarquia: int = Field(3, ge=1, le=4, description="1=Super Admin, 2=Admin, 3=Funcionario, 4=Usuario básico")
    
    # Permisos globales
    puede_gestionar_usuarios: bool = False
    puede_gestionar_departamentos: bool = False
    puede_gestionar_roles: bool = False
    puede_ver_todas_metricas: bool = False
    puede_exportar_datos_globales: bool = False
    puede_configurar_sistema: bool = False
    puede_gestionar_api_keys: bool = False

class RolCreate(RolBase):
    pass

class RolUpdate(BaseModel):
    nombre_rol: Optional[str] = None
    descripcion: Optional[str] = None
    nivel_jerarquia: Optional[int] = Field(None, ge=1, le=4)
    puede_gestionar_usuarios: Optional[bool] = None
    puede_gestionar_departamentos: Optional[bool] = None
    puede_gestionar_roles: Optional[bool] = None
    puede_ver_todas_metricas: Optional[bool] = None
    puede_exportar_datos_globales: Optional[bool] = None
    puede_configurar_sistema: Optional[bool] = None
    puede_gestionar_api_keys: Optional[bool] = None
    activo: Optional[bool] = None

class RolResponse(RolBase):
    id_rol: int
    activo: bool
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True