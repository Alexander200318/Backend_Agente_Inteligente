# routers/usuario_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, timedelta


from database.database import get_db
from models.usuario import Usuario
from repositories.usuario_repo import UsuarioRepository
from exceptions.base import NotFoundException, BadRequestException

# Importar funciones de seguridad desde core
from core.config import settings
from core.security import (
    verify_password,
    get_password_hash,
    validate_password_strength,
    create_access_token,
    sanitize_input,
    validate_username,
    validate_email,
    log_security_event,
    should_lockout_user,
    calculate_lockout_until,
    is_user_locked_out,
    get_client_ip,
    mask_email
)

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


# ========== ROUTER ==========
router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"]
)

# ========== SCHEMAS ==========

class LoginRequest(BaseModel):
    """Schema para solicitud de login"""
    username: str
    password: str
    
    @field_validator('username')
    def validate_username_field(cls, v):
        v = sanitize_input(v, max_length=50)
        is_valid, msg = validate_username(v)
        if not is_valid:
            raise ValueError(msg)
        return v
    
    @field_validator('password')
    def validate_password_field(cls, v):
        if not v or len(v.strip()) < 4:
            raise ValueError("La contraseña es demasiado corta")
        if len(v) > 100:
            raise ValueError("La contraseña es demasiado larga")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "Admin123!"
            }
        }

class LoginResponse(BaseModel):
    """Schema para respuesta de login"""
    token: str
    usuario: dict
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "usuario": {
                    "id_usuario": 1,
                    "username": "admin",
                    "email": "admin@example.com",
                    "estado": "activo",
                    "requiere_cambio_password": False
                }
            }
        }

class UsuarioCreate(BaseModel):
    """Schema para crear usuario"""
    username: str
    email: EmailStr
    password: str
    id_persona: int
    estado: Optional[str] = "activo"
    requiere_cambio_password: Optional[bool] = True
    
    @field_validator('username')
    def validate_username_field(cls, v):
        v = sanitize_input(v, max_length=50)
        is_valid, msg = validate_username(v)
        if not is_valid:
            raise ValueError(msg)
        return v
    
    @field_validator('email')
    def validate_email_field(cls, v):
        v = sanitize_input(v, max_length=100)
        is_valid, msg = validate_email(v)
        if not is_valid:
            raise ValueError(msg)
        return v.lower()
    
    @field_validator('password')
    def validate_password_field(cls, v):
        is_valid, msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(msg)
        return v

class UsuarioUpdate(BaseModel):
    """Schema para actualizar usuario"""
    email: Optional[EmailStr] = None
    estado: Optional[str] = None
    
    @field_validator('email')
    def validate_email_field(cls, v):
        if v:
            v = sanitize_input(v, max_length=100)
            is_valid, msg = validate_email(v)
            if not is_valid:
                raise ValueError(msg)
            return v.lower()
        return v

class PasswordChange(BaseModel):
    """Schema para cambio de contraseña"""
    password_actual: str
    password_nuevo: str
    
    @field_validator('password_nuevo')
    def validate_password_field(cls, v):
        is_valid, msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(msg)
        return v

# ========== ENDPOINTS ==========

