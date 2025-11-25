from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.usuario_rol_service import UsuarioRolService
from schemas.usuario_rol_schemas import (
    UsuarioRolResponse,
    UsuarioRolCreate,
    UsuarioRolUpdate,
    AsignarRolRequest,
    AsignarMultiplesRolesRequest
)
from exceptions.base import NotFoundException, ValidationException

router = APIRouter(prefix="/usuario-roles", tags=["Usuario-Roles"])

# ==================== ENDPOINTS CRUD BÁSICOS ====================

@router.post("/", response_model=UsuarioRolResponse, status_code=status.HTTP_201_CREATED)
def asignar_rol(
    usuario_rol: UsuarioRolCreate,
    db: Session = Depends(get_db)
):
    """
    ➕ Asignar un rol a un usuario
    
    - Valida que el usuario y el rol existan
    - Valida que el rol esté activo
    - Valida que el usuario esté activo
    - Previene asignación de Super Admin
    - Verifica que no exista asignación duplicada activa
    """
    service = UsuarioRolService(db)
    asignacion = service.asignar_rol(usuario_rol)
    
    # Construir respuesta con datos relacionados
    return UsuarioRolResponse(
        id_usuario_rol=asignacion.id_usuario_rol,
        id_usuario=asignacion.id_usuario,
        id_rol=asignacion.id_rol,
        fecha_asignacion=asignacion.fecha_asignacion,
        fecha_expiracion=asignacion.fecha_expiracion,
        motivo=asignacion.motivo,
        activo=asignacion.activo,
        usuario_username=asignacion.usuario.username if asignacion.usuario else None,
        usuario_email=asignacion.usuario.email if asignacion.usuario else None,
        rol_nombre=asignacion.rol.nombre_rol if asignacion.rol else None,
        rol_nivel_jerarquia=asignacion.rol.nivel_jerarquia if asignacion.rol else None
    )

