from pydantic import BaseModel, Field
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


# SCHEMAS NUEVOS PARA VERIFICACIÓN DE PERMISOS 

class PermisosDetalleSchema(BaseModel):
    """Schema para detallar todos los permisos de un usuario sobre un agente"""
    puede_ver_contenido: bool
    puede_crear_contenido: bool
    puede_editar_contenido: bool
    puede_eliminar_contenido: bool
    puede_publicar_contenido: bool
    puede_ver_metricas: bool
    puede_exportar_datos: bool
    puede_configurar_agente: bool
    puede_gestionar_permisos: bool
    puede_gestionar_categorias: bool
    puede_gestionar_widgets: bool

    class Config:
        from_attributes = True


class VerificacionPermisosResponse(BaseModel):
    """Respuesta para endpoint de verificación de permisos"""
    tiene_acceso: bool
    id_usuario: int
    id_agente: int
    permisos: PermisosDetalleSchema
    activo: bool
    fecha_asignacion: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentesAccesiblesResponse(BaseModel):
    """Respuesta con lista de agentes accesibles por un usuario"""
    id_usuario: int
    agentes_accesibles: list[int] = Field(default_factory=list, description="Lista de IDs de agentes")
    total_agentes: int = Field(description="Cantidad total de agentes accesibles")

    class Config:
        from_attributes = True