from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List, Optional
from models.departamento_agente import DepartamentoAgente
from schemas.departamento_agente_schemas import DepartamentoAgenteCreate, DepartamentoAgenteUpdate
from exceptions.base import *

class DepartamentoAgenteRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: DepartamentoAgenteCreate, asignado_por_id: Optional[int] = None):
        try:
            # Verificar si ya existe
            existing = self.get_by_departamento_agente(data.id_departamento, data.id_agente)
            if existing:
                raise AlreadyExistsException(
                    "Asignación Departamento-Agente",
                    "relación",
                    f"depto:{data.id_departamento} - agente:{data.id_agente}"
                )
            
            asignacion = DepartamentoAgente(**data.dict())
            if asignado_por_id:
                asignacion.asignado_por = asignado_por_id
            
            self.db.add(asignacion)
            self.db.commit()
            self.db.refresh(asignacion)
            return asignacion
        except IntegrityError:
            self.db.rollback()
            raise AlreadyExistsException("Asignación", "departamento-agente", "duplicada")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al crear asignación: {str(e)}")
    
    def get_by_id(self, id_depto_agente: int):
        asignacion = self.db.query(DepartamentoAgente).filter(
            DepartamentoAgente.id_depto_agente == id_depto_agente
        ).first()
        
        if not asignacion:
            raise NotFoundException("Asignación Departamento-Agente", id_depto_agente)
        return asignacion
    
    def get_by_departamento_agente(self, id_departamento: int, id_agente: int):
        return self.db.query(DepartamentoAgente).filter(
            DepartamentoAgente.id_departamento == id_departamento,
            DepartamentoAgente.id_agente == id_agente
        ).first()
    
    def get_by_departamento(self, id_departamento: int, activo: Optional[bool] = None) -> List[DepartamentoAgente]:
        query = self.db.query(DepartamentoAgente).filter(
            DepartamentoAgente.id_departamento == id_departamento
        )
        if activo is not None:
            query = query.filter(DepartamentoAgente.activo == activo)
        return query.all()
    
    def get_by_agente(self, id_agente: int, activo: Optional[bool] = None) -> List[DepartamentoAgente]:
        query = self.db.query(DepartamentoAgente).filter(
            DepartamentoAgente.id_agente == id_agente
        )
        if activo is not None:
            query = query.filter(DepartamentoAgente.activo == activo)
        return query.all()
    
    def update(self, id_depto_agente: int, data: DepartamentoAgenteUpdate):
        try:
            asignacion = self.get_by_id(id_depto_agente)
            
            for field, value in data.dict(exclude_unset=True).items():
                setattr(asignacion, field, value)
            
            self.db.commit()
            self.db.refresh(asignacion)
            return asignacion
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar asignación: {str(e)}")
    
    def delete(self, id_depto_agente: int) -> dict:
        asignacion = self.get_by_id(id_depto_agente)
        try:
            asignacion.activo = False
            self.db.commit()
            return {"message": "Asignación desactivada", "id": id_depto_agente}
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al desactivar asignación: {str(e)}")
    
    def count_by_departamento(self, id_departamento: int) -> int:
        return self.db.query(DepartamentoAgente).filter(
            DepartamentoAgente.id_departamento == id_departamento,
            DepartamentoAgente.activo == True
        ).count()
    
    def count_by_agente(self, id_agente: int) -> int:
        return self.db.query(DepartamentoAgente).filter(
            DepartamentoAgente.id_agente == id_agente,
            DepartamentoAgente.activo == True
        ).count()
