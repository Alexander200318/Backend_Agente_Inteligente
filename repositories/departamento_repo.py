from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func
from typing import Optional, List
from models.departamento import Departamento
from models.persona import Persona
from models.agente_virtual import AgenteVirtual
from models.unidad_contenido import UnidadContenido
from schemas.departamento_schemas import DepartamentoCreate, DepartamentoUpdate
from exceptions.base import (
    NotFoundException, 
    AlreadyExistsException, 
    DatabaseException
)

class DepartamentoRepository:
    """Repositorio para operaciones CRUD de Departamento"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, depto_data: DepartamentoCreate, creado_por_id: Optional[int] = None) -> Departamento:
        """Crear un nuevo departamento"""
        try:
            # Verificar nombre único
            if self.get_by_nombre(depto_data.nombre):
                raise AlreadyExistsException("Departamento", "nombre", depto_data.nombre)
            
            # Verificar código único
            if self.get_by_codigo(depto_data.codigo):
                raise AlreadyExistsException("Departamento", "código", depto_data.codigo)
            
            departamento = Departamento(**depto_data.dict())
            if creado_por_id:
                departamento.creado_por = creado_por_id
            
            self.db.add(departamento)
            self.db.commit()
            self.db.refresh(departamento)
            return departamento
            
        except IntegrityError as e:
            self.db.rollback()
            if 'nombre' in str(e.orig):
                raise AlreadyExistsException("Departamento", "nombre", depto_data.nombre)
            elif 'codigo' in str(e.orig):
                raise AlreadyExistsException("Departamento", "código", depto_data.codigo)
            raise DatabaseException(f"Error de integridad: {str(e.orig)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al crear departamento: {str(e)}")
    
    def get_by_id(self, id_departamento: int) -> Departamento:
        """Obtener departamento por ID"""
        departamento = self.db.query(Departamento).filter(
            Departamento.id_departamento == id_departamento
        ).first()
        
        if not departamento:
            raise NotFoundException("Departamento", id_departamento)
        return departamento
    
    def get_by_nombre(self, nombre: str) -> Optional[Departamento]:
        """Obtener departamento por nombre"""
        return self.db.query(Departamento).filter(
            Departamento.nombre == nombre
        ).first()
    
    def get_by_codigo(self, codigo: str) -> Optional[Departamento]:
        """Obtener departamento por código"""
        return self.db.query(Departamento).filter(
            Departamento.codigo == codigo.upper()
        ).first()
    
    def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        activo: Optional[bool] = None,
        facultad: Optional[str] = None
    ) -> List[Departamento]:
        """Listar departamentos con filtros"""
        query = self.db.query(Departamento)
        
        if activo is not None:
            query = query.filter(Departamento.activo == activo)
        if facultad:
            query = query.filter(Departamento.facultad == facultad)
        
        return query.order_by(Departamento.nombre).offset(skip).limit(limit).all()
    
    def update(
        self, 
        id_departamento: int, 
        depto_data: DepartamentoUpdate,
        actualizado_por_id: Optional[int] = None
    ) -> Departamento:
        """Actualizar un departamento"""
        try:
            departamento = self.get_by_id(id_departamento)
            
            update_data = depto_data.dict(exclude_unset=True)
            
            # Validar nombre único si se está actualizando
            if 'nombre' in update_data:
                existing = self.get_by_nombre(update_data['nombre'])
                if existing and existing.id_departamento != id_departamento:
                    raise AlreadyExistsException("Departamento", "nombre", update_data['nombre'])
            
            # Validar código único si se está actualizando
            if 'codigo' in update_data:
                existing = self.get_by_codigo(update_data['codigo'])
                if existing and existing.id_departamento != id_departamento:
                    raise AlreadyExistsException("Departamento", "código", update_data['codigo'])
            
            for field, value in update_data.items():
                setattr(departamento, field, value)
            
            if actualizado_por_id:
                departamento.actualizado_por = actualizado_por_id
            
            self.db.commit()
            self.db.refresh(departamento)
            return departamento
            
        except IntegrityError as e:
            self.db.rollback()
            raise DatabaseException(f"Error de integridad: {str(e.orig)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar departamento: {str(e)}")
    
    def delete(self, id_departamento: int) -> dict:
        """Desactivar un departamento (soft delete)"""
        departamento = self.get_by_id(id_departamento)
        
        try:
            departamento.activo = False
            self.db.commit()
            return {
                "message": "Departamento desactivado exitosamente",
                "id_departamento": id_departamento
            }
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al desactivar departamento: {str(e)}")
    
    def get_estadisticas(self, id_departamento: int) -> dict:
        """Obtener estadísticas del departamento"""
        departamento = self.get_by_id(id_departamento)
        
        total_personas = self.db.query(func.count(Persona.id_persona)).filter(
            Persona.id_departamento == id_departamento
        ).scalar()
        
        total_agentes = self.db.query(func.count(AgenteVirtual.id_agente)).filter(
            AgenteVirtual.id_departamento == id_departamento
        ).scalar()
        
        total_contenidos = self.db.query(func.count(UnidadContenido.id_contenido)).filter(
            UnidadContenido.id_departamento == id_departamento
        ).scalar()
        
        return {
            "total_personas": total_personas,
            "total_agentes": total_agentes,
            "total_contenidos": total_contenidos
        }
    
    def count(self, activo: Optional[bool] = None) -> int:
        """Contar departamentos"""
        query = self.db.query(Departamento)
        if activo is not None:
            query = query.filter(Departamento.activo == activo)
        return query.count()
    
    def search(self, search_term: str, limit: int = 20) -> List[Departamento]:
        """Buscar departamentos por nombre o código"""
        search_pattern = f"%{search_term}%"
        return self.db.query(Departamento).filter(
            (Departamento.nombre.ilike(search_pattern)) | 
            (Departamento.codigo.ilike(search_pattern))
        ).limit(limit).all()