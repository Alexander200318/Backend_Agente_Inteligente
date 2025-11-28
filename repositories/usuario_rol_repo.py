from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
from datetime import datetime
from models.usuario_rol import UsuarioRol
from models.usuario import Usuario
from models.rol import Rol
from exceptions.base import NotFoundException, AlreadyExistsException, DatabaseException
from schemas.usuario_rol_schemas import UsuarioRolCreate, UsuarioRolUpdate

class UsuarioRolRepository:
    """Repositorio para operaciones de base de datos de UsuarioRol"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, usuario_rol_data: UsuarioRolCreate, asignado_por_id: Optional[int] = None) -> UsuarioRol:
        """Crear nueva asignación de rol a usuario"""
        try:
            # Verificar si ya existe la asignación activa
            asignacion_existente = self.get_by_usuario_y_rol(
                usuario_rol_data.id_usuario, 
                usuario_rol_data.id_rol
            )
            
            if asignacion_existente and asignacion_existente.activo:
                raise AlreadyExistsException(
                    "UsuarioRol", 
                    "asignación", 
                    f"Usuario {usuario_rol_data.id_usuario} - Rol {usuario_rol_data.id_rol}"
                )
            
            usuario_rol = UsuarioRol(
                id_usuario=usuario_rol_data.id_usuario,
                id_rol=usuario_rol_data.id_rol,
                motivo=usuario_rol_data.motivo,
                fecha_expiracion=usuario_rol_data.fecha_expiracion,
                asignado_por=asignado_por_id
            )
            
            self.db.add(usuario_rol)
            self.db.commit()
            self.db.refresh(usuario_rol)
            return usuario_rol
            
        except IntegrityError as e:
            self.db.rollback()
            # Puede ser FK constraint (usuario o rol no existe)
            if "foreign key constraint" in str(e).lower():
                raise NotFoundException("Usuario o Rol", "referenciado")
            raise AlreadyExistsException("UsuarioRol", "asignación", "duplicada")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al crear asignación de rol: {str(e)}")
    
    def get_by_id(self, id_usuario_rol: int, include_relations: bool = False) -> UsuarioRol:
        """Obtener asignación por ID"""
        query = self.db.query(UsuarioRol)
        
        if include_relations:
            query = query.options(
                joinedload(UsuarioRol.usuario),
                joinedload(UsuarioRol.rol)
            )
        
        usuario_rol = query.filter(UsuarioRol.id_usuario_rol == id_usuario_rol).first()
        
        if not usuario_rol:
            raise NotFoundException("UsuarioRol", id_usuario_rol)
        
        return usuario_rol
    
    def get_by_usuario_y_rol(self, id_usuario: int, id_rol: int) -> Optional[UsuarioRol]:
        """Obtener asignación específica de usuario-rol"""
        return self.db.query(UsuarioRol).filter(
            UsuarioRol.id_usuario == id_usuario,
            UsuarioRol.id_rol == id_rol
        ).first()
    
    def get_roles_by_usuario(
        self, 
        id_usuario: int, 
        solo_activos: bool = True,
        include_relations: bool = True
    ) -> List[UsuarioRol]:
        """Obtener todos los roles de un usuario"""
        query = self.db.query(UsuarioRol).filter(UsuarioRol.id_usuario == id_usuario)
        
        if solo_activos:
            query = query.filter(UsuarioRol.activo == 1)
        
        if include_relations:
            query = query.options(joinedload(UsuarioRol.rol))
        
        return query.all()
    
    def get_usuarios_by_rol(
        self, 
        id_rol: int, 
        solo_activos: bool = True,
        include_relations: bool = True
    ) -> List[UsuarioRol]:
        """Obtener todos los usuarios que tienen un rol específico"""
        query = self.db.query(UsuarioRol).filter(UsuarioRol.id_rol == id_rol)
        
        if solo_activos:
            query = query.filter(UsuarioRol.activo == 1)
        
        if include_relations:
            query = query.options(joinedload(UsuarioRol.usuario))
        
        return query.all()
    
    def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        id_usuario: Optional[int] = None,
        id_rol: Optional[int] = None,
        solo_activos: Optional[bool] = None,
        include_relations: bool = True
    ) -> List[UsuarioRol]:
        """Listar asignaciones con filtros"""
        query = self.db.query(UsuarioRol)
        
        if id_usuario:
            query = query.filter(UsuarioRol.id_usuario == id_usuario)
        
        if id_rol:
            query = query.filter(UsuarioRol.id_rol == id_rol)
        
        if solo_activos is not None:
            query = query.filter(UsuarioRol.activo == solo_activos)
        
        if include_relations:
            query = query.options(
                joinedload(UsuarioRol.usuario),
                joinedload(UsuarioRol.rol)
            )
        
        return query.offset(skip).limit(limit).all()
    
    def update(self, id_usuario_rol: int, usuario_rol_data: UsuarioRolUpdate) -> UsuarioRol:
        """Actualizar asignación de rol"""
        try:
            usuario_rol = self.get_by_id(id_usuario_rol)
            
            update_data = usuario_rol_data.dict(exclude_unset=True)
            
            for field, value in update_data.items():
                setattr(usuario_rol, field, value)
            
            self.db.commit()
            self.db.refresh(usuario_rol)
            return usuario_rol
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar asignación de rol: {str(e)}")
    
    def delete(self, id_usuario_rol: int) -> dict:
        """Desactivar asignación de rol (soft delete)"""
        usuario_rol = self.get_by_id(id_usuario_rol, include_relations=True)
        
        try:
            usuario_rol.activo = False
            self.db.commit()
            
            return {
                "message": "Asignación de rol desactivada",
                "id_usuario_rol": id_usuario_rol,
                "usuario": usuario_rol.usuario.username if usuario_rol.usuario else None,
                "rol": usuario_rol.rol.nombre_rol if usuario_rol.rol else None
            }
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al desactivar asignación de rol: {str(e)}")
    
    def delete_permanente(self, id_usuario_rol: int) -> dict:
        """Eliminar asignación de rol permanentemente (hard delete)"""
        usuario_rol = self.get_by_id(id_usuario_rol)
        
        try:
            self.db.delete(usuario_rol)
            self.db.commit()
            
            return {
                "message": "Asignación de rol eliminada permanentemente",
                "id_usuario_rol": id_usuario_rol
            }
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al eliminar asignación de rol: {str(e)}")
    
    def revocar_rol_usuario(self, id_usuario: int, id_rol: int) -> dict:
        """Revocar un rol específico de un usuario"""
        usuario_rol = self.get_by_usuario_y_rol(id_usuario, id_rol)
        
        if not usuario_rol:
            raise NotFoundException("UsuarioRol", f"Usuario {id_usuario} - Rol {id_rol}")
        
        if not usuario_rol.activo:
            raise DatabaseException("La asignación ya está inactiva")
        
        return self.delete(usuario_rol.id_usuario_rol)
    
    def revocar_todos_roles_usuario(self, id_usuario: int) -> dict:
        """Revocar todos los roles de un usuario"""
        roles = self.get_roles_by_usuario(id_usuario, solo_activos=True)
        
        if not roles:
            raise NotFoundException("Roles activos", f"para usuario {id_usuario}")
        
        try:
            count = 0
            for rol_asignacion in roles:
                rol_asignacion.activo = False
                count += 1
            
            self.db.commit()
            
            return {
                "message": f"Se revocaron {count} roles del usuario",
                "roles_revocados": count
            }
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al revocar roles: {str(e)}")
    
    def verificar_expiraciones(self) -> int:
        """Desactivar asignaciones expiradas (tarea programada)"""
        try:
            asignaciones_expiradas = self.db.query(UsuarioRol).filter(
                UsuarioRol.activo == 1,
                UsuarioRol.fecha_expiracion != None,
                UsuarioRol.fecha_expiracion <= datetime.now()
            ).all()
            
            count = 0
            for asignacion in asignaciones_expiradas:
                asignacion.activo = False
                count += 1
            
            if count > 0:
                self.db.commit()
            
            return count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al verificar expiraciones: {str(e)}")
    
    def count(
        self, 
        id_usuario: Optional[int] = None,
        id_rol: Optional[int] = None,
        solo_activos: Optional[bool] = None
    ) -> int:
        """Contar asignaciones con filtros"""
        query = self.db.query(UsuarioRol)
        
        if id_usuario:
            query = query.filter(UsuarioRol.id_usuario == id_usuario)
        
        if id_rol:
            query = query.filter(UsuarioRol.id_rol == id_rol)
        
        if solo_activos is not None:
            query = query.filter(UsuarioRol.activo == solo_activos)
        
        return query.count()
    
    def usuario_tiene_rol(self, id_usuario: int, id_rol: int, solo_activos: bool = True) -> bool:
        """Verificar si un usuario tiene un rol específico"""
        query = self.db.query(UsuarioRol).filter(
            UsuarioRol.id_usuario == id_usuario,
            UsuarioRol.id_rol == id_rol
        )
        
        if solo_activos:
            query = query.filter(UsuarioRol.activo == 1)
        
        return query.first() is not None
    
    def get_usuario_by_id(self, id_usuario: int) -> Optional[Usuario]:
        """Obtener usuario por ID"""
        return self.db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    
    def get_rol_by_id(self, id_rol: int) -> Optional[Rol]:
        """Obtener rol por ID"""
        return self.db.query(Rol).filter(Rol.id_rol == id_rol).first()