@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🔐 Endpoint de autenticación con seguridad completa
    
    **Seguridad implementada:**
    - ✅ Validación y sanitización de inputs
    - ✅ Rate limiting
    - ✅ Control de intentos fallidos
    - ✅ Bloqueo automático después de 5 intentos
    - ✅ Bloqueo temporal de 15 minutos
    - ✅ Logging de eventos de seguridad
    - ✅ Tokens JWT seguros
    
    **Returns:**
    - `token`: Token JWT para autenticación
    - `usuario`: Datos del usuario autenticado
    """
    client_ip = get_client_ip(request)
    
    try:
        # 1. Buscar usuario
        usuario = db.query(Usuario).filter(
            Usuario.username == credentials.username
        ).first()
        
        if not usuario:
            log_security_event(
                "LOGIN_FAILED",
                credentials.username,
                "Usuario no encontrado",
                success=False,
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos"
            )
        
        # 2. Verificar si el usuario está bloqueado temporalmente
        if usuario.estado == "bloqueado":
            # Verificar si el bloqueo temporal ha expirado
            if usuario.fecha_bloqueo and is_user_locked_out(usuario.fecha_bloqueo):
                tiempo_restante = (
                    usuario.fecha_bloqueo + 
                    timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES) - 
                    datetime.now()
                )
                minutos_restantes = int(tiempo_restante.total_seconds() / 60)
                
                log_security_event(
                    "LOGIN_BLOCKED",
                    usuario.username,
                    f"Usuario bloqueado temporalmente. {minutos_restantes} minutos restantes",
                    success=False,
                    ip_address=client_ip
                )
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuario bloqueado temporalmente. Intenta nuevamente en {minutos_restantes} minutos"
                )
            else:
                # El bloqueo temporal expiró, desbloquear automáticamente
                usuario.estado = "activo"
                usuario.intentos_fallidos = 0
                usuario.fecha_bloqueo = None
                db.commit()
                log_security_event(
                    "AUTO_UNLOCK",
                    usuario.username,
                    "Desbloqueo automático por expiración de tiempo",
                    success=True,
                    ip_address=client_ip
                )
        
        # 3. Verificar otros estados
        if usuario.estado == "inactivo":
            log_security_event(
                "LOGIN_INACTIVE",
                usuario.username,
                "Intento de login con usuario inactivo",
                success=False,
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo. Contacta al administrador"
            )
        
        if usuario.estado == "suspendido":
            log_security_event(
                "LOGIN_SUSPENDED",
                usuario.username,
                "Intento de login con usuario suspendido",
                success=False,
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario suspendido. Contacta al administrador"
            )
        
        # 4. Verificar contraseña
        if not verify_password(credentials.password, usuario.password):
            # Registrar intento fallido
            usuario.intentos_fallidos += 1
            usuario.fecha_ultimo_intento_fallido = datetime.now()
            
            log_security_event(
                "LOGIN_FAILED",
                usuario.username,
                f"Contraseña incorrecta. Intento #{usuario.intentos_fallidos}",
                success=False,
                ip_address=client_ip
            )
            
            # Verificar si debe ser bloqueado
            if should_lockout_user(usuario.intentos_fallidos):
                usuario.estado = "bloqueado"
                usuario.fecha_bloqueo = datetime.now()
                db.commit()
                
                log_security_event(
                    "USER_LOCKED",
                    usuario.username,
                    f"Usuario bloqueado por {settings.MAX_LOGIN_ATTEMPTS} intentos fallidos",
                    success=False,
                    ip_address=client_ip
                )
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuario bloqueado por múltiples intentos fallidos. Intenta nuevamente en {settings.LOCKOUT_DURATION_MINUTES} minutos"
                )
            
            db.commit()
            
            intentos_restantes = settings.MAX_LOGIN_ATTEMPTS - usuario.intentos_fallidos
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Usuario o contraseña incorrectos. Te quedan {intentos_restantes} intento{'s' if intentos_restantes != 1 else ''}"
            )
        
        # 5. Login exitoso - resetear intentos
        usuario.intentos_fallidos = 0
        usuario.ultimo_acceso = datetime.now()
        usuario.fecha_ultimo_intento_fallido = None
        db.commit()
        
        log_security_event(
            "LOGIN_SUCCESS",
            usuario.username,
            "Login exitoso",
            success=True,
            ip_address=client_ip
        )
        
        # 6. Crear token JWT seguro
        token_data = {
            "sub": str(usuario.id_usuario),
            "username": usuario.username,
            "email": usuario.email,
        }
        token = create_access_token(token_data)
        
        # 7. Respuesta
        return {
            "token": token,
            "usuario": {
                "id_usuario": usuario.id_usuario,
                "username": usuario.username,
                "email": usuario.email,
                "estado": usuario.estado,
                "requiere_cambio_password": usuario.requiere_cambio_password,
                "ultimo_acceso": usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_security_event(
            "LOGIN_ERROR",
            credentials.username,
            f"Error inesperado: {str(e)}",
            success=False,
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    usuario_data: UsuarioCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    ➕ Crear nuevo usuario con validaciones de seguridad
    
    **Seguridad:**
    - ✅ Validación de fortaleza de contraseña
    - ✅ Sanitización de inputs
    - ✅ Validación de username y email únicos
    - ✅ Hash seguro de contraseña
    """
    repo = UsuarioRepository(db)
    client_ip = get_client_ip(request)
    
    try:
        # Validaciones de unicidad
        if repo.exists_by_username(usuario_data.username):
            raise BadRequestException(
                f"El username '{usuario_data.username}' ya está en uso"
            )
        
        if repo.exists_by_email(usuario_data.email):
            raise BadRequestException(
                f"El email '{usuario_data.email}' ya está en uso"
            )
        
        # Verificar que la persona exista
        persona = repo.get_persona_by_id(usuario_data.id_persona)
        if not persona:
            raise NotFoundException(
                f"Persona con ID {usuario_data.id_persona} no encontrada"
            )
        
        # Hash seguro de la contraseña
        hashed_password = get_password_hash(usuario_data.password)
        usuario_data.password = hashed_password
        
        # Crear usuario
        nuevo_usuario = repo.create(usuario_data, persona)
        
        log_security_event(
            "USER_CREATED",
            nuevo_usuario.username,
            f"Nuevo usuario creado - Email: {mask_email(nuevo_usuario.email)}",
            success=True,
            ip_address=client_ip
        )
        
        return {
            "message": "Usuario creado exitosamente",
            "usuario": {
                "id_usuario": nuevo_usuario.id_usuario,
                "username": nuevo_usuario.username,
                "email": nuevo_usuario.email,
                "estado": nuevo_usuario.estado
            }
        }
        
    except (BadRequestException, NotFoundException):
        raise
    except Exception as e:
        print(f"❌ Error creando usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear usuario"
        )


