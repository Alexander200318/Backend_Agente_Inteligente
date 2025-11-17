from exceptions.base import ValidationException

from typing import  Optional
from typing import Optional
from sqlalchemy.orm import Session
from repositories.departamento_agente_repo import DepartamentoAgenteRepository,DepartamentoAgenteCreate,DepartamentoAgenteUpdate


class DepartamentoAgenteService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DepartamentoAgenteRepository(db)
    
    def asignar_departamento_agente(
        self,
        data: DepartamentoAgenteCreate,
        asignado_por_id: Optional[int] = None
    ):
        # Validación: al menos un permiso activo
        permisos = [
            data.puede_ver_contenido,
            data.puede_crear_contenido,
            data.puede_ver_metricas
        ]
        if not any(permisos):
            raise ValidationException("Debe otorgar al menos un permiso al departamento")
        
        return self.repo.create(data, asignado_por_id)
    
    def obtener_asignacion(self, id_depto_agente: int):
        return self.repo.get_by_id(id_depto_agente)
    
    def listar_por_departamento(self, id_departamento: int, activo: Optional[bool] = None):
        return self.repo.get_by_departamento(id_departamento, activo)
    
    def listar_por_agente(self, id_agente: int, activo: Optional[bool] = None):
        return self.repo.get_by_agente(id_agente, activo)
    
    def actualizar_permisos(self, id_depto_agente: int, data: DepartamentoAgenteUpdate):
        return self.repo.update(id_depto_agente, data)
    
    def revocar_acceso(self, id_depto_agente: int):
        return self.repo.delete(id_depto_agente)
    
    def obtener_estadisticas(self) -> dict:
        return {
            "info": "Estadísticas de permisos heredados por departamento"
        }
