from models.unidad_contenido import UnidadContenido
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from exceptions.base import NotFoundException, DatabaseException
from schemas.unidad_contenido_schemas import UnidadContenidoCreate, UnidadContenidoUpdate


class UnidadContenidoRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: UnidadContenidoCreate, creado_por: int):
        try:
            # 🔥 CAMBIO: Remover estado="borrador" hardcodeado
            contenido_dict = data.dict()
            contenido = UnidadContenido(**contenido_dict, creado_por=creado_por)
            self.db.add(contenido)
            self.db.commit()
            self.db.refresh(contenido)
            return contenido
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def get_by_id(self, id_contenido: int):
        cont = self.db.query(UnidadContenido).filter(UnidadContenido.id_contenido == id_contenido).first()
        if not cont:
            raise NotFoundException("Contenido", id_contenido)
        return cont
    
    def get_by_agente(self, id_agente: int, estado: Optional[str] = None, skip: int = 0, limit: int = 100):
        query = self.db.query(UnidadContenido).filter(UnidadContenido.id_agente == id_agente)
        if estado:
            query = query.filter(UnidadContenido.estado == estado)
        return query.order_by(UnidadContenido.prioridad.desc()).offset(skip).limit(limit).all()
    
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
    
    
    def delete(self, id_contenido: int, hard_delete: bool = True):
        """
        Elimina contenido (soft o hard delete)
        
        Args:
            hard_delete: Si True, elimina físicamente. Si False, solo archiva.
        """
        try:
            cont = self.get_by_id(id_contenido)
            
            if hard_delete:
                # Eliminación física
                self.db.delete(cont)
            else:
                # Soft delete
                cont.estado = "archivado"
            
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))