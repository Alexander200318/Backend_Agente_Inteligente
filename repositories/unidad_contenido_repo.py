# app/repositories/unidad_contenido_repo.py
from models.unidad_contenido import UnidadContenido
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from exceptions.base import NotFoundException, DatabaseException, ValidationException
from schemas.unidad_contenido_schemas import UnidadContenidoCreate, UnidadContenidoUpdate


class UnidadContenidoRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: UnidadContenidoCreate, creado_por: int):
        try:
            contenido_dict = data.dict()
            contenido = UnidadContenido(**contenido_dict, creado_por=creado_por)
            self.db.add(contenido)
            self.db.commit()
            self.db.refresh(contenido)
            return contenido
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def get_by_id(self, id_contenido: int, include_deleted: bool = False):
        """
        Obtiene contenido por ID, excluye eliminados por defecto
        
        Args:
            id_contenido: ID del contenido
            include_deleted: Si True, incluye contenidos eliminados
        """
        query = self.db.query(UnidadContenido).filter(
            UnidadContenido.id_contenido == id_contenido
        )
        
        # 🔥 Excluir eliminados por defecto
        if not include_deleted:
            query = query.filter(UnidadContenido.eliminado == False)
        
        cont = query.first()
        if not cont:
            raise NotFoundException("Contenido", id_contenido)
        return cont
    
    def get_by_agente(self, id_agente: int, estado: Optional[str] = None, 
                      skip: int = 0, limit: int = 100, include_deleted: bool = False):
        """
        Lista contenidos de un agente con filtros
        
        Args:
            id_agente: ID del agente
            estado: Filtro por estado (opcional)
            skip: Registros a saltar (paginación)
            limit: Límite de registros
            include_deleted: Si True, incluye contenidos eliminados
        """
        from models.agente_virtual import AgenteVirtual
        from models.categoria import Categoria
        
        # 🔥 Query mejorado con aliases explícitos
        query = (
            self.db.query(
                UnidadContenido,
                AgenteVirtual.nombre_agente,
                AgenteVirtual.area_especialidad,
                Categoria.nombre.label('categoria_nombre')
            )
            .join(AgenteVirtual, UnidadContenido.id_agente == AgenteVirtual.id_agente)
            .outerjoin(Categoria, UnidadContenido.id_categoria == Categoria.id_categoria)
            .filter(UnidadContenido.id_agente == id_agente)
        )
        
        # 🔥 Excluir eliminados por defecto
        if not include_deleted:
            query = query.filter(UnidadContenido.eliminado == False)
        
        if estado:
            query = query.filter(UnidadContenido.estado == estado)
        
        resultados = query.order_by(UnidadContenido.prioridad.desc()).offset(skip).limit(limit).all()
        
        # 🔥 Construir respuesta con nombres incluidos
        contenidos_con_nombres = []
        for contenido, nombre_agente, area_especialidad, categoria_nombre in resultados:
            contenido_dict = {
                **{k: v for k, v in contenido.__dict__.items() if not k.startswith('_')},
                'agente_nombre': nombre_agente,
                'area_especialidad': area_especialidad,
                'categoria_nombre': categoria_nombre
            }
            contenidos_con_nombres.append(contenido_dict)
        
        return contenidos_con_nombres
    
    def update(self, id_contenido: int, data: UnidadContenidoUpdate, actualizado_por: int):
        try:
            cont = self.get_by_id(id_contenido)
            for field, value in data.dict(exclude_unset=True).items():
                setattr(cont, field, value)
            cont.actualizado_por = actualizado_por
            self.db.commit()
            self.db.refresh(cont)
            return cont
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def publicar(self, id_contenido: int, publicado_por: int):
        cont = self.get_by_id(id_contenido)
        cont.estado = "activo"
        cont.publicado_por = publicado_por
        cont.fecha_publicacion = datetime.now()
        self.db.commit()
        self.db.refresh(cont)
        return cont
    
    def delete(self, id_contenido: int, eliminado_por: Optional[int] = None, hard_delete: bool = False):
        """
        Elimina contenido (soft delete por defecto)
        
        Args:
            id_contenido: ID del contenido
            eliminado_por: Usuario que elimina el contenido
            hard_delete: Si True, elimina físicamente. Si False, marca como eliminado
        """
        try:
            # 🔥 Incluir eliminados para permitir hard delete de contenidos ya eliminados
            cont = self.get_by_id(id_contenido, include_deleted=True)
            
            if hard_delete:
                # Eliminación física
                self.db.delete(cont)
            else:
                # Soft delete
                cont.eliminado = True
                cont.fecha_eliminacion = datetime.now()
                cont.eliminado_por = eliminado_por
                cont.estado = "archivado"  # Opcional: cambiar estado también
            
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def restore(self, id_contenido: int):
        """
        Restaura un contenido eliminado lógicamente
        
        Args:
            id_contenido: ID del contenido a restaurar
        
        Returns:
            UnidadContenido: Contenido restaurado
        """
        try:
            # 🔥 Buscar incluyendo eliminados
            cont = self.get_by_id(id_contenido, include_deleted=True)
            
            if not cont.eliminado:
                raise ValidationException("El contenido no está eliminado")
            
            # Restaurar
            cont.eliminado = False
            cont.fecha_eliminacion = None
            cont.eliminado_por = None
            # Opcional: cambiar estado a borrador o el que prefieras
            cont.estado = "borrador"
            
            self.db.commit()
            self.db.refresh(cont)
            return cont
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        estado: Optional[str] = None,
        id_agente: Optional[int] = None,
        id_categoria: Optional[int] = None,
        id_departamento: Optional[int] = None,
        include_deleted: bool = False
    ):
        """
        Lista todos los contenidos con filtros opcionales
        
        Args:
            skip: Registros a saltar
            limit: Límite de registros
            estado: Filtro por estado
            id_agente: Filtro por agente
            id_categoria: Filtro por categoría
            id_departamento: Filtro por departamento
            include_deleted: Si True, incluye eliminados
        """
        query = self.db.query(UnidadContenido)
        
        # 🔥 Excluir eliminados por defecto
        if not include_deleted:
            query = query.filter(UnidadContenido.eliminado == False)
        
        if estado:
            query = query.filter(UnidadContenido.estado == estado)
        if id_agente:
            query = query.filter(UnidadContenido.id_agente == id_agente)
        if id_categoria:
            query = query.filter(UnidadContenido.id_categoria == id_categoria)
        if id_departamento:
            query = query.filter(UnidadContenido.id_departamento == id_departamento)
        
        return query.order_by(UnidadContenido.prioridad.desc()).offset(skip).limit(limit).all()
    
    def search(self, termino: str, id_agente: Optional[int] = None, include_deleted: bool = False):
        """
        Busca contenidos por término
        
        Args:
            termino: Término de búsqueda
            id_agente: Filtro por agente (opcional)
            include_deleted: Si True, incluye eliminados
        """
        query = self.db.query(UnidadContenido).filter(
            (UnidadContenido.titulo.contains(termino)) |
            (UnidadContenido.contenido.contains(termino)) |
            (UnidadContenido.resumen.contains(termino))
        )
        
        # 🔥 Excluir eliminados por defecto
        if not include_deleted:
            query = query.filter(UnidadContenido.eliminado == False)
        
        if id_agente:
            query = query.filter(UnidadContenido.id_agente == id_agente)
        
        return query.all()
    
    def get_statistics(self, id_agente: Optional[int] = None, include_deleted: bool = False):
        """
        Obtiene estadísticas de contenidos
        
        Args:
            id_agente: Filtro por agente (opcional)
            include_deleted: Si True, incluye eliminados en estadísticas
        """
        from sqlalchemy import func
        
        query = self.db.query(
            UnidadContenido.estado,
            func.count(UnidadContenido.id_contenido).label('total')
        )
        
        if not include_deleted:
            query = query.filter(UnidadContenido.eliminado == False)
        
        if id_agente:
            query = query.filter(UnidadContenido.id_agente == id_agente)
        
        return query.group_by(UnidadContenido.estado).all()