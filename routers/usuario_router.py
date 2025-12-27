# routers/usuario_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, Field
from datetime import datetime, timedelta

from database.database import get_db
from models.usuario import Usuario
from repositories.usuario_repo import UsuarioRepository
from exceptions.base import NotFoundException, BadRequestException
from schemas.usuario_departamento_schemas import (
    CambiarDepartamentoRequest, 
    CambiarDepartamentoResponse
)


from schemas.usuario_completo_schemas import UsuarioCompletoCreate, UsuarioCompletoResponse

from models.persona import Persona
from models.usuario_rol import UsuarioRol
from models.rol import Rol
from models.departamento import Departamento
from repositories.persona_repo import PersonaRepository
from repositories.usuario_rol_repo import UsuarioRolRepository
from sqlalchemy.exc import SQLAlchemyError, IntegrityError




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
    username: Optional[str] = Field(None, min_length=4, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    estado: Optional[str] = None
    
    @field_validator('username')
    def validate_username_field(cls, v):
        if v:
            v = sanitize_input(v, max_length=50)
            is_valid, msg = validate_username(v)
            if not is_valid:
                raise ValueError(msg)
            return v
        return v
    
    @field_validator('email')
    def validate_email_field(cls, v):
        if v:
            v = sanitize_input(v, max_length=100)
            is_valid, msg = validate_email(v)
            if not is_valid:
                raise ValueError(msg)
            return v.lower()
        return v
    
    @field_validator('password')
    def validate_password_field(cls, v):
        if v:
            is_valid, msg = validate_password_strength(v)
            if not is_valid:
                raise ValueError(msg)
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
        # 1. Buscar usuario con su persona
        from sqlalchemy.orm import joinedload

        usuario = db.query(Usuario).options(
            joinedload(Usuario.persona)
        ).filter(
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
                
                # 🔥 NUEVO: Incluir id_departamento desde la persona
                "id_departamento": usuario.persona.id_departamento if usuario.persona else None,
                "nombre_completo": f"{usuario.persona.nombre} {usuario.persona.apellido}" if usuario.persona else None,
                
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
    


# Agregar este endpoint después de la función login
@router.post("/crear-completo", response_model=UsuarioCompletoResponse, status_code=status.HTTP_201_CREATED)
async def crear_usuario_completo(
    usuario_data: UsuarioCompletoCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🔒 TRANSACCIÓN ATÓMICA: Crear Persona + Usuario + Roles
    
    Si falla cualquier paso, se revierte TODA la operación.
    Solo si todo es exitoso se confirma la transacción.
    """
    client_ip = get_client_ip(request)
    
    try:
        # ========== VALIDACIONES PREVIAS (sin modificar DB) ==========
        
        # 1. Validar que la cédula no exista
        persona_existente = db.query(Persona).filter(
            Persona.cedula == usuario_data.persona.cedula
        ).first()
        
        if persona_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una persona con la cédula {usuario_data.persona.cedula}"
            )
        
        # 2. Validar que el username no exista
        usuario_existente = db.query(Usuario).filter(
            Usuario.username == usuario_data.username
        ).first()
        
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El username '{usuario_data.username}' ya está en uso"
            )
        
        # 3. Validar que el email no exista
        email_existente = db.query(Usuario).filter(
            Usuario.email == usuario_data.email
        ).first()
        
        if email_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El email '{usuario_data.email}' ya está en uso"
            )
        
        # 4. Validar que todos los roles existan
        for id_rol in usuario_data.roles:
            rol = db.query(Rol).filter(Rol.id_rol == id_rol).first()
            if not rol:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El rol con ID {id_rol} no existe"
                )
        
        # ========== INICIO DE TRANSACCIÓN ATÓMICA ==========
        
        # PASO 1: Crear Persona
        nueva_persona = Persona(
            cedula=usuario_data.persona.cedula,
            nombre=usuario_data.persona.nombre,
            apellido=usuario_data.persona.apellido,
            fecha_nacimiento=usuario_data.persona.fecha_nacimiento,
            genero=usuario_data.persona.genero,
            telefono=usuario_data.persona.telefono,
            celular=usuario_data.persona.celular,
            email_personal=usuario_data.persona.email_personal,
            direccion=usuario_data.persona.direccion,
            ciudad=usuario_data.persona.ciudad,
            provincia=usuario_data.persona.provincia,
            tipo_persona=usuario_data.persona.tipo_persona,
            id_departamento=usuario_data.persona.id_departamento,
            cargo=usuario_data.persona.cargo,
            fecha_ingreso_institucion=usuario_data.persona.fecha_ingreso_institucion,
            contacto_emergencia_nombre=usuario_data.persona.contacto_emergencia_nombre,
            contacto_emergencia_telefono=usuario_data.persona.contacto_emergencia_telefono,
            contacto_emergencia_relacion=usuario_data.persona.contacto_emergencia_relacion,
            foto_perfil=usuario_data.persona.foto_perfil,
            estado="activo",
            fecha_registro=datetime.now()
        )
        
        db.add(nueva_persona)
        db.flush()  # Obtener id_persona sin hacer commit
        
        # PASO 2: Crear Usuario
        password_hash = get_password_hash(usuario_data.password)
        
        nuevo_usuario = Usuario(
            username=usuario_data.username,
            email=usuario_data.email,
            password=password_hash,
            estado=usuario_data.estado,
            id_persona=nueva_persona.id_persona,
            creado_por=usuario_data.creado_por,
            requiere_cambio_password=True,
            intentos_fallidos=0,
            fecha_creacion=datetime.now()
        )
        
        db.add(nuevo_usuario)
        db.flush()  # Obtener id_usuario sin hacer commit
        
        # PASO 3: Asignar Roles
        roles_asignados = []
        for id_rol in usuario_data.roles:
            usuario_rol = UsuarioRol(
                id_usuario=nuevo_usuario.id_usuario,
                id_rol=id_rol,
                fecha_asignacion=datetime.now(),
                activo=True
            )
            db.add(usuario_rol)
            db.flush()
            
            # Obtener info del rol para la respuesta
            rol_info = db.query(Rol).filter(Rol.id_rol == id_rol).first()
            roles_asignados.append({
                "id_rol": id_rol,
                "nombre_rol": rol_info.nombre_rol,
                "nivel_jerarquia": rol_info.nivel_jerarquia,
                "fecha_asignacion": usuario_rol.fecha_asignacion.isoformat()
            })
        
        # ========== COMMIT DE LA TRANSACCIÓN ==========
        # Si llegamos aquí, TODO fue exitoso
        db.commit()
        
        # Refrescar objetos
        db.refresh(nuevo_usuario)
        db.refresh(nueva_persona)
        
        log_security_event(
            "USER_CREATED_COMPLETE",
            nuevo_usuario.username,
            f"Usuario completo creado con {len(roles_asignados)} roles",
            success=True,
            ip_address=client_ip
        )
        
        # Respuesta exitosa
        return {
            "message": "Usuario creado exitosamente",
            "usuario": {
                "id_usuario": nuevo_usuario.id_usuario,
                "username": nuevo_usuario.username,
                "email": nuevo_usuario.email,
                "estado": nuevo_usuario.estado,
                "id_persona": nuevo_usuario.id_persona
            },
            "persona": {
                "id_persona": nueva_persona.id_persona,
                "cedula": nueva_persona.cedula,
                "nombre": nueva_persona.nombre,
                "apellido": nueva_persona.apellido,
                "tipo_persona": nueva_persona.tipo_persona
            },
            "roles_asignados": roles_asignados
        }
        
    except HTTPException:
        # Re-lanzar excepciones HTTP (validaciones)
        db.rollback()
        raise
        
    except IntegrityError as e:
        # Error de integridad de base de datos (claves duplicadas, etc.)
        db.rollback()
        
        error_msg = str(e.orig)
        if "Duplicate entry" in error_msg or "UNIQUE constraint" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un registro con estos datos"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de integridad en la base de datos"
        )
        
    except SQLAlchemyError as e:
        # Error de base de datos - ROLLBACK automático
        db.rollback()
        
        log_security_event(
            "USER_CREATION_FAILED",
            usuario_data.username,
            f"Error en base de datos: {str(e)}",
            success=False,
            ip_address=client_ip
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en la base de datos. La operación fue revertida"
        )
        
    except Exception as e:
        # Cualquier otro error - ROLLBACK
        db.rollback()
        
        log_security_event(
            "USER_CREATION_ERROR",
            usuario_data.username,
            f"Error inesperado: {str(e)}",
            success=False,
            ip_address=client_ip
        )
        
        print(f"❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado. La operación fue revertida completamente"
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
        # ✅ Validar que username no esté en uso por otro usuario
        if usuario_data.username:
            usuario_existente = db.query(Usuario).filter(
                Usuario.username == usuario_data.username,
                Usuario.id_usuario != id_usuario
            ).first()
            
            if usuario_existente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El username '{usuario_data.username}' ya está en uso"
                )

        # ✅ Validar que email no esté en uso por otro usuario
        if usuario_data.email:
            email_existente = db.query(Usuario).filter(
                Usuario.email == usuario_data.email,
                Usuario.id_usuario != id_usuario
            ).first()
            
            if email_existente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El email '{usuario_data.email}' ya está en uso"
                )

        # ✅ Si hay password, hashearla
        if usuario_data.password:
            usuario_data.password = get_password_hash(usuario_data.password)

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
                "estado": usuario_actualizado.estado,
                "fecha_actualizacion": usuario_actualizado.fecha_actualizacion
            }
        }
    except NotFoundException:
        raise
    except Exception as e:
        db.rollback()  # ✅ AGREGAR: Rollback explícito
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar usuario"
        )





@router.delete("/{id_usuario}", status_code=status.HTTP_200_OK)
async def eliminar_usuario(
    id_usuario: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🗑️ Eliminado lógico: Cambia el estado del usuario y persona a 'inactivo'
    
    - Marca el usuario como inactivo en lugar de eliminarlo físicamente
    - También marca la persona asociada como inactiva
    - No permite eliminar el propio usuario (auto-eliminación)
    - Mantiene todos los registros en la base de datos
    """
    client_ip = get_client_ip(request)
    
    try:
        # 1. Buscar el usuario con su persona
        from sqlalchemy.orm import joinedload
        
        usuario = db.query(Usuario).options(
            joinedload(Usuario.persona)
        ).filter(Usuario.id_usuario == id_usuario).first()
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {id_usuario} no encontrado"
            )
        
        # 2. Verificar si ya está inactivo
        if usuario.estado == "inactivo":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya está inactivo"
            )
        
        # 3. Guardar información para el log
        nombre_completo = "Sin nombre"
        if usuario.persona:
            nombre_completo = f"{usuario.persona.nombre} {usuario.persona.apellido}"
        
        # 4. Cambiar estado del usuario a inactivo
        usuario.estado = "inactivo"
        usuario.fecha_actualizacion = datetime.now()
        
        # 5. Cambiar estado de la persona asociada a inactivo
        if usuario.persona:
            usuario.persona.estado = "inactivo"
            usuario.persona.fecha_actualizacion = datetime.now()
        
        # 6. Commit de la transacción
        db.commit()
        
        # 7. Log de seguridad
        log_security_event(
            "USER_DELETED_LOGICAL",
            usuario.username,
            f"Usuario eliminado lógicamente (inactivo) - Persona: {nombre_completo}",
            success=True,
            ip_address=client_ip
        )
        
        return {
            "message": "Usuario eliminado correctamente (eliminado lógico)",
            "id_usuario": id_usuario,
            "username": usuario.username,
            "estado_anterior": "activo",
            "estado_actual": "inactivo",
            "persona_actualizada": True if usuario.persona else False,
            "fecha_eliminacion": datetime.now().isoformat()
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        
        log_security_event(
            "USER_DELETE_ERROR",
            f"ID:{id_usuario}",
            f"Error al eliminar usuario: {str(e)}",
            success=False,
            ip_address=client_ip
        )
        
        print(f"❌ Error eliminando usuario: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar usuario"
        )
        
@router.patch("/{id_usuario}/reactivar", status_code=status.HTTP_200_OK)
async def reactivar_usuario(
    id_usuario: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🔄 Reactivar un usuario inactivo
    
    - Cambia el estado del usuario y persona de 'inactivo' a 'activo'
    - Solo funciona con usuarios en estado inactivo
    """
    client_ip = get_client_ip(request)
    
    try:
        # 1. Buscar el usuario con su persona
        from sqlalchemy.orm import joinedload
        
        usuario = db.query(Usuario).options(
            joinedload(Usuario.persona)
        ).filter(Usuario.id_usuario == id_usuario).first()
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {id_usuario} no encontrado"
            )
        
        # 2. Verificar que esté inactivo
        if usuario.estado != "inactivo":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario está en estado '{usuario.estado}', no puede ser reactivado"
            )
        
        # 3. Cambiar estado a activo
        usuario.estado = "activo"
        usuario.fecha_actualizacion = datetime.now()
        
        # 4. Cambiar estado de la persona a activo
        if usuario.persona:
            usuario.persona.estado = "activo"
            usuario.persona.fecha_actualizacion = datetime.now()
        
        # 5. Resetear intentos fallidos por si acaso
        usuario.intentos_fallidos = 0
        usuario.fecha_bloqueo = None
        usuario.fecha_ultimo_intento_fallido = None
        
        # 6. Commit
        db.commit()
        
        # 7. Log
        log_security_event(
            "USER_REACTIVATED",
            usuario.username,
            "Usuario reactivado desde estado inactivo",
            success=True,
            ip_address=client_ip
        )
        
        return {
            "message": f"Usuario '{usuario.username}' reactivado exitosamente",
            "id_usuario": id_usuario,
            "estado_anterior": "inactivo",
            "estado_actual": "activo",
            "fecha_reactivacion": datetime.now().isoformat()
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        
        log_security_event(
            "USER_REACTIVATION_ERROR",
            f"ID:{id_usuario}",
            f"Error: {str(e)}",
            success=False,
            ip_address=client_ip
        )
        
        print(f"❌ Error reactivando usuario: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al reactivar usuario"
        )
        


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
@router.get("/verificar-sesion", status_code=status.HTTP_200_OK)
async def verificar_sesion_activa(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🔐 Verificar si la sesión actual es válida
    
    - Verifica que el token sea válido
    - Verifica que el usuario exista y esté activo
    - Devuelve información básica de la sesión
    """
    try:
        # Obtener token del header Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token no proporcionado"
            )
        
        token = auth_header.replace("Bearer ", "")
        
        # Decodificar y validar token
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado"
            )
        
        # Obtener ID de usuario del token
        id_usuario = payload.get("sub")
        if not id_usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token mal formado"
            )
        
        # Verificar que el usuario existe y está activo
        usuario = db.query(Usuario).filter(
            Usuario.id_usuario == int(id_usuario)
        ).first()
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado"
            )
        
        if usuario.estado != "activo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Usuario en estado: {usuario.estado}"
            )
        
        # Sesión válida
        return {
            "valido": True,
            "id_usuario": usuario.id_usuario,
            "username": usuario.username,
            "email": usuario.email,
            "estado": usuario.estado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error verificando sesión: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error verificando sesión"
        )
        
