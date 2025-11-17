from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
from datetime import datetime
from models.usuario import Usuario
from models.persona import Persona
from schemas.usuario_schemas import UsuarioCreate, UsuarioUpdate
from schemas.persona_schemas import PersonaCreate
from exceptions.base import (
    NotFoundException, 
    AlreadyExistsException, 
    DatabaseException,
    ValidationException
)

class UsuarioRepository:
    """Repositorio para operaciones CRUD de Usuario"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, usuario_data: UsuarioCreate, persona: Persona) -> Usuario:
        """Crear un nuevo usuario vinculado a una persona"""
        try:
            # Verificar duplicados
            if self.get_by_username(usuario_data.username):
                raise AlreadyExistsException("Usuario", "username", usuario_data.username)
            
            if self.get_by_email(usuario_data.email):
                raise AlreadyExistsException("Usuario", "email", usuario_data.email)
            
            # Crear usuario (la contraseña será hasheada en el service)
            usuario = Usuario(
                id_persona=persona.id_persona,
                username=usuario_data.username,
                email=usuario_data.email,
                password=usuario_data.password  # Ya viene hasheada del service
            )
            
            self.db.add(usuario)
            self.db.commit()
            self.db.refresh(usuario)
            return usuario
            
        except IntegrityError as e:
            self.db.rollback()
            error_msg = str(e.orig).lower()
            if 'username' in error_msg:
                raise AlreadyExistsException("Usuario", "username", usuario_data.username)
            elif 'email' in error_msg:
                raise AlreadyExistsException("Usuario", "email", usuario_data.email)
            raise DatabaseException(f"Error de integridad: {str(e.orig)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al crear usuario: {str(e)}")
    
    def get_by_id(self, id_usuario: int, include_persona: bool = True) -> Usuario:
        """Obtener usuario por ID"""
        query = self.db.query(Usuario)
        
        if include_persona:
            query = query.options(joinedload(Usuario.persona))
        
        usuario = query.filter(Usuario.id_usuario == id_usuario).first()
        
        if not usuario:
            raise NotFoundException("Usuario", id_usuario)
        return usuario
    
    def get_by_username(self, username: str) -> Optional[Usuario]:
        """Obtener usuario por username"""
        return self.db.query(Usuario).filter(
            Usuario.username == username
        ).first()
    
    def get_by_email(self, email: str) -> Optional[Usuario]:
        """Obtener usuario por email"""
        return self.db.query(Usuario).filter(
            Usuario.email == email
        ).first()
    
    def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        estado: Optional[str] = None,
        include_persona: bool = True
    ) -> List[Usuario]:
        """Listar usuarios con filtros"""
        query = self.db.query(Usuario)
        
        if include_persona:
            query = query.options(joinedload(Usuario.persona))
        
        if estado:
            query = query.filter(Usuario.estado == estado)
        
        return query.offset(skip).limit(limit).all()
    
    def update(self, id_usuario: int, usuario_data: UsuarioUpdate) -> Usuario:
        """Actualizar un usuario"""
        try:
            usuario = self.get_by_id(id_usuario, include_persona=False)
            
            update_data = usuario_data.dict(exclude_unset=True)
            
            # Validar username único si se está actualizando
            if 'username' in update_data:
                existing = self.get_by_username(update_data['username'])
                if existing and existing.id_usuario != id_usuario:
                    raise AlreadyExistsException("Usuario", "username", update_data['username'])
            
            # Validar email único si se está actualizando
            if 'email' in update_data:
                existing = self.get_by_email(update_data['email'])
                if existing and existing.id_usuario != id_usuario:
                    raise AlreadyExistsException("Usuario", "email", update_data['email'])
            
            for field, value in update_data.items():
                setattr(usuario, field, value)
            
            self.db.commit()
            self.db.refresh(usuario)
            return usuario
            
        except IntegrityError as e:
            self.db.rollback()
            raise DatabaseException(f"Error de integridad: {str(e.orig)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar usuario: {str(e)}")
    
    def delete(self, id_usuario: int) -> dict:
        """Desactivar un usuario (soft delete)"""
        usuario = self.get_by_id(id_usuario, include_persona=False)
        
        try:
            usuario.estado = "inactivo"
            self.db.commit()
            return {
                "message": "Usuario desactivado exitosamente",
                "id_usuario": id_usuario
            }
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al desactivar usuario: {str(e)}")
    
    def register_login_attempt(
        self, 
        id_usuario: int, 
        success: bool, 
        ip_address: Optional[str] = None
    ) -> Usuario:
        """Registrar intento de login"""
        usuario = self.get_by_id(id_usuario, include_persona=False)
        
        if success:
            usuario.intentos_fallidos = 0
            usuario.ultimo_acceso = datetime.now()
            if ip_address:
                usuario.ultimo_ip = ip_address
        else:
            usuario.intentos_fallidos += 1
            usuario.fecha_ultimo_intento_fallido = datetime.now()
            
            # Bloquear después de 5 intentos fallidos
            if usuario.intentos_fallidos >= 5:
                usuario.estado = "bloqueado"
                usuario.fecha_bloqueo = datetime.now()
        
        self.db.commit()
        self.db.refresh(usuario)
        return usuario
    
    def update_password(self, id_usuario: int, hashed_password: str) -> Usuario:
        """Actualizar contraseña de usuario"""
        usuario = self.get_by_id(id_usuario, include_persona=False)
        usuario.password = hashed_password
        usuario.requiere_cambio_password = False
        
        self.db.commit()
        self.db.refresh(usuario)
        return usuario
    
    def count(self, estado: Optional[str] = None) -> int:
        """Contar usuarios"""
        query = self.db.query(Usuario)
        if estado:
            query = query.filter(Usuario.estado == estado)
        return query.count()