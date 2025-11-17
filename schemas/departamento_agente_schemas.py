from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DepartamentoAgenteBase(BaseModel):
    puede_ver_contenido: bool = True
    puede_crear_contenido: bool = True
    puede_editar_contenido: bool = False
    puede_eliminar_contenido: bool = False
    puede_ver_metricas: bool = True

class DepartamentoAgenteCreate(DepartamentoAgenteBase):
    id_departamento: int
    id_agente: int

class DepartamentoAgenteUpdate(BaseModel):
    puede_ver_contenido: Optional[bool] = None
    puede_crear_contenido: Optional[bool] = None
    puede_editar_contenido: Optional[bool] = None
    puede_eliminar_contenido: Optional[bool] = None
    puede_ver_metricas: Optional[bool] = None
    activo: Optional[bool] = None

class DepartamentoAgenteResponse(DepartamentoAgenteBase):
    id_depto_agente: int
    id_departamento: int
    id_agente: int
    fecha_asignacion: datetime
    activo: bool
    
    class Config:
        from_attributes = True

