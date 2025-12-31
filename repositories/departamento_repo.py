from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from models.departamento import Departamento
from schemas.departamento_schemas import DepartamentoCreate, DepartamentoUpdate
from exceptions.base import NotFoundException, ValidationException
from datetime import datetime

class DepartamentoRepository:
    """Repository para operaciones de base de datos de Departamento"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self, 
        depto_data: DepartamentoCreate,
        creado_por_id: Optional[int] = None
    ) -> Departamento:
        """Crear nuevo departamento"""
        
        # 🔥 Validar unicidad de código (solo contra departamentos activos)
        existe = self.db.query(Departamento).filter(
            func.upper(Departamento.codigo) == depto_data.codigo.upper(),
            Departamento.activo == True  # Solo validar contra activos
        ).first()
        
        if existe:
            raise ValidationException(
                f"Ya existe un departamento activo con el código '{depto_data.codigo}'"
            )
        
        # 🔥 Validar unicidad de nombre (solo contra departamentos activos)
        existe_nombre = self.db.query(Departamento).filter(
            func.upper(Departamento.nombre) == depto_data.nombre.upper(),
            Departamento.activo == True  # Solo validar contra activos
        ).first()
        
        if existe_nombre:
            raise ValidationException(
                f"Ya existe un departamento activo con el nombre '{depto_data.nombre}'"
            )
        
        # Crear departamento
        nuevo_depto = Departamento(
            **depto_data.model_dump(),
            creado_por=creado_por_id,
            activo=True  # 🔥 Siempre crear como activo
        )
        
        self.db.add(nuevo_depto)
        self.db.commit()
        self.db.refresh(nuevo_depto)
        return nuevo_depto
    
    def get_by_id(self, id_departamento: int) -> Departamento:
        """Obtener departamento por ID (incluye inactivos)"""
        depto = self.db.query(Departamento).filter(
            Departamento.id_departamento == id_departamento
        ).first()
        
        if not depto:
            raise NotFoundException(f"Departamento con ID {id_departamento} no encontrado")
        
        return depto
    
    def get_by_codigo(self, codigo: str) -> Optional[Departamento]:
        """Obtener departamento por código (solo activos)"""
        return self.db.query(Departamento).filter(
            func.upper(Departamento.codigo) == codigo.upper(),
            Departamento.activo == True  # 🔥 Solo retornar activos
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
        
        # 🔥 Filtrar por estado activo/inactivo
        if activo is not None:
            query = query.filter(Departamento.activo == activo)
        
        # Filtrar por facultad
        if facultad:
            query = query.filter(
                func.upper(Departamento.facultad).like(f"%{facultad.upper()}%")
            )
        
        return query.order_by(Departamento.nombre).offset(skip).limit(limit).all()
    
    def update(
        self,
        id_departamento: int,
        depto_data: DepartamentoUpdate,
        actualizado_por_id: Optional[int] = None
    ) -> Departamento:
        """Actualizar departamento"""
        depto = self.get_by_id(id_departamento)
        
        # 🔥 Si se está actualizando el código, validar unicidad (solo contra activos)
        if depto_data.codigo and depto_data.codigo.upper() != depto.codigo.upper():
            existe = self.db.query(Departamento).filter(
                func.upper(Departamento.codigo) == depto_data.codigo.upper(),
                Departamento.id_departamento != id_departamento,
                Departamento.activo == True  # Solo validar contra activos
            ).first()
            
            if existe:
                raise ValidationException(
                    f"Ya existe un departamento activo con el código '{depto_data.codigo}'"
                )
        
        # 🔥 Si se está actualizando el nombre, validar unicidad (solo contra activos)
        if depto_data.nombre and depto_data.nombre.upper() != depto.nombre.upper():
            existe_nombre = self.db.query(Departamento).filter(
                func.upper(Departamento.nombre) == depto_data.nombre.upper(),
                Departamento.id_departamento != id_departamento,
                Departamento.activo == True  # Solo validar contra activos
            ).first()
            
            if existe_nombre:
                raise ValidationException(
                    f"Ya existe un departamento activo con el nombre '{depto_data.nombre}'"
                )
        
        # Actualizar campos
        update_data = depto_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(depto, field, value)
        
        depto.actualizado_por = actualizado_por_id
        depto.fecha_actualizacion = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(depto)
        return depto
    
    def delete(
        self, 
        id_departamento: int,
        eliminado_por_id: Optional[int] = None
    ) -> dict:
        """
        🔥 ELIMINADO LÓGICO (SOFT DELETE)
        Cambia activo de True a False (1 a 0)
        NO elimina físicamente el registro
        """
        depto = self.get_by_id(id_departamento)
        
        # 🔥 Validar que no esté ya inactivo
        if not depto.activo:
            raise ValidationException(
                f"El departamento '{depto.nombre}' ya está inactivo"
            )
        
        # 🔥 Desactivar (soft delete)
        depto.activo = False
        depto.actualizado_por = eliminado_por_id
        depto.fecha_actualizacion = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "message": f"Departamento '{depto.nombre}' desactivado correctamente",
            "id_departamento": id_departamento,
            "activo": False
        }
    
    def restore(
        self,
        id_departamento: int,
        restaurado_por_id: Optional[int] = None
    ) -> Departamento:
        """
        🔥 RESTAURAR DEPARTAMENTO
        Cambia activo de False a True (0 a 1)
        """
        depto = self.get_by_id(id_departamento)
        
        # Validar que esté inactivo
        if depto.activo:
            raise ValidationException(
                f"El departamento '{depto.nombre}' ya está activo"
            )
        
        # Validar que no exista otro departamento activo con el mismo código
        existe = self.db.query(Departamento).filter(
            func.upper(Departamento.codigo) == depto.codigo.upper(),
            Departamento.id_departamento != id_departamento,
            Departamento.activo == True
        ).first()
        
        if existe:
            raise ValidationException(
                f"No se puede restaurar: ya existe un departamento activo con el código '{depto.codigo}'"
            )
        
        # Validar que no exista otro departamento activo con el mismo nombre
        existe_nombre = self.db.query(Departamento).filter(
            func.upper(Departamento.nombre) == depto.nombre.upper(),
            Departamento.id_departamento != id_departamento,
            Departamento.activo == True
        ).first()
        
        if existe_nombre:
            raise ValidationException(
                f"No se puede restaurar: ya existe un departamento activo con el nombre '{depto.nombre}'"
            )
        
        # Restaurar
        depto.activo = True
        depto.actualizado_por = restaurado_por_id
        depto.fecha_actualizacion = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(depto)
        
        return depto
    
    def count(self, activo: Optional[bool] = None) -> int:
        """Contar departamentos"""
        query = self.db.query(Departamento)
        
        if activo is not None:
            query = query.filter(Departamento.activo == activo)
        
        return query.count()
    
    def search(self, termino: str) -> List[Departamento]:
        """Buscar departamentos por nombre o código (solo activos)"""
        return self.db.query(Departamento).filter(
            or_(
                func.upper(Departamento.nombre).like(f"%{termino.upper()}%"),
                func.upper(Departamento.codigo).like(f"%{termino.upper()}%")
            ),
            Departamento.activo == True  # 🔥 Solo buscar en activos
        ).order_by(Departamento.nombre).all()
    
    def get_estadisticas(self, id_departamento: int) -> dict:
        """Obtener estadísticas del departamento"""
        depto = self.get_by_id(id_departamento)
        
        # Aquí irían las consultas a tablas relacionadas
        return {
            "total_personas": 0,  # TODO: Implementar conteo real
            "total_agentes": 0,   # TODO: Implementar conteo real
            "total_contenidos": 0  # TODO: Implementar conteo real
        }