from exceptions.base import ValidationException
from typing import List, Optional
from typing import Optional
from sqlalchemy.orm import Session
from repositories.agente_virtual_repo import AgenteVirtualRepository,AgenteVirtualCreate,AgenteVirtual,AgenteVirtualUpdate


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
    
    def obtener_agente(self, id_agente: int) -> AgenteVirtual:
        return self.repo.get_by_id(id_agente)
    
    def listar_agentes(
        self,
        skip: int = 0,
        limit: int = 100,
        activo: Optional[bool] = None,
        tipo_agente: Optional[str] = None,
        id_departamento: Optional[int] = None
    ) -> List[AgenteVirtual]:
        if limit > 500:
            raise ValidationException("Límite máximo: 500 registros")
        
        return self.repo.get_all(skip, limit, activo, tipo_agente, id_departamento)
    
    def actualizar_agente(
        self,
        id_agente: int,
        agente_data: AgenteVirtualUpdate,
        actualizado_por_id: Optional[int] = None
    ) -> AgenteVirtual:
        return self.repo.update(id_agente, agente_data, actualizado_por_id)
    
    def eliminar_agente(self, id_agente: int) -> dict:
        # 🔥 NUEVO: Validar solo contenidos NO eliminados
        from models.unidad_contenido import UnidadContenido
        
        contenidos_activos = (
            self.db.query(UnidadContenido)
            .filter(
                UnidadContenido.id_agente == id_agente,
                UnidadContenido.eliminado == False  # ✅ Solo contenidos activos
            )
            .count()
        )
        
        if contenidos_activos > 0:
            raise ValidationException(
                f"No se puede eliminar el agente porque tiene {contenidos_activos} contenido(s) activo(s). "
                "Elimine o archive los contenidos primero."
            )
        
        return self.repo.delete(id_agente)
    
    def obtener_estadisticas(self, id_agente: int) -> dict:
        agente = self.repo.get_by_id(id_agente)
        stats = self.repo.get_estadisticas(id_agente)
        
        return {
            "agente": {
                "id": agente.id_agente,
                "nombre": agente.nombre_agente,
                "tipo": agente.tipo_agente,
                "activo": agente.activo
            },
            **stats
        }
    
    def obtener_estadisticas_generales(self) -> dict:
        return {
            "total_agentes": self.repo.count(),
            "agentes_activos": self.repo.count(activo=True),
            "agentes_inactivos": self.repo.count(activo=False),
            "agentes_router": self.repo.count(activo=True, tipo="router"),
            "agentes_especializados": self.repo.count(activo=True, tipo="especializado"),
            "agentes_hibridos": self.repo.count(activo=True, tipo="hibrido")
        }
    
    def buscar_agentes(self, termino: str) -> List[AgenteVirtual]:
        if len(termino.strip()) < 2:
            raise ValidationException("El término debe tener al menos 2 caracteres")
        
        return self.repo.search(termino)
