from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from repositories.usuario_rol_repo import UsuarioRolRepository
from schemas.usuario_rol_schemas import (
    UsuarioRolCreate, 
    UsuarioRolUpdate,
    AsignarMultiplesRolesRequest
)
from models.usuario_rol import UsuarioRol
from exceptions.base import ValidationException, NotFoundException

class UsuarioRolService:
    """Servicio con lógica de negocio para UsuarioRol"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = UsuarioRolRepository(db)
    
    def asignar_rol(
        self, 
        usuario_rol_data: UsuarioRolCreate,
        asignado_por_id: Optional[int] = None
    ) -> UsuarioRol:
        """
        Asignar rol a usuario con validaciones de negocio
        """
        # Validar que el usuario existe
        usuario = self.repo.get_usuario_by_id(usuario_rol_data.id_usuario)
        if not usuario:
            raise NotFoundException("Usuario", usuario_rol_data.id_usuario)
        
        # Validar que el rol existe
        rol = self.repo.get_rol_by_id(usuario_rol_data.id_rol)
        if not rol:
            raise NotFoundException("Rol", usuario_rol_data.id_rol)
        
        # Validar que el rol esté activo
        if not rol.activo:
            raise ValidationException(f"El rol '{rol.nombre_rol}' está inactivo y no puede ser asignado")
        
        # Validar que el usuario esté activo
        if usuario.estado != "activo":
            raise ValidationException(
                f"El usuario está en estado '{usuario.estado}'. "
                "Solo se pueden asignar roles a usuarios activos"
            )
        
        # Validar jerarquía: no asignar Super Admin a cualquiera
        if rol.nivel_jerarquia == 1:
            raise ValidationException(
                "No se puede asignar el rol de Super Administrador mediante este método. "
                "Contacte al administrador del sistema"
            )
        
        # Validar fecha de expiración
        if usuario_rol_data.fecha_expiracion:
            if usuario_rol_data.fecha_expiracion <= datetime.now():
                raise ValidationException("La fecha de expiración debe ser futura")
        
        # Crear asignación
        return self.repo.create(usuario_rol_data, asignado_por_id)
    
    def asignar_multiples_roles(
        self,
        id_usuario: int,
        roles_data: AsignarMultiplesRolesRequest,
        asignado_por_id: Optional[int] = None
    ) -> dict:
        """Asignar múltiples roles a un usuario de una vez"""
        # Validar que el usuario existe
        usuario = self.repo.get_usuario_by_id(id_usuario)
        if not usuario:
            raise NotFoundException("Usuario", id_usuario)
        
        if usuario.estado != "activo":
            raise ValidationException(
                f"El usuario está en estado '{usuario.estado}'. "
                "Solo se pueden asignar roles a usuarios activos"
            )
        
        asignados = []
        errores = []
        
        for id_rol in roles_data.roles:
            try:
                # Verificar si ya tiene el rol
                if self.repo.usuario_tiene_rol(id_usuario, id_rol):
                    errores.append({
                        "id_rol": id_rol,
                        "error": "El usuario ya tiene este rol asignado"
                    })
                    continue
                
                usuario_rol_data = UsuarioRolCreate(
                    id_usuario=id_usuario,
                    id_rol=id_rol,
                    motivo=roles_data.motivo,
                    fecha_expiracion=roles_data.fecha_expiracion
                )
                
                asignacion = self.repo.create(usuario_rol_data, asignado_por_id)
                asignados.append({
                    "id_usuario_rol": asignacion.id_usuario_rol,
                    "id_rol": id_rol
                })
                
            except Exception as e:
                errores.append({
                    "id_rol": id_rol,
                    "error": str(e)
                })
        
        return {
            "message": f"Se asignaron {len(asignados)} roles exitosamente",
            "asignados": asignados,
            "errores": errores if errores else None,
            "total_procesados": len(roles_data.roles),
            "exitosos": len(asignados),
            "fallidos": len(errores)
        }
    
    def obtener_asignacion(self, id_usuario_rol: int) -> UsuarioRol:
        """Obtener asignación por ID"""
        return self.repo.get_by_id(id_usuario_rol, include_relations=True)
    
    def listar_asignaciones(
        self,
        skip: int = 0,
        limit: int = 100,
        id_usuario: Optional[int] = None,
        id_rol: Optional[int] = None,
        solo_activos: Optional[bool] = None
    ) -> List[UsuarioRol]:
        """Listar asignaciones con filtros"""
        if limit > 500:
            raise ValidationException("El límite máximo es 500 registros")
        
        return self.repo.get_all(
            skip=skip,
            limit=limit,
            id_usuario=id_usuario,
            id_rol=id_rol,
            solo_activos=solo_activos,
            include_relations=True
        )
    
    def obtener_roles_usuario(
        self, 
        id_usuario: int,
        solo_activos: bool = True
    ) -> List[UsuarioRol]:
        """Obtener todos los roles de un usuario"""
        usuario = self.repo.get_usuario_by_id(id_usuario)
        if not usuario:
            raise NotFoundException("Usuario", id_usuario)
        
        return self.repo.get_roles_by_usuario(id_usuario, solo_activos, include_relations=True)
    
    def obtener_usuarios_con_rol(
        self, 
        id_rol: int,
        solo_activos: bool = True
    ) -> List[UsuarioRol]:
        """Obtener todos los usuarios que tienen un rol específico"""
        rol = self.repo.get_rol_by_id(id_rol)
        if not rol:
            raise NotFoundException("Rol", id_rol)
        
        return self.repo.get_usuarios_by_rol(id_rol, solo_activos, include_relations=True)
    
    def actualizar_asignacion(
        self,
        id_usuario_rol: int,
        usuario_rol_data: UsuarioRolUpdate
    ) -> UsuarioRol:
        """Actualizar asignación de rol"""
        # Validar fecha de expiración si se proporciona
        if usuario_rol_data.fecha_expiracion:
            if usuario_rol_data.fecha_expiracion <= datetime.now():
                raise ValidationException("La fecha de expiración debe ser futura")
        
        return self.repo.update(id_usuario_rol, usuario_rol_data)
    
    def revocar_rol(self, id_usuario: int, id_rol: int) -> dict:
        """Revocar un rol específico de un usuario"""
        return self.repo.revocar_rol_usuario(id_usuario, id_rol)
    
    def revocar_todos_roles(self, id_usuario: int) -> dict:
        """Revocar todos los roles de un usuario"""
        usuario = self.repo.get_usuario_by_id(id_usuario)
        if not usuario:
            raise NotFoundException("Usuario", id_usuario)
        
        return self.repo.revocar_todos_roles_usuario(id_usuario)
    
    def eliminar_asignacion(self, id_usuario_rol: int) -> dict:
        """Desactivar asignación (soft delete)"""
        return self.repo.delete(id_usuario_rol)
    
    def verificar_usuario_tiene_rol(
        self, 
        id_usuario: int, 
        id_rol: int,
        solo_activos: bool = True
    ) -> bool:
        """Verificar si un usuario tiene un rol específico"""
        return self.repo.usuario_tiene_rol(id_usuario, id_rol, solo_activos)
    
    def verificar_usuario_tiene_cualquier_rol(
        self,
        id_usuario: int,
        ids_roles: List[int],
        solo_activos: bool = True
    ) -> bool:
        """Verificar si un usuario tiene al menos uno de los roles especificados"""
        for id_rol in ids_roles:
            if self.repo.usuario_tiene_rol(id_usuario, id_rol, solo_activos):
                return True
        return False
    
    def verificar_usuario_tiene_todos_roles(
        self,
        id_usuario: int,
        ids_roles: List[int],
        solo_activos: bool = True
    ) -> bool:
        """Verificar si un usuario tiene todos los roles especificados"""
        for id_rol in ids_roles:
            if not self.repo.usuario_tiene_rol(id_usuario, id_rol, solo_activos):
                return False
        return True
    
    def procesar_expiraciones(self) -> dict:
        """Procesar y desactivar asignaciones expiradas"""
        count = self.repo.verificar_expiraciones()
        
        return {
            "message": f"Se procesaron {count} asignaciones expiradas",
            "asignaciones_desactivadas": count
        }
    
    def obtener_estadisticas(self) -> dict:
        """Obtener estadísticas generales de asignaciones"""
        return {
            "total_asignaciones": self.repo.count(),
            "asignaciones_activas": self.repo.count(solo_activos=True),
            "asignaciones_inactivas": self.repo.count(solo_activos=False)
        }
    
    def obtener_estadisticas_usuario(self, id_usuario: int) -> dict:
        """Obtener estadísticas de roles de un usuario"""
        usuario = self.repo.get_usuario_by_id(id_usuario)
        if not usuario:
            raise NotFoundException("Usuario", id_usuario)
        
        roles = self.repo.get_roles_by_usuario(id_usuario, solo_activos=False, include_relations=True)
        roles_activos = [r for r in roles if r.activo]
        roles_inactivos = [r for r in roles if not r.activo]
        
        return {
            "id_usuario": id_usuario,
            "username": usuario.username,
            "total_roles_asignados": len(roles),
            "roles_activos": len(roles_activos),
            "roles_inactivos": len(roles_inactivos),
            "roles": [
                {
                    "id_rol": r.id_rol,
                    "nombre_rol": r.rol.nombre_rol if r.rol else None,
                    "nivel_jerarquia": r.rol.nivel_jerarquia if r.rol else None,
                    "activo": r.activo,
                    "fecha_asignacion": r.fecha_asignacion,
                    "fecha_expiracion": r.fecha_expiracion
                }
                for r in roles_activos
            ]
        }
    
    def obtener_estadisticas_rol(self, id_rol: int) -> dict:
        """Obtener estadísticas de usuarios con un rol"""
        rol = self.repo.get_rol_by_id(id_rol)
        if not rol:
            raise NotFoundException("Rol", id_rol)
        
        usuarios = self.repo.get_usuarios_by_rol(id_rol, solo_activos=False, include_relations=True)
        usuarios_activos = [u for u in usuarios if u.activo]
        usuarios_inactivos = [u for u in usuarios if not u.activo]
        
        return {
            "id_rol": id_rol,
            "nombre_rol": rol.nombre_rol,
            "nivel_jerarquia": rol.nivel_jerarquia,
            "total_usuarios": len(usuarios),
            "usuarios_activos": len(usuarios_activos),
            "usuarios_inactivos": len(usuarios_inactivos),
            "usuarios": [
                {
                    "id_usuario": u.id_usuario,
                    "username": u.usuario.username if u.usuario else None,
                    "email": u.usuario.email if u.usuario else None,
                    "activo": u.activo,
                    "fecha_asignacion": u.fecha_asignacion,
                    "fecha_expiracion": u.fecha_expiracion
                }
                for u in usuarios_activos
            ]
        }