@router.get("/", status_code=status.HTTP_200_OK)
def listar_asignaciones(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    id_usuario: Optional[int] = None,
    id_rol: Optional[int] = None,
    solo_activos: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    📋 Listar todas las asignaciones de roles con filtros
    
    - **skip**: Cantidad de registros a omitir (paginación)
    - **limit**: Cantidad máxima de registros a retornar
    - **id_usuario**: Filtrar por usuario específico
    - **id_rol**: Filtrar por rol específico
    - **solo_activos**: Filtrar solo asignaciones activas (true) o inactivas (false)
    """
    service = UsuarioRolService(db)
    asignaciones = service.listar_asignaciones(
        skip=skip,
        limit=limit,
        id_usuario=id_usuario,
        id_rol=id_rol,
        solo_activos=solo_activos
    )
    
    total = service.repo.count(id_usuario=id_usuario, id_rol=id_rol, solo_activos=solo_activos)
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "asignaciones": [
            {
                "id_usuario_rol": a.id_usuario_rol,
                "id_usuario": a.id_usuario,
                "id_rol": a.id_rol,
                "usuario_username": a.usuario.username if a.usuario else None,
                "usuario_email": a.usuario.email if a.usuario else None,
                "rol_nombre": a.rol.nombre_rol if a.rol else None,
                "rol_nivel_jerarquia": a.rol.nivel_jerarquia if a.rol else None,
                "fecha_asignacion": a.fecha_asignacion,
                "fecha_expiracion": a.fecha_expiracion,
                "motivo": a.motivo,
                "activo": a.activo
            }
            for a in asignaciones
        ]
    }

@router.get("/estadisticas", status_code=status.HTTP_200_OK)
def obtener_estadisticas(db: Session = Depends(get_db)):
    """📊 Obtener estadísticas generales de asignaciones de roles"""
    service = UsuarioRolService(db)
    return service.obtener_estadisticas()

@router.get("/{id_usuario_rol}", response_model=UsuarioRolResponse)
def obtener_asignacion(
    id_usuario_rol: int,
    db: Session = Depends(get_db)
):
    """🔍 Obtener una asignación específica por ID"""
    service = UsuarioRolService(db)
    asignacion = service.obtener_asignacion(id_usuario_rol)
    
    return UsuarioRolResponse(
        id_usuario_rol=asignacion.id_usuario_rol,
        id_usuario=asignacion.id_usuario,
        id_rol=asignacion.id_rol,
        fecha_asignacion=asignacion.fecha_asignacion,
        fecha_expiracion=asignacion.fecha_expiracion,
        motivo=asignacion.motivo,
        activo=asignacion.activo,
        usuario_username=asignacion.usuario.username if asignacion.usuario else None,
        usuario_email=asignacion.usuario.email if asignacion.usuario else None,
        rol_nombre=asignacion.rol.nombre_rol if asignacion.rol else None,
        rol_nivel_jerarquia=asignacion.rol.nivel_jerarquia if asignacion.rol else None
    )

@router.put("/{id_usuario_rol}", response_model=UsuarioRolResponse)
def actualizar_asignacion(
    id_usuario_rol: int,
    usuario_rol: UsuarioRolUpdate,
    db: Session = Depends(get_db)
):
    """✏️ Actualizar una asignación de rol (fecha de expiración, motivo, estado activo)"""
    service = UsuarioRolService(db)
    asignacion = service.actualizar_asignacion(id_usuario_rol, usuario_rol)
    
    return UsuarioRolResponse(
        id_usuario_rol=asignacion.id_usuario_rol,
        id_usuario=asignacion.id_usuario,
        id_rol=asignacion.id_rol,
        fecha_asignacion=asignacion.fecha_asignacion,
        fecha_expiracion=asignacion.fecha_expiracion,
        motivo=asignacion.motivo,
        activo=asignacion.activo,
        usuario_username=asignacion.usuario.username if asignacion.usuario else None,
        usuario_email=asignacion.usuario.email if asignacion.usuario else None,
        rol_nombre=asignacion.rol.nombre_rol if asignacion.rol else None,
        rol_nivel_jerarquia=asignacion.rol.nivel_jerarquia if asignacion.rol else None
    )

@router.delete("/{id_usuario_rol}", status_code=status.HTTP_200_OK)
def eliminar_asignacion(
    id_usuario_rol: int,
    db: Session = Depends(get_db)
):
    """🗑️ Desactivar una asignación de rol (soft delete)"""
    service = UsuarioRolService(db)
    return service.eliminar_asignacion(id_usuario_rol)

# ==================== ENDPOINTS ESPECÍFICOS DE USUARIO ====================

@router.get("/usuario/{id_usuario}/roles", status_code=status.HTTP_200_OK)
def obtener_roles_usuario(
    id_usuario: int,
    solo_activos: bool = Query(True, description="Filtrar solo roles activos"),
    db: Session = Depends(get_db)
):
    """
    👤 Obtener todos los roles de un usuario específico
    
    Útil para verificar permisos y accesos del usuario
    """
    service = UsuarioRolService(db)
    roles = service.obtener_roles_usuario(id_usuario, solo_activos)
    
    return {
        "id_usuario": id_usuario,
        "total_roles": len(roles),
        "roles": [
            {
                "id_usuario_rol": r.id_usuario_rol,
                "id_rol": r.id_rol,
                "rol_nombre": r.rol.nombre_rol if r.rol else None,
                "rol_descripcion": r.rol.descripcion if r.rol else None,
                "nivel_jerarquia": r.rol.nivel_jerarquia if r.rol else None,
                "fecha_asignacion": r.fecha_asignacion,
                "fecha_expiracion": r.fecha_expiracion,
                "motivo": r.motivo,
                "activo": r.activo
            }
            for r in roles
        ]
    }

@router.get("/usuario/{id_usuario}/estadisticas", status_code=status.HTTP_200_OK)
def obtener_estadisticas_usuario(
    id_usuario: int,
    db: Session = Depends(get_db)
):
    """📊 Obtener estadísticas detalladas de roles de un usuario"""
    service = UsuarioRolService(db)
    return service.obtener_estadisticas_usuario(id_usuario)

@router.post("/usuario/{id_usuario}/asignar-rol", response_model=UsuarioRolResponse, status_code=status.HTTP_201_CREATED)
def asignar_rol_a_usuario(
    id_usuario: int,
    rol_data: AsignarRolRequest,
    db: Session = Depends(get_db)
):
    """
    ➕ Asignar un rol a un usuario (endpoint simplificado)
    
    Endpoint alternativo más simple para asignar un rol
    """
    service = UsuarioRolService(db)
    
    usuario_rol_data = UsuarioRolCreate(
        id_usuario=id_usuario,
        id_rol=rol_data.id_rol,
        motivo=rol_data.motivo,
        fecha_expiracion=rol_data.fecha_expiracion
    )
    
    asignacion = service.asignar_rol(usuario_rol_data)
    
    return UsuarioRolResponse(
        id_usuario_rol=asignacion.id_usuario_rol,
        id_usuario=asignacion.id_usuario,
        id_rol=asignacion.id_rol,
        fecha_asignacion=asignacion.fecha_asignacion,
        fecha_expiracion=asignacion.fecha_expiracion,
        motivo=asignacion.motivo,
        activo=asignacion.activo,
        usuario_username=asignacion.usuario.username if asignacion.usuario else None,
        usuario_email=asignacion.usuario.email if asignacion.usuario else None,
        rol_nombre=asignacion.rol.nombre_rol if asignacion.rol else None,
        rol_nivel_jerarquia=asignacion.rol.nivel_jerarquia if asignacion.rol else None
    )

@router.post("/usuario/{id_usuario}/asignar-multiples-roles", status_code=status.HTTP_201_CREATED)
def asignar_multiples_roles_a_usuario(
    id_usuario: int,
    roles_data: AsignarMultiplesRolesRequest,
    db: Session = Depends(get_db)
):
    """
    ➕➕ Asignar múltiples roles a un usuario de una vez
    
    Permite asignar varios roles en una sola operación
    """
    service = UsuarioRolService(db)
    return service.asignar_multiples_roles(id_usuario, roles_data)

@router.delete("/usuario/{id_usuario}/revocar-rol/{id_rol}", status_code=status.HTTP_200_OK)
def revocar_rol_usuario(
    id_usuario: int,
    id_rol: int,
    db: Session = Depends(get_db)
):
    """❌ Revocar un rol específico de un usuario"""
    service = UsuarioRolService(db)
    return service.revocar_rol(id_usuario, id_rol)

@router.delete("/usuario/{id_usuario}/revocar-todos-roles", status_code=status.HTTP_200_OK)
def revocar_todos_roles_usuario(
    id_usuario: int,
    db: Session = Depends(get_db)
):
    """❌❌ Revocar todos los roles activos de un usuario"""
    service = UsuarioRolService(db)
    return service.revocar_todos_roles(id_usuario)

# ==================== ENDPOINTS ESPECÍFICOS DE ROL ====================

@router.get("/rol/{id_rol}/usuarios", status_code=status.HTTP_200_OK)
def obtener_usuarios_con_rol(
    id_rol: int,
    solo_activos: bool = Query(True, description="Filtrar solo asignaciones activas"),
    db: Session = Depends(get_db)
):
    """
    👥 Obtener todos los usuarios que tienen un rol específico
    
    Útil para gestión de permisos y auditoría
    """
    service = UsuarioRolService(db)
    usuarios = service.obtener_usuarios_con_rol(id_rol, solo_activos)
    
    return {
        "id_rol": id_rol,
        "total_usuarios": len(usuarios),
        "usuarios": [
            {
                "id_usuario_rol": u.id_usuario_rol,
                "id_usuario": u.id_usuario,
                "usuario_username": u.usuario.username if u.usuario else None,
                "usuario_email": u.usuario.email if u.usuario else None,
                "usuario_estado": u.usuario.estado if u.usuario else None,
                "fecha_asignacion": u.fecha_asignacion,
                "fecha_expiracion": u.fecha_expiracion,
                "motivo": u.motivo,
                "activo": u.activo
            }
            for u in usuarios
        ]
    }

@router.get("/rol/{id_rol}/estadisticas", status_code=status.HTTP_200_OK)
def obtener_estadisticas_rol(
    id_rol: int,
    db: Session = Depends(get_db)
):
    """📊 Obtener estadísticas detalladas de usuarios con un rol"""
    service = UsuarioRolService(db)
    return service.obtener_estadisticas_rol(id_rol)

# ==================== ENDPOINTS DE VERIFICACIÓN ====================

@router.get("/verificar/usuario/{id_usuario}/tiene-rol/{id_rol}", status_code=status.HTTP_200_OK)
def verificar_usuario_tiene_rol(
    id_usuario: int,
    id_rol: int,
    solo_activos: bool = Query(True, description="Verificar solo asignaciones activas"),
    db: Session = Depends(get_db)
):
    """
    ✅ Verificar si un usuario tiene un rol específico
    
    Útil para validaciones de permisos
    """
    service = UsuarioRolService(db)
    tiene_rol = service.verificar_usuario_tiene_rol(id_usuario, id_rol, solo_activos)
    
    return {
        "id_usuario": id_usuario,
        "id_rol": id_rol,
        "tiene_rol": tiene_rol
    }

# ==================== ENDPOINTS DE MANTENIMIENTO ====================

@router.post("/procesar-expiraciones", status_code=status.HTTP_200_OK)
def procesar_expiraciones(db: Session = Depends(get_db)):
    """
    ⏰ Procesar y desactivar asignaciones expiradas
    
    Endpoint para tarea programada (cron job) que desactiva
    automáticamente las asignaciones que han expirado
    """
    service = UsuarioRolService(db)
    return service.procesar_expiraciones()