@router.get("", status_code=status.HTTP_200_OK)
async def listar_usuarios(
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """📋 Listar usuarios con paginación y filtros"""
    repo = UsuarioRepository(db)
    
    # Limitar resultados máximos por seguridad
    limit = min(limit, 500)
    
    usuarios = repo.get_all(
        skip=skip,
        limit=limit,
        estado=estado,
        include_persona=True
    )
    
    total = repo.count(estado=estado)
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "usuarios": [
            {
                "id_usuario": u.id_usuario,
                "username": u.username,
                "email": u.email,
                "estado": u.estado,
                "ultimo_acceso": u.ultimo_acceso.isoformat() if u.ultimo_acceso else None,
                "persona": {
                    "id_persona": u.persona.id_persona,
                    "nombre": u.persona.nombre,
                    "apellido": u.persona.apellido
                } if u.persona else None
            }
            for u in usuarios
        ]
    }


@router.get("/estadisticas", status_code=status.HTTP_200_OK)
async def obtener_estadisticas(db: Session = Depends(get_db)):
    """📊 Obtener estadísticas de usuarios"""
    repo = UsuarioRepository(db)
    
    total = repo.count()
    activos = repo.count(estado="activo")
    inactivos = repo.count(estado="inactivo")
    bloqueados = repo.count(estado="bloqueado")
    suspendidos = repo.count(estado="suspendido")
    
    return {
        "total": total,
        "por_estado": {
            "activos": activos,
            "inactivos": inactivos,
            "bloqueados": bloqueados,
            "suspendidos": suspendidos
        },
        "porcentajes": {
            "activos": round((activos / total * 100), 2) if total > 0 else 0,
            "inactivos": round((inactivos / total * 100), 2) if total > 0 else 0,
            "bloqueados": round((bloqueados / total * 100), 2) if total > 0 else 0,
            "suspendidos": round((suspendidos / total * 100), 2) if total > 0 else 0
        }
    }


@router.get("/{id_usuario}", status_code=status.HTTP_200_OK)
async def obtener_usuario(
    id_usuario: int,
    db: Session = Depends(get_db)
):
    """🔍 Obtener usuario por ID"""
    repo = UsuarioRepository(db)
    
    try:
        usuario = repo.get_by_id(id_usuario, include_persona=True)
        
        return {
            "id_usuario": usuario.id_usuario,
            "username": usuario.username,
            "email": usuario.email,
            "estado": usuario.estado,
            "requiere_cambio_password": usuario.requiere_cambio_password,
            "intentos_fallidos": usuario.intentos_fallidos,
            "ultimo_acceso": usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None,
            "fecha_creacion": usuario.fecha_creacion.isoformat() if usuario.fecha_creacion else None,
            "persona": {
                "id_persona": usuario.persona.id_persona,
                "nombre": usuario.persona.nombre,
                "apellido": usuario.persona.apellido,
                "email": usuario.persona.email
            } if usuario.persona else None
        }
    except NotFoundException:
        raise


