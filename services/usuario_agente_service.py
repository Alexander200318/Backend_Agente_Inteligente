from exceptions.base import ValidationException
from typing import Optional
from sqlalchemy.orm import Session
from repositories.usuario_agente_repo import UsuarioAgenteRepository, UsuarioAgenteCreate, UsuarioAgenteUpdate


class UsuarioAgenteService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UsuarioAgenteRepository(db)
    
    def asignar_usuario_agente(self, data: UsuarioAgenteCreate, asignado_por: Optional[int] = None):
        # Validación: al menos un permiso debe estar activo
        permisos = [
            data.puede_ver_contenido, data.puede_crear_contenido,
            data.puede_editar_contenido, data.puede_ver_metricas
        ]
        if not any(permisos):
            raise ValidationException("Debe otorgar al menos un permiso")
        
        return self.repo.create(data, asignado_por)
    
    def listar_por_usuario(self, id_usuario: int, activo: Optional[bool] = None):
        return self.repo.get_by_usuario(id_usuario, activo)
    
    def listar_por_agente(self, id_agente: int, activo: Optional[bool] = None):
        return self.repo.get_by_agente(id_agente, activo)
    
    def actualizar_permisos(self, id_usuario_agente: int, data: UsuarioAgenteUpdate):
        return self.repo.update(id_usuario_agente, data)
    
    def revocar_acceso(self, id_usuario_agente: int):
        """Desactiva el acceso (soft delete)"""
        return self.repo.delete(id_usuario_agente)
    
    # ✅ NUEVO: Eliminación permanente
    def eliminar_asignacion(self, id_usuario: int, id_agente: int):
        """
        Elimina permanentemente la asignación de un usuario a un agente.
        Esta acción NO se puede deshacer.
        """
        return self.repo.delete_permanently(id_usuario, id_agente)
    
    def verificar_permisos(self, id_usuario: int, id_agente: int):
        """
        Retorna los permisos del usuario sobre el agente específico.
        Si no tiene acceso activo, retorna None.
        """
        permisos = self.repo.get_by_usuario_agente(id_usuario, id_agente)
        
        if permisos and permisos.activo:
            return permisos
        return None
    
    def listar_agentes_accesibles(self, id_usuario: int):
        """
        Retorna lista de IDs de agentes a los que el usuario tiene acceso
        """
        asignaciones = self.repo.get_by_usuario(id_usuario, activo=True)
        return [asig.id_agente for asig in asignaciones if asig.puede_ver_contenido]
    
    def obtener_por_usuario_agente(self, id_usuario: int, id_agente: int):
        """
        Obtiene la asignación de un usuario a un agente específico.
        """
        return self.repo.get_permisos_usuario_agente(id_usuario, id_agente)

    def actualizar_por_usuario_agente(self, id_usuario: int, id_agente: int, data: UsuarioAgenteUpdate):
        """
        Actualiza los permisos de un usuario sobre un agente específico.
        Busca la asignación por id_usuario e id_agente, luego actualiza.
        """
        # Buscar la asignación
        asignacion = self.repo.get_by_usuario_agente(id_usuario, id_agente)
        
        if not asignacion:
            return None
        
        # Actualizar usando el ID de la asignación
        return self.repo.update(asignacion.id_usuario_agente, data)