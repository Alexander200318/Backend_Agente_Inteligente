from sqlalchemy.orm import Session
from typing import List, Optional
from passlib.context import CryptContext
from datetime import datetime, timedelta
from repositories.usuario_repo import UsuarioRepository
from repositories.persona_repo import PersonaRepository
from schemas.usuario_schemas import (
    UsuarioCreate, 
    UsuarioUpdate, 
    UsuarioLogin,
    CambioPasswordRequest
)
from models.usuario import Usuario
from exceptions.base import (
    ValidationException, 
    UnauthorizedException,
)

# Configuración de hash de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UsuarioService:
    """Servicio con lógica de negocio para Usuario"""
    
    def __init__(self, db: Session):
        self.db = db
        self.usuario_repo = UsuarioRepository(db)
        self.persona_repo = PersonaRepository(db)
    
    def _hash_password(self, password: str) -> str:
        """Hashear contraseña"""
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar contraseña"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def crear_usuario(self, usuario_data: UsuarioCreate, creado_por_id: Optional[int] = None) -> Usuario:
        """
        Crear usuario con validaciones de negocio.
        - Crea primero la persona
        - Luego crea el usuario vinculado
        - Hashea la contraseña
        """
        
        # Validación de negocio: edad mínima
        if usuario_data.persona.fecha_nacimiento:
            edad = (datetime.now().date() - usuario_data.persona.fecha_nacimiento).days // 365
            if edad < 18:
                raise ValidationException("El usuario debe ser mayor de 18 años")
        
        # Validación: tipo de persona no puede ser 'externo' para usuarios del sistema
        if usuario_data.persona.tipo_persona == "externo":
            raise ValidationException("Los usuarios externos no pueden acceder al sistema")
        
        # 1. Crear la persona
        persona = self.persona_repo.create(usuario_data.persona)
        
        try:
            # 2. Hashear contraseña
            usuario_data.password = self._hash_password(usuario_data.password)
            
            # 3. Crear usuario
            usuario = self.usuario_repo.create(usuario_data, persona)
            
            # 4. Asignar creador si existe
            if creado_por_id:
                usuario.creado_por = creado_por_id
                self.db.commit()
                self.db.refresh(usuario)
            
            return usuario
            
        except Exception as e:
            # Si falla la creación del usuario, eliminar la persona
            self.persona_repo.delete(persona.id_persona)
            raise e
    
    def obtener_usuario(self, id_usuario: int) -> Usuario:
        """Obtener usuario con su persona"""
        return self.usuario_repo.get_by_id(id_usuario, include_persona=True)
    
    def listar_usuarios(
        self, 
        skip: int = 0, 
        limit: int = 100,
        estado: Optional[str] = None
    ) -> List[Usuario]:
        """Listar usuarios con filtros"""
        # Validación: límite máximo
        if limit > 500:
            raise ValidationException("El límite máximo es 500 registros")
        
        return self.usuario_repo.get_all(skip, limit, estado, include_persona=True)
    
    def actualizar_usuario(
        self, 
        id_usuario: int, 
        usuario_data: UsuarioUpdate,
        actualizado_por_id: Optional[int] = None
    ) -> Usuario:
        """Actualizar usuario con validaciones"""
        
        # Si se actualiza contraseña, hashearla
        if usuario_data.password:
            usuario_data.password = self._hash_password(usuario_data.password)
        
        usuario = self.usuario_repo.update(id_usuario, usuario_data)
        
        return usuario
    
    def eliminar_usuario(self, id_usuario: int, eliminado_por_id: Optional[int] = None) -> dict:
        """Desactivar usuario (soft delete)"""
        
        # Validación: no se puede eliminar a sí mismo
        if id_usuario == eliminado_por_id:
            raise ValidationException("No puedes desactivar tu propia cuenta")
        
        return self.usuario_repo.delete(id_usuario)
    
    def autenticar_usuario(
        self, 
        login_data: UsuarioLogin,
        ip_address: Optional[str] = None
    ) -> Usuario:
        """
        Autenticar usuario con validaciones de seguridad
        - Verifica estado de cuenta
        - Valida contraseña
        - Registra intentos
        """
        
        # Buscar usuario
        usuario = self.usuario_repo.get_by_username(login_data.username)
        
        if not usuario:
            raise UnauthorizedException("Credenciales inválidas")
        
        # Validar estado de cuenta
        if usuario.estado == "bloqueado":
            raise UnauthorizedException(
                f"Cuenta bloqueada. Contacte al administrador. "
                f"Bloqueada desde: {usuario.fecha_bloqueo}"
            )
        
        if usuario.estado == "inactivo":
            raise UnauthorizedException("Cuenta inactiva")
        
        if usuario.estado == "suspendido":
            raise UnauthorizedException("Cuenta suspendida temporalmente")
        
        # Verificar contraseña
        if not self._verify_password(login_data.password, usuario.password):
            # Registrar intento fallido
            self.usuario_repo.register_login_attempt(
                usuario.id_usuario, 
                success=False,
                ip_address=ip_address
            )
            raise UnauthorizedException("Credenciales inválidas")
        
        # Registrar login exitoso
        self.usuario_repo.register_login_attempt(
            usuario.id_usuario,
            success=True,
            ip_address=ip_address
        )
        
        return usuario
    
    def cambiar_password(
        self, 
        id_usuario: int, 
        cambio_data: CambioPasswordRequest
    ) -> dict:
        """Cambiar contraseña del usuario"""
        
        usuario = self.usuario_repo.get_by_id(id_usuario, include_persona=False)
        
        # Verificar contraseña actual
        if not self._verify_password(cambio_data.password_actual, usuario.password):
            raise ValidationException("La contraseña actual es incorrecta")
        
        # Validar que la nueva sea diferente
        if self._verify_password(cambio_data.password_nueva, usuario.password):
            raise ValidationException("La nueva contraseña debe ser diferente a la actual")
        
        # Actualizar contraseña
        hashed_nueva = self._hash_password(cambio_data.password_nueva)
        self.usuario_repo.update_password(id_usuario, hashed_nueva)
        
        return {"message": "Contraseña actualizada exitosamente"}
    
    def desbloquear_usuario(self, id_usuario: int, desbloqueado_por_id: int) -> Usuario:
        """Desbloquear cuenta de usuario"""
        
        usuario = self.usuario_repo.get_by_id(id_usuario, include_persona=False)
        
        if usuario.estado != "bloqueado":
            raise ValidationException("El usuario no está bloqueado")
        
        # Resetear intentos y desbloquear
        usuario.estado = "activo"
        usuario.intentos_fallidos = 0
        usuario.fecha_bloqueo = None
        usuario.requiere_cambio_password = True  # Forzar cambio de contraseña
        
        self.db.commit()
        self.db.refresh(usuario)
        
        return usuario
    
    def obtener_estadisticas(self) -> dict:
        """Obtener estadísticas generales de usuarios"""
        return {
            "total_usuarios": self.usuario_repo.count(),
            "usuarios_activos": self.usuario_repo.count(estado="activo"),
            "usuarios_inactivos": self.usuario_repo.count(estado="inactivo"),
            "usuarios_bloqueados": self.usuario_repo.count(estado="bloqueado"),
            "usuarios_suspendidos": self.usuario_repo.count(estado="suspendido")
        }
    
    
    def crear_usuario_persona_existente(
        self,
        id_persona: int,
        username: str,
        email: str,
        password: str,
        requiere_cambio_password: bool = True
    ) -> Usuario:
        """Crear usuario para persona ya registrada"""
        
        # Verificar que la persona existe
        persona = self.usuario_repo.get_persona_by_id(id_persona)
        if not persona:
            raise ValidationException("La persona no existe")
        
        # Verificar que la persona no tenga usuario
        if self.usuario_repo.exists_by_persona_id(id_persona):
            raise ValidationException("La persona ya tiene un usuario asociado")
        
        # Verificar unicidad de username y email
        if self.usuario_repo.exists_by_username(username):
            raise ValidationException("El nombre de usuario ya está en uso")
        
        if self.usuario_repo.exists_by_email(email):
            raise ValidationException("El email ya está en uso")
        
        # Hashear contraseña
        hashed_password = self._hash_password(password)
        
        # Crear usuario
        usuario = Usuario(
            id_persona=id_persona,
            username=username,
            email=email,
            password=hashed_password,
            estado="activo",
            requiere_cambio_password=requiere_cambio_password
        )
        
        self.usuario_repo.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        
        return usuario
    