from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List, Optional
from models.usuario_agente import UsuarioAgente
from exceptions.base import *
from schemas.usuario_agente_schemas import UsuarioAgenteCreate, UsuarioAgenteUpdate

class UsuarioAgenteRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: UsuarioAgenteCreate, asignado_por_id: Optional[int] = None):
        try:
            # Verificar si ya existe
            existing = self.get_by_usuario_agente(data.id_usuario, data.id_agente)
            if existing:
                raise AlreadyExistsException("Asignación", "usuario-agente", f"{data.id_usuario}-{data.id_agente}")
            
            asignacion = UsuarioAgente(**data.dict())
            if asignado_por_id:
                asignacion.asignado_por = asignado_por_id
            
            self.db.add(asignacion)
            self.db.commit()
            self.db.refresh(asignacion)
            return asignacion
        except IntegrityError:
            self.db.rollback()
            raise AlreadyExistsException("Asignación", "usuario-agente", "duplicada")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def get_by_id(self, id_usuario_agente: int):
        asignacion = self.db.query(UsuarioAgente).filter(
            UsuarioAgente.id_usuario_agente == id_usuario_agente
        ).first()
        if not asignacion:
            raise NotFoundException("Asignación", id_usuario_agente)
        return asignacion
    
    def get_by_usuario_agente(self, id_usuario: int, id_agente: int):
        return self.db.query(UsuarioAgente).filter(
            UsuarioAgente.id_usuario == id_usuario,
            UsuarioAgente.id_agente == id_agente
        ).first()
    
    def get_by_usuario(self, id_usuario: int, activo: Optional[bool] = None) -> List[UsuarioAgente]:
        query = self.db.query(UsuarioAgente).filter(UsuarioAgente.id_usuario == id_usuario)
        if activo is not None:
            query = query.filter(UsuarioAgente.activo == activo)
        return query.all()
    
    def get_by_agente(self, id_agente: int, activo: Optional[bool] = None) -> List[UsuarioAgente]:
        query = self.db.query(UsuarioAgente).filter(UsuarioAgente.id_agente == id_agente)
        if activo is not None:
            query = query.filter(UsuarioAgente.activo == activo)
        return query.all()
    
    def update(self, id_usuario_agente: int, data: UsuarioAgenteUpdate):
        try:
            asignacion = self.get_by_id(id_usuario_agente)
            for field, value in data.dict(exclude_unset=True).items():
                setattr(asignacion, field, value)
            self.db.commit()
            self.db.refresh(asignacion)
            return asignacion
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def delete(self, id_usuario_agente: int) -> dict:
        asignacion = self.get_by_id(id_usuario_agente)
        try:
            asignacion.activo = False
            self.db.commit()
            return {"message": "Asignación desactivada", "id": id_usuario_agente}
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(str(e))