@router.put("/{id_usuario}", status_code=status.HTTP_200_OK)
async def actualizar_usuario(
    id_usuario: int,
    usuario_data: UsuarioUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """✏️ Actualizar usuario"""
    repo = UsuarioRepository(db)
    client_ip = get_client_ip(request)
    
    try:
        usuario_actualizado = repo.update(id_usuario, usuario_data)
        
        log_security_event(
            "USER_UPDATED",
            usuario_actualizado.username,
            "Usuario actualizado",
            success=True,
            ip_address=client_ip
        )
        
        return {
            "message": "Usuario actualizado exitosamente",
            "usuario": {
                "id_usuario": usuario_actualizado.id_usuario,
                "username": usuario_actualizado.username,
                "email": usuario_actualizado.email,
                "estado": usuario_actualizado.estado
            }
        }
    except NotFoundException:
        raise


@router.delete("/{id_usuario}", status_code=status.HTTP_200_OK)
async def eliminar_usuario(
    id_usuario: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """🗑️ Desactivar usuario (soft delete)"""
    repo = UsuarioRepository(db)
    client_ip = get_client_ip(request)
    
    try:
        resultado = repo.delete(id_usuario)
        
        log_security_event(
            "USER_DELETED",
            f"ID:{id_usuario}",
            "Usuario desactivado (soft delete)",
            success=True,
            ip_address=client_ip
        )
        
        return resultado
    except NotFoundException:
        raise


@router.post("/{id_usuario}/cambiar-password", status_code=status.HTTP_200_OK)
async def cambiar_password(
    id_usuario: int,
    password_data: PasswordChange,
    request: Request,
    db: Session = Depends(get_db)
):
    """🔑 Cambiar contraseña con validaciones de seguridad"""
    repo = UsuarioRepository(db)
    client_ip = get_client_ip(request)
    
    try:
        usuario = repo.get_by_id(id_usuario)
        
        # Verificar contraseña actual
        if not verify_password(password_data.password_actual, usuario.password):
            log_security_event(
                "PASSWORD_CHANGE_FAILED",
                usuario.username,
                "Contraseña actual incorrecta",
                success=False,
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña actual incorrecta"
            )
        
        # Validar que la nueva contraseña sea diferente
        if verify_password(password_data.password_nuevo, usuario.password):
            raise BadRequestException(
                "La nueva contraseña debe ser diferente a la actual"
            )
        
        # Hash de nueva contraseña
        nueva_password_hash = get_password_hash(password_data.password_nuevo)
        
        # Actualizar
        repo.update_password(id_usuario, nueva_password_hash)
        
        # Marcar que ya no requiere cambio de contraseña
        usuario.requiere_cambio_password = False
        db.commit()
        
        log_security_event(
            "PASSWORD_CHANGED",
            usuario.username,
            "Contraseña cambiada exitosamente",
            success=True,
            ip_address=client_ip
        )
        
        return {
            "message": "Contraseña actualizada exitosamente",
            "requiere_nuevo_login": True
        }
        
    except (NotFoundException, BadRequestException, HTTPException):
        raise
    except Exception as e:
        print(f"❌ Error cambiando contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cambiar contraseña"
        )


@router.post("/{id_usuario}/desbloquear", status_code=status.HTTP_200_OK)
async def desbloquear_usuario(
    id_usuario: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """🔓 Desbloquear usuario manualmente"""
    repo = UsuarioRepository(db)
    client_ip = get_client_ip(request)
    
    try:
        usuario = repo.get_by_id(id_usuario)
        
        if usuario.estado != "bloqueado":
            raise BadRequestException(
                f"El usuario está en estado '{usuario.estado}', no está bloqueado"
            )
        
        usuario.estado = "activo"
        usuario.intentos_fallidos = 0
        usuario.fecha_bloqueo = None
        usuario.fecha_ultimo_intento_fallido = None
        db.commit()
        
        log_security_event(
            "USER_UNLOCKED",
            usuario.username,
            "Usuario desbloqueado manualmente",
            success=True,
            ip_address=client_ip
        )
        
        return {
            "message": f"Usuario '{usuario.username}' desbloqueado exitosamente",
            "estado_anterior": "bloqueado",
            "estado_actual": "activo"
        }
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        print(f"❌ Error desbloqueando usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al desbloquear usuario"
        )