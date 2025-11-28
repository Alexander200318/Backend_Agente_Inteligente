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

# routers/usuario_router.py - LOGIN CON ROLES COMPLETO
# Este endpoint maneja TODOS los roles correctamente

@limiter.limit(f"{settings.RATE_LIMIT_LOGIN_PER_MINUTE}/minute")
@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🔐 LOGIN UNIVERSAL CON SISTEMA DE ROLES
    
    Funciona para:
    - ✅ Super Administrador (id_rol = 1)
    - ✅ Administrador (id_rol = 2)
    - ✅ Funcionario (id_rol = 3)
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
        
        # ✅ CORRECCIÓN: Inicializar intentos_fallidos si es None
        if usuario.intentos_fallidos is None:
            usuario.intentos_fallidos = 0
        
        # 2. Verificar estado del usuario
        if usuario.estado == "bloqueado":
            if usuario.fecha_bloqueo and is_user_locked_out(usuario.fecha_bloqueo):
                tiempo_restante = (
                    usuario.fecha_bloqueo + 
                    timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES) - 
                    datetime.now()
                )
                minutos_restantes = int(tiempo_restante.total_seconds() / 60)
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuario bloqueado. Intenta en {minutos_restantes} minutos"
                )
            else:
                # Desbloqueo automático
                usuario.estado = "activo"
                usuario.intentos_fallidos = 0
                usuario.fecha_bloqueo = None
                db.commit()
        
        if usuario.estado in ["inactivo", "suspendido"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Usuario {usuario.estado}. Contacta al administrador"
            )
        
        # 3. Verificar contraseña
        if not verify_password(credentials.password, usuario.password):
            usuario.intentos_fallidos += 1
            usuario.fecha_ultimo_intento_fallido = datetime.now()
            
            if should_lockout_user(usuario.intentos_fallidos):
                usuario.estado = "bloqueado"
                usuario.fecha_bloqueo = datetime.now()
                db.commit()
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Usuario bloqueado por intentos fallidos"
                )
            
            db.commit()
            intentos_restantes = settings.MAX_LOGIN_ATTEMPTS - usuario.intentos_fallidos
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Credenciales incorrectas. {intentos_restantes} intentos restantes"
            )
        
            # ========================================
        # 🎭 SISTEMA DE ROLES - PARTE CRÍTICA
        # ========================================

        # 4. Obtener TODOS los roles del usuario
        from models.usuario_rol import UsuarioRol
        from models.rol import Rol

        # ✅ CORRECCIÓN: Quitar el filtro de estado
        roles_usuario = db.query(UsuarioRol).filter(
            UsuarioRol.id_usuario == usuario.id_usuario,
            UsuarioRol.activo == 1  # ✅ Filtrar por activo = 1
        ).join(Rol).all()

        if not roles_usuario or len(roles_usuario) == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sin roles asignados. Contacta al administrador"
            )

        # 5. Determinar ROL PRINCIPAL (mayor jerarquía = nivel más bajo)
        # Super Admin (nivel 1) > Admin (nivel 2) > Funcionario (nivel 3)
        rol_principal = min(roles_usuario, key=lambda r: r.rol.nivel_jerarquia)

        # 6. Construir información de roles
        roles_info = []
        for ur in roles_usuario:
            roles_info.append({
                "id_rol": ur.id_rol,
                "nombre_rol": ur.rol.nombre_rol,
                "nivel_jerarquia": ur.rol.nivel_jerarquia,
                "descripcion": ur.rol.descripcion
            })

        # 7. Obtener TODOS los permisos del rol principal
        permisos = {
            # Permisos de gestión de usuarios
            "puede_ver_usuarios": getattr(rol_principal.rol, 'puede_ver_usuarios', False),
            "puede_crear_usuarios": getattr(rol_principal.rol, 'puede_crear_usuarios', False),
            "puede_editar_usuarios": getattr(rol_principal.rol, 'puede_editar_usuarios', False),
            "puede_eliminar_usuarios": getattr(rol_principal.rol, 'puede_eliminar_usuarios', False),
            
            # Permisos de gestión de roles
            "puede_ver_roles": getattr(rol_principal.rol, 'puede_ver_roles', False),
            "puede_crear_roles": getattr(rol_principal.rol, 'puede_crear_roles', False),
            "puede_editar_roles": getattr(rol_principal.rol, 'puede_editar_roles', False),
            "puede_eliminar_roles": getattr(rol_principal.rol, 'puede_eliminar_roles', False),
            "puede_asignar_roles": getattr(rol_principal.rol, 'puede_asignar_roles', False),
            
            # Permisos de gestión de agentes
            "puede_ver_agentes": getattr(rol_principal.rol, 'puede_ver_agentes', False),
            "puede_crear_agentes": getattr(rol_principal.rol, 'puede_crear_agentes', False),
            "puede_editar_agentes": getattr(rol_principal.rol, 'puede_editar_agentes', False),
            "puede_eliminar_agentes": getattr(rol_principal.rol, 'puede_eliminar_agentes', False),
            
            # Permisos de conversaciones
            "puede_ver_conversaciones": getattr(rol_principal.rol, 'puede_ver_conversaciones', False),
            "puede_ver_todas_conversaciones": getattr(rol_principal.rol, 'puede_ver_todas_conversaciones', False),
            "puede_exportar_conversaciones": getattr(rol_principal.rol, 'puede_exportar_conversaciones', False),
            
            # Permisos de departamentos
            "puede_ver_departamentos": getattr(rol_principal.rol, 'puede_ver_departamentos', False),
            "puede_crear_departamentos": getattr(rol_principal.rol, 'puede_crear_departamentos', False),
            "puede_editar_departamentos": getattr(rol_principal.rol, 'puede_editar_departamentos', False),
            "puede_eliminar_departamentos": getattr(rol_principal.rol, 'puede_eliminar_departamentos', False),
            
            # Permisos de contenido
            "puede_ver_contenido": getattr(rol_principal.rol, 'puede_ver_contenido', False),
            "puede_crear_contenido": getattr(rol_principal.rol, 'puede_crear_contenido', False),
            "puede_editar_contenido": getattr(rol_principal.rol, 'puede_editar_contenido', False),
            "puede_eliminar_contenido": getattr(rol_principal.rol, 'puede_eliminar_contenido', False),
            
            # Permisos de sistema
            "puede_ver_logs": getattr(rol_principal.rol, 'puede_ver_logs', False),
            "puede_configurar_sistema": getattr(rol_principal.rol, 'puede_configurar_sistema', False),
            "puede_gestionar_api_keys": getattr(rol_principal.rol, 'puede_gestionar_api_keys', False),
            "puede_exportar_datos": getattr(rol_principal.rol, 'puede_exportar_datos', False),
            "puede_ver_estadisticas": getattr(rol_principal.rol, 'puede_ver_estadisticas', False)
        }

        # 8. Login exitoso - actualizar usuario
        usuario.intentos_fallidos = 0
        usuario.ultimo_acceso = datetime.now()
        usuario.fecha_ultimo_intento_fallido = None
        db.commit()

        log_security_event(
            "LOGIN_SUCCESS",
            usuario.username,
            f"Login exitoso - Rol: {rol_principal.rol.nombre_rol}",
            success=True,
            ip_address=client_ip
        )

        # 9. Crear token JWT con información del rol
        token_data = {
            "sub": str(usuario.id_usuario),
            "username": usuario.username,
            "email": usuario.email,
            "id_rol": rol_principal.id_rol,
            "nombre_rol": rol_principal.rol.nombre_rol,
            "nivel_jerarquia": rol_principal.rol.nivel_jerarquia
        }
        token = create_access_token(token_data)

        # 10. Respuesta COMPLETA con roles y permisos
        return {
            "token": token,
            "usuario": {
                "id_usuario": usuario.id_usuario,
                "username": usuario.username,
                "email": usuario.email,
                "estado": usuario.estado,
                "requiere_cambio_password": usuario.requiere_cambio_password,
                "ultimo_acceso": usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None,
                
                # 🎭 INFORMACIÓN DE ROLES
                "rol_principal": {
                    "id_rol": rol_principal.id_rol,
                    "nombre_rol": rol_principal.rol.nombre_rol,
                    "nivel_jerarquia": rol_principal.rol.nivel_jerarquia,
                    "descripcion": rol_principal.rol.descripcion
                },
                
                # Todos los roles del usuario
                "roles": roles_info,
                
                # 🔑 PERMISOS COMPLETOS
                "permisos": permisos
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
        print(f"❌ ERROR DETALLADO: {e}")
        import traceback
        traceback.print_exc()
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
    """➕ Crear nuevo usuario con validaciones de seguridad"""
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