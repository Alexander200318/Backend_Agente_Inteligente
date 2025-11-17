from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
from models.rol import Rol
from exceptions.base import NotFoundException, AlreadyExistsException, DatabaseException
from schemas.rol_schemas import RolCreate, RolUpdate
class RolRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, rol_data: RolCreate, creado_por_id: Optional[int] = None) -> Rol:
        try:
            if self.get_by_nombre(rol_data.nombre_rol):
                raise AlreadyExistsException("Rol", "nombre", rol_data.nombre_rol)
            
            rol = Rol(**rol_data.dict())
            if creado_por_id:
                rol.creado_por = creado_por_id
            
            self.db.add(rol)
            self.db.commit()
            self.db.refresh(rol)
            return rol
        except IntegrityError as e:
            self.db.rollback()
            raise AlreadyExistsException("Rol", "nombre", rol_data.nombre_rol)
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al crear rol: {str(e)}")
    
    def get_by_id(self, id_rol: int) -> Rol:
        rol = self.db.query(Rol).filter(Rol.id_rol == id_rol).first()
        if not rol:
            raise NotFoundException("Rol", id_rol)
        return rol
    
    def get_by_nombre(self, nombre: str) -> Optional[Rol]:
        return self.db.query(Rol).filter(Rol.nombre_rol == nombre).first()
    
    def get_all(self, skip: int = 0, limit: int = 100, activo: Optional[bool] = None) -> List[Rol]:
        query = self.db.query(Rol)
        if activo is not None:
            query = query.filter(Rol.activo == activo)
        return query.order_by(Rol.nivel_jerarquia, Rol.nombre_rol).offset(skip).limit(limit).all()
    
    def update(self, id_rol: int, rol_data: RolUpdate) -> Rol:
        try:
            rol = self.get_by_id(id_rol)
            update_data = rol_data.dict(exclude_unset=True)
            
            if 'nombre_rol' in update_data:
                existing = self.get_by_nombre(update_data['nombre_rol'])
                if existing and existing.id_rol != id_rol:
                    raise AlreadyExistsException("Rol", "nombre", update_data['nombre_rol'])
            
            for field, value in update_data.items():
                setattr(rol, field, value)
            
            self.db.commit()
            self.db.refresh(rol)
            return rol
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar rol: {str(e)}")
    
    def delete(self, id_rol: int) -> dict:
        rol = self.get_by_id(id_rol)
        try:
            rol.activo = False
            self.db.commit()
            return {"message": "Rol desactivado", "id_rol": id_rol}
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al desactivar rol: {str(e)}")
    
    def count(self, activo: Optional[bool] = None) -> int:
        query = self.db.query(Rol)
        if activo is not None:
            query = query.filter(Rol.activo == activo)
        return query.count()
