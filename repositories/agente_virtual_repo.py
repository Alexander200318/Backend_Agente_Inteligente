# agente_virtual_repo.py 
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime
from models.agente_virtual import AgenteVirtual
from models.usuario_agente import UsuarioAgente
from models.categoria import Categoria
from models.unidad_contenido import UnidadContenido
from models.conversacion_sync import ConversacionSync
from schemas.agente_virtual_schemas import AgenteVirtualCreate, AgenteVirtualUpdate
from exceptions.base import *

class AgenteVirtualRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, agente_data: AgenteVirtualCreate, creado_por_id: Optional[int] = None) -> AgenteVirtual:
        try:
            agente = AgenteVirtual(**agente_data.dict())
            if creado_por_id:
                agente.creado_por = creado_por_id
            
            self.db.add(agente)
            self.db.commit()
            self.db.refresh(agente)
            return agente
        except IntegrityError as e:
            self.db.rollback()
            raise DatabaseException(f"Error de integridad: {str(e.orig)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al crear agente: {str(e)}")
    
    def get_by_id(self, id_agente: int, incluir_eliminados: bool = False) -> AgenteVirtual:
        """Obtener agente por ID. Por defecto NO incluye eliminados."""
        query = self.db.query(AgenteVirtual).filter(
            AgenteVirtual.id_agente == id_agente
        )
        
        # Filtrar eliminados por defecto
        if not incluir_eliminados:
            query = query.filter(AgenteVirtual.eliminado == False)
        
        agente = query.first()
        
        if not agente:
            raise NotFoundException("AgenteVirtual", id_agente)
        return agente
    
    def get_by_nombre(self, nombre: str, incluir_eliminados: bool = False) -> Optional[AgenteVirtual]:
        """Obtener agente por nombre. Por defecto NO incluye eliminados."""
        query = self.db.query(AgenteVirtual).filter(
            AgenteVirtual.nombre_agente == nombre
        )
        
        if not incluir_eliminados:
            query = query.filter(AgenteVirtual.eliminado == False)
        
        return query.first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        activo: Optional[bool] = None,
        tipo_agente: Optional[str] = None,
        id_departamento: Optional[int] = None,
        incluir_eliminados: bool = False
    ) -> List[AgenteVirtual]:
        """
        Obtener lista de agentes.
        - activo: filtro de estado activo/inactivo (operacional)
        - eliminado: filtro de soft delete (por defecto excluye eliminados)
        """
        query = self.db.query(AgenteVirtual)
        
        # Filtrar eliminados por defecto
        if not incluir_eliminados:
            query = query.filter(AgenteVirtual.eliminado == False)
        
        # activo es independiente de eliminado
        if activo is not None:
            query = query.filter(AgenteVirtual.activo == activo)
        if tipo_agente:
            query = query.filter(AgenteVirtual.tipo_agente == tipo_agente)
        if id_departamento:
            query = query.filter(AgenteVirtual.id_departamento == id_departamento)
        
        return query.order_by(AgenteVirtual.nombre_agente).offset(skip).limit(limit).all()
    
    def update(
        self,
        id_agente: int,
        agente_data: AgenteVirtualUpdate,
        actualizado_por_id: Optional[int] = None
    ) -> AgenteVirtual:
        """Actualizar agente. Solo permite actualizar agentes NO eliminados."""
        try:
            agente = self.get_by_id(id_agente, incluir_eliminados=False)
            
            update_data = agente_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(agente, field, value)
            
            if actualizado_por_id:
                agente.actualizado_por = actualizado_por_id
            
            self.db.commit()
            self.db.refresh(agente)
            return agente
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar agente: {str(e)}")
    
    def delete(self, id_agente: int, eliminado_por_id: Optional[int] = None) -> dict:
        """
        Soft delete: Marca el agente como eliminado.
        También lo desactiva (activo=False) por seguridad.
        """
        agente = self.get_by_id(id_agente, incluir_eliminados=False)
        try:
            agente.eliminado = True
            agente.activo = False  # También desactivamos
            agente.fecha_eliminacion = datetime.now()
            if eliminado_por_id:
                agente.eliminado_por = eliminado_por_id
            
            self.db.commit()
            return {"message": "Agente eliminado correctamente", "id_agente": id_agente}
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al eliminar agente: {str(e)}")
    
    def restore(self, id_agente: int) -> dict:
        """Restaurar un agente eliminado (soft delete reverso)."""
        agente = self.get_by_id(id_agente, incluir_eliminados=True)
        
        if not agente.eliminado:
            raise BusinessLogicException("El agente no está eliminado")
        
        try:
            agente.eliminado = False
            agente.fecha_eliminacion = None
            agente.eliminado_por = None
            # No cambiamos 'activo' automáticamente, el usuario decide si reactivarlo
            
            self.db.commit()
            return {"message": "Agente restaurado correctamente", "id_agente": id_agente}
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al restaurar agente: {str(e)}")
    
    def desactivar(self, id_agente: int) -> dict:
        """Desactivar agente (cambiar activo=False). No es eliminación."""
        agente = self.get_by_id(id_agente, incluir_eliminados=False)
        try:
            agente.activo = False
            self.db.commit()
            return {"message": "Agente desactivado", "id_agente": id_agente}
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al desactivar agente: {str(e)}")
    
    def activar(self, id_agente: int) -> dict:
        """Activar agente (cambiar activo=True)."""
        agente = self.get_by_id(id_agente, incluir_eliminados=False)
        try:
            agente.activo = True
            self.db.commit()
            return {"message": "Agente activado", "id_agente": id_agente}
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al activar agente: {str(e)}")
    
    def delete_permanently(self, id_agente: int) -> dict:
        """
        Hard delete: Elimina físicamente el registro de la base de datos.
        ⚠️ USAR CON PRECAUCIÓN - Esta acción es irreversible.
        """
        agente = self.get_by_id(id_agente, incluir_eliminados=True)
        try:
            self.db.delete(agente)
            self.db.commit()
            return {"message": "Agente eliminado permanentemente", "id_agente": id_agente}
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error al eliminar agente permanentemente: {str(e)}")
    
    def get_estadisticas(self, id_agente: int) -> dict:
        """Obtener estadísticas del agente. Solo para agentes NO eliminados."""
        agente = self.get_by_id(id_agente, incluir_eliminados=False)
        
        total_usuarios = self.db.query(func.count(UsuarioAgente.id_usuario_agente)).filter(
            UsuarioAgente.id_agente == id_agente,
            UsuarioAgente.activo == True
        ).scalar()
        
        total_categorias = self.db.query(func.count(Categoria.id_categoria)).filter(
            Categoria.id_agente == id_agente,
            Categoria.activo == True
        ).scalar()
        
        total_contenidos = self.db.query(func.count(UnidadContenido.id_contenido)).filter(
            UnidadContenido.id_agente == id_agente
        ).scalar()
        
        total_conversaciones = self.db.query(func.count(ConversacionSync.id_conversacion_sync)).filter(
            ConversacionSync.id_agente_inicial == id_agente
        ).scalar()
        
        return {
            "total_usuarios_asignados": total_usuarios or 0,
            "total_categorias": total_categorias or 0,
            "total_contenidos": total_contenidos or 0,
            "total_conversaciones": total_conversaciones or 0
        }
    
    def count(
        self, 
        activo: Optional[bool] = None, 
        tipo: Optional[str] = None,
        incluir_eliminados: bool = False
    ) -> int:
        """Contar agentes. Por defecto NO incluye eliminados."""
        query = self.db.query(AgenteVirtual)
        
        if not incluir_eliminados:
            query = query.filter(AgenteVirtual.eliminado == False)
        
        if activo is not None:
            query = query.filter(AgenteVirtual.activo == activo)
        if tipo:
            query = query.filter(AgenteVirtual.tipo_agente == tipo)
        return query.count()
    
    def search(
        self, 
        search_term: str, 
        limit: int = 20,
        incluir_eliminados: bool = False
    ) -> List[AgenteVirtual]:
        """Buscar agentes por nombre o área. Por defecto NO incluye eliminados."""
        search_pattern = f"%{search_term}%"
        query = self.db.query(AgenteVirtual).filter(
            (AgenteVirtual.nombre_agente.ilike(search_pattern)) |
            (AgenteVirtual.area_especialidad.ilike(search_pattern))
        )
        
        if not incluir_eliminados:
            query = query.filter(AgenteVirtual.eliminado == False)
        
        return query.limit(limit).all()