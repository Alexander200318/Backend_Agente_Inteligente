from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UsuarioAgenteBase(BaseModel):
    puede_ver_contenido: bool = True
    puede_crear_contenido: bool = True
    puede_editar_contenido: bool = True
    puede_eliminar_contenido: bool = False
    puede_publicar_contenido: bool = False
    puede_ver_metricas: bool = True
    puede_exportar_datos: bool = False
    puede_configurar_agente: bool = False
    puede_gestionar_permisos: bool = False
    puede_gestionar_categorias: bool = False
    puede_gestionar_widgets: bool = False

class UsuarioAgenteCreate(UsuarioAgenteBase):
    id_usuario: int
    id_agente: int
    notas: Optional[str] = None

class UsuarioAgenteUpdate(BaseModel):
    puede_ver_contenido: Optional[bool] = None
    puede_crear_contenido: Optional[bool] = None
    puede_editar_contenido: Optional[bool] = None
    puede_eliminar_contenido: Optional[bool] = None
    puede_publicar_contenido: Optional[bool] = None
    puede_ver_metricas: Optional[bool] = None
    puede_exportar_datos: Optional[bool] = None
    puede_configurar_agente: Optional[bool] = None
    puede_gestionar_permisos: Optional[bool] = None
    puede_gestionar_categorias: Optional[bool] = None
    puede_gestionar_widgets: Optional[bool] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None

class UsuarioAgenteResponse(UsuarioAgenteBase):
    id_usuario_agente: int
    id_usuario: int
    id_agente: int
    fecha_asignacion: datetime
    activo: bool
    
    class Config:
        from_attributes = True