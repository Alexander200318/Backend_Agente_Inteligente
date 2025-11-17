from exceptions.base import ValidationException
from typing import Optional, List
from sqlalchemy.orm import Session
from repositories.rol_repo import RolRepository,RolCreate,RolUpdate,Rol




class RolService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RolRepository(db)
    
    def crear_rol(self, rol_data: RolCreate, creado_por_id: Optional[int] = None) -> Rol:
        # Validación: Super Admin solo nivel 1
        if rol_data.nivel_jerarquia == 1 and not rol_data.puede_configurar_sistema:
            raise ValidationException("Super Admin debe tener todos los permisos")
        
        return self.repo.create(rol_data, creado_por_id)
    
    def obtener_rol(self, id_rol: int) -> Rol:
        return self.repo.get_by_id(id_rol)
    
    def listar_roles(self, skip: int = 0, limit: int = 100, activo: Optional[bool] = None) -> List[Rol]:
        if limit > 500:
            raise ValidationException("Límite máximo: 500")
        return self.repo.get_all(skip, limit, activo)
    
    def actualizar_rol(self, id_rol: int, rol_data: RolUpdate) -> Rol:
        return self.repo.update(id_rol, rol_data)
    
    def eliminar_rol(self, id_rol: int) -> dict:
        rol = self.repo.get_by_id(id_rol)
        
        # No eliminar Super Admin
        if rol.nivel_jerarquia == 1:
            raise ValidationException("No se puede eliminar el rol de Super Administrador")
        
        return self.repo.delete(id_rol)
    
    def obtener_estadisticas(self) -> dict:
        return {
            "total_roles": self.repo.count(),
            "roles_activos": self.repo.count(activo=True),
            "roles_inactivos": self.repo.count(activo=False)
        }