from exceptions.base import ValidationException
from exceptions.base import ValidationException
from typing import Optional
from sqlalchemy.orm import Session
from repositories.usuario_agente_repo import UsuarioAgenteRepository,UsuarioAgenteCreate,UsuarioAgenteUpdate


class UsuarioAgenteService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UsuarioAgenteRepository(db)
    
    def asignar_usuario_agente(self, data: UsuarioAgenteCreate, asignado_por: Optional[int] = None):
        # Validación: al menos un permiso debe estar activo
        permisos = [
            data.puede_ver_contenido, data.puede_crear_contenido,
            data.puede_editar_contenido, data.puede_ver_metricas
        ]
        if not any(permisos):
            raise ValidationException("Debe otorgar al menos un permiso")
        
        return self.repo.create(data, asignado_por)
    
    def listar_por_usuario(self, id_usuario: int, activo: Optional[bool] = None):
        return self.repo.get_by_usuario(id_usuario, activo)
    
    def listar_por_agente(self, id_agente: int, activo: Optional[bool] = None):
        return self.repo.get_by_agente(id_agente, activo)
    
    def actualizar_permisos(self, id_usuario_agente: int, data: UsuarioAgenteUpdate):
        return self.repo.update(id_usuario_agente, data)
    
    def revocar_acceso(self, id_usuario_agente: int):
        return self.repo.delete(id_usuario_agente)