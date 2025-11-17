from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.usuario_service import UsuarioService
from schemas.usuario_schemas import (
    UsuarioCreate,
    UsuarioUpdate,
    UsuarioResponse,
    UsuarioLogin,
    UsuarioLoginResponse,
    CambioPasswordRequest
)

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"]
)

# ==================== ENDPOINTS ====================

@router.post(
    "/",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario",
    description="Crea un usuario con su persona asociada. Valida edad mínima, tipo de persona y hashea la contraseña."
)
def crear_usuario(
    usuario: UsuarioCreate,
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo usuario:
    - **username**: único, 4-50 caracteres
    - **email**: único, formato válido
    - **password**: mínimo 8 caracteres, debe contener mayúsculas, minúsculas y números
    - **persona**: datos completos de la persona (cédula, nombres, etc.)
    """
    service = UsuarioService(db)
    return service.crear_usuario(usuario)


@router.get(
    "/",
    response_model=List[UsuarioResponse],
    summary="Listar usuarios",
    description="Obtiene listado de usuarios con paginación y filtros opcionales"
)
def listar_usuarios(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    db: Session = Depends(get_db)
):
    """
    Listar usuarios con filtros:
    - **skip**: paginación (default: 0)
    - **limit**: máximo 500 registros (default: 100)
    - **estado**: activo, inactivo, suspendido, bloqueado
    """
    service = UsuarioService(db)
    return service.listar_usuarios(skip, limit, estado)


@router.get(
    "/estadisticas",
    response_model=dict,
    summary="Estadísticas de usuarios",
    description="Obtiene contadores generales de usuarios por estado"
)
def obtener_estadisticas_usuarios(db: Session = Depends(get_db)):
    """
    Retorna estadísticas:
    - Total de usuarios
    - Usuarios por estado (activos, inactivos, bloqueados, suspendidos)
    """
    service = UsuarioService(db)
    return service.obtener_estadisticas()


@router.get(
    "/{id_usuario}",
    response_model=UsuarioResponse,
    summary="Obtener usuario por ID",
    description="Obtiene un usuario específico con su información de persona"
)
def obtener_usuario(
    id_usuario: int,
    db: Session = Depends(get_db)
):
    """
    Obtener usuario por ID incluyendo datos de persona asociada
    """
    service = UsuarioService(db)
    return service.obtener_usuario(id_usuario)


@router.put(
    "/{id_usuario}",
    response_model=UsuarioResponse,
    summary="Actualizar usuario",
    description="Actualiza datos de un usuario. Si incluye password, será hasheada automáticamente"
)
def actualizar_usuario(
    id_usuario: int,
    usuario: UsuarioUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar usuario:
    - Solo enviar los campos a modificar
    - Si se incluye password, debe cumplir reglas de seguridad
    """
    service = UsuarioService(db)
    return service.actualizar_usuario(id_usuario, usuario)


@router.delete(
    "/{id_usuario}",
    status_code=status.HTTP_200_OK,
    summary="Desactivar usuario",
    description="Desactiva un usuario (soft delete). No puede desactivarse a sí mismo"
)
def eliminar_usuario(
    id_usuario: int,
    db: Session = Depends(get_db)
):
    """
    Desactiva un usuario cambiando su estado a 'inactivo'.
    No elimina físicamente los registros.
    """
    service = UsuarioService(db)
    return service.eliminar_usuario(id_usuario)


@router.post(
    "/login",
    response_model=dict,
    summary="Autenticar usuario",
    description="Valida credenciales y registra el acceso. Bloquea tras 5 intentos fallidos"
)
def login_usuario(
    login_data: UsuarioLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Autenticar usuario:
    - Valida username y password
    - Verifica estado de cuenta (no bloqueada, no suspendida)
    - Registra intento de login
    - Bloquea automáticamente después de 5 intentos fallidos
    
    **Nota**: Este endpoint debería generar un JWT token en producción
    """
    service = UsuarioService(db)
    
    # Obtener IP del cliente
    ip_address = request.client.host if request.client else None
    
    usuario = service.autenticar_usuario(login_data, ip_address)
    
    return {
        "message": "Login exitoso",
        "usuario": usuario,
        "access_token": "TODO: Implementar JWT",
        "token_type": "bearer"
    }


@router.post(
    "/{id_usuario}/cambiar-password",
    status_code=status.HTTP_200_OK,
    summary="Cambiar contraseña",
    description="Permite al usuario cambiar su contraseña actual"
)
def cambiar_password(
    id_usuario: int,
    cambio_data: CambioPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Cambiar contraseña:
    - Valida contraseña actual
    - Nueva contraseña debe ser diferente
    - Nueva contraseña debe cumplir reglas de seguridad
    """
    service = UsuarioService(db)
    return service.cambiar_password(id_usuario, cambio_data)


@router.post(
    "/{id_usuario}/desbloquear",
    response_model=UsuarioResponse,
    summary="Desbloquear usuario",
    description="Desbloquea una cuenta bloqueada y fuerza cambio de contraseña"
)
def desbloquear_usuario(
    id_usuario: int,
    db: Session = Depends(get_db)
):
    """
    Desbloquear usuario:
    - Cambia estado de 'bloqueado' a 'activo'
    - Resetea intentos fallidos
    - Fuerza cambio de contraseña en próximo login
    
    **Requiere permisos de administrador**
    """
    service = UsuarioService(db)
    return service.desbloquear_usuario(id_usuario, desbloqueado_por_id=1)  # TODO: Obtener de JWT