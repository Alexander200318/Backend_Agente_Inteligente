# routers/usuario_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt

from database.database import get_db
from models.usuario import Usuario
from repositories.usuario_repo import UsuarioRepository
from exceptions.base import NotFoundException, BadRequestException

# ========== CONFIGURACIÓN DE SEGURIDAD ==========
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ⚠️ MOVER ESTO A core/config.py EN PRODUCCIÓN
SECRET_KEY = "tu-clave-secreta-super-segura-cambiala-en-produccion-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "admin123"
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

class UsuarioUpdate(BaseModel):
    """Schema para actualizar usuario"""
    email: Optional[EmailStr] = None
    estado: Optional[str] = None

class PasswordChange(BaseModel):
    """Schema para cambio de contraseña"""
    password_actual: str
    password_nuevo: str

# ========== ENDPOINTS ==========

@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    🔐 Endpoint de autenticación
    
    - Valida credenciales de usuario
    - Genera token JWT
    - Registra intentos fallidos
    - Bloquea usuario después de 5 intentos
    
    **Returns:**
    - `token`: Token JWT para autenticación
    - `usuario`: Datos del usuario autenticado
    """
    print(f"📥 [LOGIN] Recibiendo login request")
    print(f"📥 [LOGIN] Username: {credentials.username}")
    print(f"📥 [LOGIN] Password length: {len(credentials.password)}")
    
    try:
        # 1. Buscar usuario
        usuario = db.query(Usuario).filter(
            Usuario.username == credentials.username
        ).first()
        
        if not usuario:
            print(f"❌ [LOGIN] Usuario no encontrado: {credentials.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos"
            )
        
        print(f"✅ [LOGIN] Usuario encontrado: {usuario.username}")
        print(f"📊 [LOGIN] Estado: {usuario.estado}")
        print(f"📊 [LOGIN] Intentos fallidos: {usuario.intentos_fallidos}")
        
        # 2. Verificar estado del usuario
        if usuario.estado == "bloqueado":
            print(f"🔒 [LOGIN] Usuario bloqueado: {usuario.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario bloqueado. Contacta al administrador"
            )
        
        if usuario.estado == "inactivo":
            print(f"⏸️ [LOGIN] Usuario inactivo: {usuario.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo. Contacta al administrador"
            )
        
        if usuario.estado == "suspendido":
            print(f"⏸️ [LOGIN] Usuario suspendido: {usuario.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario suspendido. Contacta al administrador"
            )
        
        # 3. Verificar contraseña
        if not pwd_context.verify(credentials.password, usuario.password):
            print(f"❌ [LOGIN] Contraseña incorrecta para: {usuario.username}")
            
            # Registrar intento fallido
            usuario.intentos_fallidos += 1
            usuario.fecha_ultimo_intento_fallido = datetime.now()
            
            print(f"⚠️ [LOGIN] Intento fallido #{usuario.intentos_fallidos}")
            
            # Bloquear si supera 5 intentos
            if usuario.intentos_fallidos >= 5:
                usuario.estado = "bloqueado"
                usuario.fecha_bloqueo = datetime.now()
                db.commit()
                print(f"🔒 [LOGIN] Usuario bloqueado por intentos fallidos: {usuario.username}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuario bloqueado por múltiples intentos fallidos. Contacta al administrador"
                )
            
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos"
            )
        
        print(f"✅ [LOGIN] Contraseña correcta para: {usuario.username}")
        
        # 4. Login exitoso - resetear intentos
        usuario.intentos_fallidos = 0
        usuario.ultimo_acceso = datetime.now()
        usuario.fecha_ultimo_intento_fallido = None
        db.commit()
        
        print(f"✅ [LOGIN] Intentos fallidos reseteados")
        
        # 5. Crear token JWT
        token_data = {
            "sub": str(usuario.id_usuario),
            "username": usuario.username,
            "email": usuario.email,
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        
        print(f"🎫 [LOGIN] Token JWT generado para: {usuario.username}")
        print(f"✅ [LOGIN] Login exitoso completado")
        
        # 6. Respuesta
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
        print(f"❌ [LOGIN] Error inesperado: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    usuario_data: UsuarioCreate,
    db: Session = Depends(get_db)
):
    """
    ➕ Crear nuevo usuario
    
    - Valida que username y email sean únicos
    - Verifica que la persona exista
    - Hashea la contraseña antes de guardar
    """
    repo = UsuarioRepository(db)
    
    try:
        # Validaciones
        if repo.exists_by_username(usuario_data.username):
            raise BadRequestException(
                f"El username '{usuario_data.username}' ya está en uso"
            )
        
        if repo.exists_by_email(usuario_data.email):
            raise BadRequestException(
                f"El email '{usuario_data.email}' ya está en uso"
            )
        
        persona = repo.get_persona_by_id(usuario_data.id_persona)
        if not persona:
            raise NotFoundException(
                f"Persona con ID {usuario_data.id_persona} no encontrada"
            )
        
        # Hash de la contraseña
        hashed_password = pwd_context.hash(usuario_data.password)
        usuario_data.password = hashed_password
        
        # Crear usuario
        nuevo_usuario = repo.create(usuario_data, persona)
        
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
    db: Session = Depends(get_db)
):
    """✏️ Actualizar usuario"""
    repo = UsuarioRepository(db)
    
    try:
        usuario_actualizado = repo.update(id_usuario, usuario_data)
        
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
    db: Session = Depends(get_db)
):
    """🗑️ Desactivar usuario (soft delete)"""
    repo = UsuarioRepository(db)
    
    try:
        resultado = repo.delete(id_usuario)
        return resultado
    except NotFoundException:
        raise


@router.post("/{id_usuario}/cambiar-password", status_code=status.HTTP_200_OK)
async def cambiar_password(
    id_usuario: int,
    password_data: PasswordChange,
    db: Session = Depends(get_db)
):
    """🔑 Cambiar contraseña de usuario"""
    repo = UsuarioRepository(db)
    
    try:
        usuario = repo.get_by_id(id_usuario)
        
        # Verificar contraseña actual
        if not pwd_context.verify(password_data.password_actual, usuario.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña actual incorrecta"
            )
        
        # Validar que la nueva contraseña sea diferente
        if password_data.password_actual == password_data.password_nuevo:
            raise BadRequestException(
                "La nueva contraseña debe ser diferente a la actual"
            )
        
        # Hash de nueva contraseña
        nueva_password_hash = pwd_context.hash(password_data.password_nuevo)
        
        # Actualizar
        repo.update_password(id_usuario, nueva_password_hash)
        
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
    db: Session = Depends(get_db)
):
    """🔓 Desbloquear usuario"""
    repo = UsuarioRepository(db)
    
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