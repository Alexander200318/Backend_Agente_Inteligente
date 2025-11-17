from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
from models.persona import Persona
from schemas.persona_schemas import PersonaCreate, PersonaUpdate
from exceptions.base import (
    NotFoundException, 
    AlreadyExistsException, 
    DatabaseException
)

class PersonaRepository:
    """Repositorio para operaciones CRUD de Persona"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, persona_data: PersonaCreate) -> Persona:
        """Crear una nueva persona"""
        try:
            # Verificar si ya existe la cédula
            if self.get_by_cedula(persona_data.cedula):
                raise AlreadyExistsException("Persona", "cédula", persona_data.cedula)
            
            persona = Persona(**persona_data.dict())
            self.db.add(persona)
            self.db.commit()
            self.db.refresh(persona)
            return persona
            
        except IntegrityError as e:
            self.db.rollback()
            if 'cedula' in str(e.orig):
                raise AlreadyExistsException("Persona", "cédula", persona_data.cedula)
            raise DatabaseException(f"Error de integridad: {str(e.orig)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al crear persona: {str(e)}")
    
    def get_by_id(self, id_persona: int) -> Persona:
        """Obtener persona por ID"""
        persona = self.db.query(Persona).filter(
            Persona.id_persona == id_persona
        ).first()
        
        if not persona:
            raise NotFoundException("Persona", id_persona)
        return persona
    
    def get_by_cedula(self, cedula: str) -> Optional[Persona]:
        """Obtener persona por cédula"""
        return self.db.query(Persona).filter(
            Persona.cedula == cedula
        ).first()
    
    def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        tipo_persona: Optional[str] = None,
        estado: Optional[str] = None,
        id_departamento: Optional[int] = None
    ) -> List[Persona]:
        """Listar personas con filtros opcionales"""
        query = self.db.query(Persona)
        
        if tipo_persona:
            query = query.filter(Persona.tipo_persona == tipo_persona)
        if estado:
            query = query.filter(Persona.estado == estado)
        if id_departamento:
            query = query.filter(Persona.id_departamento == id_departamento)
        
        return query.offset(skip).limit(limit).all()
    
    def update(self, id_persona: int, persona_data: PersonaUpdate) -> Persona:
        """Actualizar una persona"""
        try:
            persona = self.get_by_id(id_persona)
            
            # Actualizar solo los campos proporcionados
            update_data = persona_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(persona, field, value)
            
            self.db.commit()
            self.db.refresh(persona)
            return persona
            
        except IntegrityError as e:
            self.db.rollback()
            raise DatabaseException(f"Error de integridad: {str(e.orig)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar persona: {str(e)}")
    
    def delete(self, id_persona: int) -> dict:
        """Eliminar una persona (soft delete cambiando estado)"""
        persona = self.get_by_id(id_persona)
        
        try:
            # Soft delete
            persona.estado = "inactivo"
            self.db.commit()
            return {
                "message": "Persona eliminada exitosamente",
                "id_persona": id_persona
            }
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al eliminar persona: {str(e)}")
    
    def count(self, tipo_persona: Optional[str] = None, estado: Optional[str] = None) -> int:
        """Contar personas con filtros opcionales"""
        query = self.db.query(Persona)
        
        if tipo_persona:
            query = query.filter(Persona.tipo_persona == tipo_persona)
        if estado:
            query = query.filter(Persona.estado == estado)
        
        return query.count()
    
    def search_by_name(self, search_term: str, limit: int = 20) -> List[Persona]:
        """Buscar personas por nombre o apellido"""
        search_pattern = f"%{search_term}%"
        return self.db.query(Persona).filter(
            (Persona.nombre.ilike(search_pattern)) | 
            (Persona.apellido.ilike(search_pattern))
        ).limit(limit).all()