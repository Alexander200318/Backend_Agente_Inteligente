from sqlalchemy.orm import Session
from models.usuario import Usuario
from models.persona import Persona
from typing import Optional, List
from datetime import datetime
from exceptions.base import NotFoundException

class UsuarioRepository:
    """Repositorio para operaciones de base de datos de Usuario"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== MÉTODOS EXISTENTES (los que ya tienes) ==========
    
    def get_by_id(self, id_usuario: int, include_persona: bool = False) -> Usuario:
        """Obtener usuario por ID"""
        query = self.db.query(Usuario)
        if include_persona:
            from sqlalchemy.orm import joinedload
            query = query.options(joinedload(Usuario.persona))
        
        usuario = query.filter(Usuario.id_usuario == id_usuario).first()
        if not usuario:
            raise NotFoundException(f"Usuario con ID {id_usuario} no encontrado")
        return usuario
    
    def get_by_username(self, username: str) -> Optional[Usuario]:
        """Obtener usuario por username"""
        return self.db.query(Usuario).filter(Usuario.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[Usuario]:
        """Obtener usuario por email"""
        return self.db.query(Usuario).filter(Usuario.email == email).first()
    
    def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        estado: Optional[str] = None,
        include_persona: bool = False
    ) -> List[Usuario]:
        """Listar usuarios con filtros"""
        query = self.db.query(Usuario)
        
        if include_persona:
            from sqlalchemy.orm import joinedload
            query = query.options(joinedload(Usuario.persona))
        
        if estado:
            query = query.filter(Usuario.estado == estado)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, estado: Optional[str] = None) -> int:
        """Contar usuarios"""
        query = self.db.query(Usuario)
        if estado:
            query = query.filter(Usuario.estado == estado)
        return query.count()
    
    def create(self, usuario_data, persona) -> Usuario:
        """Crear nuevo usuario"""
        nuevo_usuario = Usuario(
            id_persona=persona.id_persona,
            username=usuario_data.username,
            email=usuario_data.email,
            password=usuario_data.password,
            estado=usuario_data.estado if hasattr(usuario_data, 'estado') else "activo",
            requiere_cambio_password=usuario_data.requiere_cambio_password if hasattr(usuario_data, 'requiere_cambio_password') else True
        )
        
        self.db.add(nuevo_usuario)
        self.db.commit()
        self.db.refresh(nuevo_usuario)
        return nuevo_usuario
    
    def update(self, id_usuario: int, usuario_data) -> Usuario:
        """Actualizar usuario"""
        usuario = self.get_by_id(id_usuario)
        
        for key, value in usuario_data.dict(exclude_unset=True).items():
            if hasattr(usuario, key) and value is not None:
                setattr(usuario, key, value)
        
        usuario.fecha_actualizacion = datetime.now()
        self.db.commit()
        self.db.refresh(usuario)
        return usuario
    
    def delete(self, id_usuario: int) -> dict:
        """Desactivar usuario (soft delete)"""
        usuario = self.get_by_id(id_usuario)
        usuario.estado = "inactivo"
        usuario.fecha_actualizacion = datetime.now()
        
        self.db.commit()
        return {"message": f"Usuario {usuario.username} desactivado exitosamente"}
    
    def update_password(self, id_usuario: int, new_password: str):
        """Actualizar contraseña"""
        usuario = self.get_by_id(id_usuario)
        usuario.password = new_password
        usuario.requiere_cambio_password = False
        usuario.fecha_actualizacion = datetime.now()
        
        self.db.commit()
    
    def register_login_attempt(
        self, 
        id_usuario: int, 
        success: bool,
        ip_address: Optional[str] = None
    ):
        """Registrar intento de login"""
        usuario = self.get_by_id(id_usuario)
        
        if success:
            # Login exitoso
            usuario.intentos_fallidos = 0
            usuario.ultimo_acceso = datetime.now()
            usuario.ultimo_ip = ip_address
            usuario.fecha_ultimo_intento_fallido = None
        else:
            # Login fallido
            usuario.intentos_fallidos += 1
            usuario.fecha_ultimo_intento_fallido = datetime.now()
            
            # Bloquear si supera 5 intentos
            if usuario.intentos_fallidos >= 5:
                usuario.estado = "bloqueado"
                usuario.fecha_bloqueo = datetime.now()
        
        self.db.commit()
    
    # ========== NUEVOS MÉTODOS PARA VINCULAR PERSONA ==========
    
    def get_persona_by_id(self, id_persona: int) -> Optional[Persona]:
        """Obtener persona por ID"""
        return self.db.query(Persona).filter(Persona.id_persona == id_persona).first()
    
    def exists_by_persona_id(self, id_persona: int) -> bool:
        """Verificar si existe usuario para una persona"""
        return self.db.query(Usuario).filter(Usuario.id_persona == id_persona).first() is not None
    
    def exists_by_username(self, username: str) -> bool:
        """Verificar si existe un username"""
        return self.db.query(Usuario).filter(Usuario.username == username).first() is not None
    
    def exists_by_email(self, email: str) -> bool:
        """Verificar si existe un email"""
        return self.db.query(Usuario).filter(Usuario.email == email).first() is not None
    
    def add(self, usuario: Usuario):
        """Agregar usuario a la sesión (sin commit automático)"""
        self.db.add(usuario)