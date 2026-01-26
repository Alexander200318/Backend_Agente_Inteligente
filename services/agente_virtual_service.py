from exceptions.base import ValidationException
from typing import List, Optional
from sqlalchemy.orm import Session
from repositories.agente_virtual_repo import AgenteVirtualRepository, AgenteVirtualCreate, AgenteVirtual, AgenteVirtualUpdate


class AgenteVirtualService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AgenteVirtualRepository(db)
    
    def crear_agente(self, agente_data: AgenteVirtualCreate, creado_por_id: Optional[int] = None) -> AgenteVirtual:
        # Validación: nombre descriptivo
        if len(agente_data.nombre_agente.strip()) < 5:
            raise ValidationException("El nombre del agente debe ser más descriptivo (mínimo 5 caracteres)")
        
        # Validación: temperatura en rango válido
        if agente_data.temperatura < 0 or agente_data.temperatura > 2:
            raise ValidationException("La temperatura debe estar entre 0 y 2")
        
        # Validación: router debe tener palabras clave
        if agente_data.tipo_agente == "router" and not agente_data.palabras_clave_trigger:
            raise ValidationException("Un agente router debe tener palabras clave configuradas")
        
        return self.repo.create(agente_data, creado_por_id)
    
    def obtener_agente(self, id_agente: int, incluir_eliminados: bool = False) -> AgenteVirtual:
        """
        Obtener agente por ID.
        Por defecto NO incluye agentes eliminados.
        """
        return self.repo.get_by_id(id_agente, incluir_eliminados)
    
    def listar_agentes(
        self,
        skip: int = 0,
        limit: int = 100,
        activo: Optional[bool] = None,
        tipo_agente: Optional[str] = None,
        id_departamento: Optional[int] = None,
        incluir_eliminados: bool = False
    ) -> List[AgenteVirtual]:
        """
        Listar agentes con filtros.
        Por defecto NO incluye agentes eliminados.
        """
        if limit > 500:
            raise ValidationException("Límite máximo: 500 registros")
        
        return self.repo.get_all(skip, limit, activo, tipo_agente, id_departamento, incluir_eliminados)
    
    def actualizar_agente(
        self,
        id_agente: int,
        agente_data: AgenteVirtualUpdate,
        actualizado_por_id: Optional[int] = None
    ) -> AgenteVirtual:
        """
        Actualizar agente.
        Solo permite actualizar agentes NO eliminados.
        """
        return self.repo.update(id_agente, agente_data, actualizado_por_id)
    
    def eliminar_agente(self, id_agente: int, eliminado_por_id: Optional[int] = None) -> dict:
        """
        Soft delete: Marca el agente como eliminado.
        - Establece eliminado=True
        - Registra fecha_eliminacion
        - Registra eliminado_por
        - También desactiva el agente (activo=False)
        
        Validación: El agente no debe tener contenidos activos.
        """
        from models.unidad_contenido import UnidadContenido
        
        # Validar solo contenidos NO eliminados
        contenidos_activos = (
            self.db.query(UnidadContenido)
            .filter(
                UnidadContenido.id_agente == id_agente,
                UnidadContenido.eliminado == False 
            )
            .count()
        )
        
        if contenidos_activos > 0:
            raise ValidationException(
                f"No se puede eliminar el agente porque tiene {contenidos_activos} contenido(s) activo(s). "
                "Elimine o archive los contenidos primero."
            )
        
        return self.repo.delete(id_agente, eliminado_por_id)
    
    def restaurar_agente(self, id_agente: int) -> dict:
        """
        Restaurar un agente eliminado (soft delete reverso).
        - Establece eliminado=False
        - Limpia fecha_eliminacion y eliminado_por
        - NO cambia el estado 'activo' automáticamente
        """
        return self.repo.restore(id_agente)
    
    def desactivar_agente(self, id_agente: int) -> dict:
        """
        Desactivar agente (activo=False).
        El agente sigue existiendo pero no está operativo.
        Esto es diferente de eliminar.
        """
        return self.repo.desactivar(id_agente)
    
    def activar_agente(self, id_agente: int) -> dict:
        """
        Activar agente (activo=True).
        Reactiva un agente previamente desactivado.
        """
        return self.repo.activar(id_agente)
    
    def eliminar_agente_permanentemente(self, id_agente: int) -> dict:
        """
        ⚠️ HARD DELETE - Elimina físicamente el registro de la base de datos.
        Esta acción es IRREVERSIBLE.
        
        Usar solo en casos excepcionales y con extrema precaución.
        
        Validación adicional: El agente debe estar previamente marcado como eliminado.
        """
        # Verificar que el agente esté marcado como eliminado
        agente = self.repo.get_by_id(id_agente, incluir_eliminados=True)
        
        if not agente.eliminado:
            raise ValidationException(
                "Solo se pueden eliminar permanentemente agentes que ya estén marcados como eliminados. "
                "Primero realice un soft delete."
            )
        
        # Validar que no tenga ningún contenido (ni activo ni eliminado)
        from models.unidad_contenido import UnidadContenido
        
        total_contenidos = (
            self.db.query(UnidadContenido)
            .filter(UnidadContenido.id_agente == id_agente)
            .count()
        )
        
        if total_contenidos > 0:
            raise ValidationException(
                f"No se puede eliminar permanentemente el agente porque tiene {total_contenidos} contenido(s) asociado(s). "
                "Elimine todos los contenidos primero."
            )
        
        return self.repo.delete_permanently(id_agente)
    
    def obtener_estadisticas(self, id_agente: int) -> dict:
        """
        Obtener estadísticas del agente.
        Solo disponible para agentes NO eliminados.
        """
        agente = self.repo.get_by_id(id_agente, incluir_eliminados=False)
        stats = self.repo.get_estadisticas(id_agente)
        
        return {
            "agente": {
                "id": agente.id_agente,
                "nombre": agente.nombre_agente,
                "tipo": agente.tipo_agente,
                "activo": agente.activo,
                "eliminado": agente.eliminado
            },
            **stats
        }
    
    def obtener_estadisticas_generales(self) -> dict:
        """
        Estadísticas generales de todos los agentes.
        Por defecto NO incluye agentes eliminados en los conteos.
        """
        return {
            "total_agentes": self.repo.count(incluir_eliminados=False),
            "agentes_activos": self.repo.count(activo=True, incluir_eliminados=False),
            "agentes_inactivos": self.repo.count(activo=False, incluir_eliminados=False),
            "agentes_router": self.repo.count(activo=True, tipo="router", incluir_eliminados=False),
            "agentes_especializados": self.repo.count(activo=True, tipo="especializado", incluir_eliminados=False),
            "agentes_hibridos": self.repo.count(activo=True, tipo="hibrido", incluir_eliminados=False),
            "agentes_eliminados": self.repo.count(incluir_eliminados=True) - self.repo.count(incluir_eliminados=False)
        }
    
    def buscar_agentes(self, termino: str, incluir_eliminados: bool = False) -> List[AgenteVirtual]:
        """
        Buscar agentes por nombre o área.
        Por defecto NO incluye agentes eliminados.
        """
        if len(termino.strip()) < 2:
            raise ValidationException("El término debe tener al menos 2 caracteres")
        
        return self.repo.search(termino, incluir_eliminados=incluir_eliminados)