# En usuario_router.py, AGREGAR:

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🚪 Cerrar sesión del usuario
    
    - Registra el logout en logs
    - Puede implementar blacklist de tokens si es necesario
    """
    client_ip = get_client_ip(request)
    
    try:
        # Obtener token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            payload = decode_access_token(token)
            
            if payload:
                username = payload.get("username", "desconocido")
                
                log_security_event(
                    "LOGOUT_SUCCESS",
                    username,
                    "Cierre de sesión exitoso",
                    success=True,
                    ip_address=client_ip
                )
        
        return {
            "message": "Sesión cerrada exitosamente"
        }
        
    except Exception as e:
        print(f"❌ Error en logout: {e}")
        return {
            "message": "Sesión cerrada"
        }

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
    

 # _________________________________________________________________________________

@router.get("/completo", status_code=status.HTTP_200_OK)
async def listar_usuarios_completo(
    skip: int = Query(0, ge=0, description="Registros a omitir (paginación)"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros"),
    estado: Optional[str] = Query(None, description="Filtrar por estado del usuario"),
    id_departamento: Optional[int] = Query(None, description="Filtrar por departamento"),
    id_rol: Optional[int] = Query(None, description="Filtrar por rol específico"),
    busqueda: Optional[str] = Query(None, description="Buscar por nombre, apellido, username, email o cédula"),
    db: Session = Depends(get_db)
):
    """
    📋 Listar TODOS los usuarios con información COMPLETA
    
    ✅ Incluye:
    - Datos del Usuario (username, email, estado, intentos_fallidos, último_acceso, etc.)
    - Datos de Persona (nombre, apellido, cédula, teléfono, email_personal, cargo, etc.)
    - Datos del Departamento (nombre, código, facultad, email, teléfono, ubicación)
    - Todos los Roles asignados con información detallada (nombre, nivel, permisos, fecha_asignacion)
    
    🔍 Filtros disponibles:
    - **estado**: activo, inactivo, bloqueado, suspendido
    - **id_departamento**: Filtrar por departamento
    - **id_rol**: Filtrar usuarios que tengan un rol específico
    - **busqueda**: Buscar por nombre, apellido, username, email o cédula
    
    📊 Respuesta incluye:
    - total: Cantidad total de usuarios (sin paginación)
    - skip: Registros omitidos
    - limit: Límite aplicado
    - usuarios: Lista de usuarios con toda la información
    """
    try:
        # Construir query base con joins
        query = db.query(Usuario).join(
            Persona, Usuario.id_persona == Persona.id_persona
        ).outerjoin(
            Departamento, Persona.id_departamento == Departamento.id_departamento
        )
        
        # Aplicar filtros
        if estado:
            query = query.filter(Usuario.estado == estado)
        
        if id_departamento:
            query = query.filter(Persona.id_departamento == id_departamento)
        
        if id_rol:
            # Filtrar usuarios que tengan el rol específico
            query = query.join(
                UsuarioRol, Usuario.id_usuario == UsuarioRol.id_usuario
            ).filter(
                UsuarioRol.id_rol == id_rol,
                UsuarioRol.activo == True
            )
        
        if busqueda and busqueda.strip():
            busqueda_lower = f"%{busqueda.lower()}%"
            query = query.filter(
                (Persona.nombre.ilike(busqueda_lower)) |
                (Persona.apellido.ilike(busqueda_lower)) |
                (Persona.cedula.ilike(busqueda_lower)) |
                (Usuario.username.ilike(busqueda_lower)) |
                (Usuario.email.ilike(busqueda_lower))
            )
        
        # Contar total (antes de paginación)
        total = query.count()

        # Aplicar paginación y ordenar
        usuarios = query.order_by(
            Persona.apellido.asc(), 
            Persona.nombre.asc()
        ).offset(skip).limit(limit).all()
        
        # Construir respuesta completa
        usuarios_completos = []
        
        for usuario in usuarios:
            # Obtener roles activos del usuario
            roles_usuario = db.query(UsuarioRol).filter(
                UsuarioRol.id_usuario == usuario.id_usuario,
                UsuarioRol.activo == True
            ).join(Rol).all()
            
            # Construir información de roles
            roles_info = []
            for ur in roles_usuario:
                roles_info.append({
                    "id_usuario_rol": ur.id_usuario_rol,
                    "id_rol": ur.id_rol,
                    "nombre_rol": ur.rol.nombre_rol,
                    "descripcion": ur.rol.descripcion,
                    "nivel_jerarquia": ur.rol.nivel_jerarquia,
                    "fecha_asignacion": ur.fecha_asignacion.isoformat() if ur.fecha_asignacion else None,
                    "fecha_expiracion": ur.fecha_expiracion.isoformat() if ur.fecha_expiracion else None,
                    "motivo": ur.motivo,
                    "activo": ur.activo,
                    # Permisos del rol
                    "permisos": {
                        # ==== Usuarios ====
                        "puede_ver_usuarios": ur.rol.puede_gestionar_usuarios,
                        "puede_crear_usuarios": ur.rol.puede_gestionar_usuarios,
                        "puede_editar_usuarios": ur.rol.puede_gestionar_usuarios,
                        "puede_eliminar_usuarios": ur.rol.puede_gestionar_usuarios,

                        # ==== Roles ====
                        "puede_ver_roles": ur.rol.puede_gestionar_roles,
                        "puede_crear_roles": ur.rol.puede_gestionar_roles,
                        "puede_editar_roles": ur.rol.puede_gestionar_roles,
                        "puede_eliminar_roles": ur.rol.puede_gestionar_roles,
                        "puede_asignar_roles": ur.rol.puede_gestionar_roles,

                        # ==== Agentes (por ahora puedes ligarlos a roles o usuarios, según tu lógica) ====
                        "puede_ver_agentes": ur.rol.puede_gestionar_usuarios,
                        "puede_crear_agentes": ur.rol.puede_gestionar_usuarios,
                        "puede_editar_agentes": ur.rol.puede_gestionar_usuarios,
                        "puede_eliminar_agentes": ur.rol.puede_gestionar_usuarios,

                        # ==== Conversaciones / métricas / exportación ====
                        "puede_ver_conversaciones": ur.rol.puede_ver_todas_metricas,
                        "puede_ver_todas_conversaciones": ur.rol.puede_ver_todas_metricas,
                        "puede_exportar_conversaciones": ur.rol.puede_exportar_datos_globales,

                        # ==== Departamentos ====
                        "puede_ver_departamentos": ur.rol.puede_gestionar_departamentos,
                        "puede_crear_departamentos": ur.rol.puede_gestionar_departamentos,
                        "puede_editar_departamentos": ur.rol.puede_gestionar_departamentos,
                        "puede_eliminar_departamentos": ur.rol.puede_gestionar_departamentos,

                        # ==== Contenido (si aún no tienes columnas, de momento en False) ====
                        "puede_ver_contenido": False,
                        "puede_crear_contenido": False,
                        "puede_editar_contenido": False,
                        "puede_eliminar_contenido": False,

                        # ==== Sistema ====
                        "puede_ver_logs": ur.rol.puede_configurar_sistema,
                        "puede_configurar_sistema": ur.rol.puede_configurar_sistema,
                        "puede_gestionar_api_keys": ur.rol.puede_gestionar_api_keys,
                        "puede_exportar_datos": ur.rol.puede_exportar_datos_globales,
                        "puede_ver_estadisticas": ur.rol.puede_ver_todas_metricas,
                    }

                })
            
            # Información del departamento (si existe)
            departamento_info = None
            if usuario.persona and usuario.persona.departamento:
                dept = usuario.persona.departamento
                departamento_info = {
                    "id_departamento": dept.id_departamento,
                    "nombre": dept.nombre,
                    "codigo": dept.codigo,
                    "descripcion": dept.descripcion,
                    "facultad": dept.facultad,
                    "email": dept.email,
                    "telefono": dept.telefono,
                    "ubicacion": dept.ubicacion,
                    "activo": dept.activo
                }
            
            # Construir objeto completo del usuario
            usuario_completo = {
                # Datos del Usuario
                "id_usuario": usuario.id_usuario,
                "username": usuario.username,
                "email": usuario.email,
                "estado": usuario.estado,
                "requiere_cambio_password": usuario.requiere_cambio_password,
                "intentos_fallidos": usuario.intentos_fallidos,
                "ultimo_acceso": usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None,
                "ultimo_ip": usuario.ultimo_ip,
                "fecha_creacion": usuario.fecha_creacion.isoformat() if usuario.fecha_creacion else None,
                "fecha_actualizacion": usuario.fecha_actualizacion.isoformat() if usuario.fecha_actualizacion else None,
                
                # Datos de Persona
                "persona": {
                    "id_persona": usuario.persona.id_persona,
                    "cedula": usuario.persona.cedula,
                    "nombre": usuario.persona.nombre,
                    "apellido": usuario.persona.apellido,
                    "nombre_completo": f"{usuario.persona.nombre} {usuario.persona.apellido}",
                    "fecha_nacimiento": usuario.persona.fecha_nacimiento.isoformat() if usuario.persona.fecha_nacimiento else None,
                    "genero": usuario.persona.genero,
                    "telefono": usuario.persona.telefono,
                    "celular": usuario.persona.celular,
                    "email_personal": usuario.persona.email_personal,
                    "direccion": usuario.persona.direccion,
                    "ciudad": usuario.persona.ciudad,
                    "provincia": usuario.persona.provincia,
                    "tipo_persona": usuario.persona.tipo_persona,
                    "cargo": usuario.persona.cargo,
                    "fecha_ingreso_institucion": usuario.persona.fecha_ingreso_institucion.isoformat() if usuario.persona.fecha_ingreso_institucion else None,
                    "contacto_emergencia_nombre": usuario.persona.contacto_emergencia_nombre,
                    "contacto_emergencia_telefono": usuario.persona.contacto_emergencia_telefono,
                    "contacto_emergencia_relacion": usuario.persona.contacto_emergencia_relacion,
                    "foto_perfil": usuario.persona.foto_perfil,
                    "estado": usuario.persona.estado,
                    "fecha_registro": usuario.persona.fecha_registro.isoformat() if usuario.persona.fecha_registro else None
                } if usuario.persona else None,
                
                # Datos del Departamento
                "departamento": departamento_info,
                
                # Roles asignados
                "roles": roles_info,
                "total_roles": len(roles_info),
                
                # Rol principal (el de mayor jerarquía = nivel más bajo)
                "rol_principal": min(roles_info, key=lambda r: r["nivel_jerarquia"]) if roles_info else None
            }
            
            usuarios_completos.append(usuario_completo)
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "usuarios": usuarios_completos
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error listando usuarios completos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar usuarios: {str(e)}"
        )
    
# ------------------------------------------------------------------------

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






@router.put("/{id_usuario}/cambiar-departamento", 
            response_model=CambiarDepartamentoResponse,
            status_code=status.HTTP_200_OK)
async def cambiar_departamento(
    id_usuario: int,
    data: CambiarDepartamentoRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🏢 Cambiar departamento de un usuario
    
    - Actualiza el departamento en la tabla Persona
    - Valida que el departamento exista (si se proporciona)
    - Permite remover departamento (id_departamento = null)
    - Registra el cambio para auditoría
    """
    client_ip = get_client_ip(request)
    
    try:
        # 1. Verificar que el usuario existe
        usuario = db.query(Usuario).filter(
            Usuario.id_usuario == id_usuario
        ).first()
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {id_usuario} no encontrado"
            )
        
        # 2. Verificar que el usuario tiene persona asociada
        if not usuario.persona:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario no tiene información de persona asociada"
            )
        
        persona = usuario.persona
        
        # 3. Guardar departamento anterior para la respuesta
        departamento_anterior = None
        if persona.id_departamento:
            dept_ant = db.query(Departamento).filter(
                Departamento.id_departamento == persona.id_departamento
            ).first()
            
            if dept_ant:
                departamento_anterior = {
                    "id_departamento": dept_ant.id_departamento,
                    "nombre": dept_ant.nombre,
                    "codigo": dept_ant.codigo,
                    "facultad": dept_ant.facultad
                }
        
        # 4. Validar nuevo departamento (si se proporciona)
        departamento_nuevo = None
        if data.id_departamento is not None:
            dept_nuevo = db.query(Departamento).filter(
                Departamento.id_departamento == data.id_departamento,
                Departamento.activo == True
            ).first()
            
            if not dept_nuevo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Departamento con ID {data.id_departamento} no encontrado o inactivo"
                )
            
            departamento_nuevo = {
                "id_departamento": dept_nuevo.id_departamento,
                "nombre": dept_nuevo.nombre,
                "codigo": dept_nuevo.codigo,
                "facultad": dept_nuevo.facultad
            }
        
        # 5. Verificar si hay cambio real
        if persona.id_departamento == data.id_departamento:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya pertenece a este departamento"
            )
        
        # 6. Actualizar departamento en Persona
        persona.id_departamento = data.id_departamento
        persona.fecha_actualizacion = datetime.now()
        
        # 7. Commit de la transacción
        db.commit()
        db.refresh(persona)
        db.refresh(usuario)
        
        # 8. Log de seguridad
        mensaje_log = f"Cambio de departamento"
        if departamento_anterior:
            mensaje_log += f" desde {departamento_anterior['nombre']}"
        if departamento_nuevo:
            mensaje_log += f" hacia {departamento_nuevo['nombre']}"
        else:
            mensaje_log += " (departamento removido)"
        
        if data.motivo:
            mensaje_log += f" - Motivo: {data.motivo}"
        
        log_security_event(
            "DEPARTAMENTO_CHANGED",
            usuario.username,
            mensaje_log,
            success=True,
            ip_address=client_ip
        )
        
        # 9. Construir respuesta
        mensaje = "Departamento actualizado exitosamente"
        if data.id_departamento is None:
            mensaje = "Departamento removido exitosamente"
        
        return {
            "message": mensaje,
            "usuario": {
                "id_usuario": usuario.id_usuario,
                "username": usuario.username,
                "email": usuario.email,
                "persona": {
                    "id_persona": persona.id_persona,
                    "nombre": persona.nombre,
                    "apellido": persona.apellido,
                    "cedula": persona.cedula
                }
            },
            "departamento_anterior": departamento_anterior,
            "departamento_nuevo": departamento_nuevo,
            "fecha_cambio": datetime.now()
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        
        log_security_event(
            "DEPARTAMENTO_CHANGE_ERROR",
            f"Usuario ID: {id_usuario}",
            f"Error: {str(e)}",
            success=False,
            ip_address=client_ip
        )
        
        print(f"❌ Error cambiando departamento: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cambiar departamento"
        )