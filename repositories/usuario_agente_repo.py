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
    
    def get_by_usuario_agente(self, id_usuario: int, id_agente: int, solo_activos: bool = False):
        """
        Obtiene la asignación por usuario y agente.
        Si solo_activos=True, solo retorna si está activo.
        """
        query = self.db.query(UsuarioAgente).filter(
            UsuarioAgente.id_usuario == id_usuario,
            UsuarioAgente.id_agente == id_agente
        )
        
        if solo_activos:
            query = query.filter(UsuarioAgente.activo == True)
        
        return query.first()
    
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
        """Desactiva la asignación (soft delete)"""
        asignacion = self.get_by_id(id_usuario_agente)
        try:
            asignacion.activo = False
            self.db.commit()
            return {"message": "Asignación desactivada", "id": id_usuario_agente}
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def delete_permanently(self, id_usuario: int, id_agente: int) -> dict:
        """
        Elimina PERMANENTEMENTE el registro de usuario_agente de la base de datos.
        """
        try:
            # Buscar SIN filtro de activo (para poder eliminar incluso si está inactivo)
            asignacion = self.get_by_usuario_agente(id_usuario, id_agente, solo_activos=False)
            
            if not asignacion:
                raise NotFoundException(
                    "Asignación", 
                    f"usuario {id_usuario} - agente {id_agente}"
                )
            
            # Eliminar físicamente
            self.db.delete(asignacion)
            self.db.commit()
            
            return {
                "message": "Asignación eliminada permanentemente",
                "id_usuario": id_usuario,
                "id_agente": id_agente,
                "id_usuario_agente": asignacion.id_usuario_agente
            }
        except NotFoundException:
            # Re-lanzar NotFoundException sin rollback
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def get_permisos_usuario_agente(self, id_usuario: int, id_agente: int) -> Optional[UsuarioAgente]:
        """
        Obtiene los permisos ACTIVOS de un usuario sobre un agente específico.
        Retorna None si no existe asignación o está inactiva.
        """
        return self.get_by_usuario_agente(id_usuario, id_agente, solo_activos=True)
    
    def tiene_permiso(self, id_usuario: int, id_agente: int, permiso: str) -> bool:
        """
        Verifica si un usuario tiene un permiso específico sobre un agente.
        """
        asignacion = self.get_permisos_usuario_agente(id_usuario, id_agente)
        
        if not asignacion:
            return False
        
        return getattr(asignacion, permiso, False) == True